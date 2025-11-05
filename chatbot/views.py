# chatbot/views.py
from django.shortcuts import render
from django.views import View
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .utils import external_bot_service
import json
import time

@method_decorator(csrf_exempt, name='dispatch')
class SendMessageView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            message = data.get('message', '').strip()
            
            if not message:
                return JsonResponse({
                    'success': False,
                    'error': 'Empty message'
                })
            
            print(f"📨 Sending to ChatGPT: {message}")
            
            def generate_stream():
                """Generator function to stream responses"""
                try:
                    # Start the ChatGPT interaction
                    for chunk in external_bot_service.send_to_chatgpt_stream(message):
                        if chunk:
                            # Send as Server-Sent Event
                            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                            time.sleep(0.1)  # Small delay for smooth streaming
                    
                    # Send completion signal
                    yield "data: [DONE]\n\n"
                    
                except Exception as e:
                    error_msg = f"Error: {str(e)}"
                    yield f"data: {json.dumps({'error': error_msg})}\n\n"
                    yield "data: [DONE]\n\n"
            
            response = StreamingHttpResponse(
                generate_stream(),
                content_type='text/event-stream'
            )
            response['Cache-Control'] = 'no-cache'
            response['X-Accel-Buffering'] = 'no'  # Disable buffering for nginx
            return response
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Internal server error'
            }, status=500)

class ChatView(View):
    def get(self, request):
        return render(request, 'chatbot/chat.html')