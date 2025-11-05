# chatbot/services.py
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

class ExternalChatbotService:
    def __init__(self):
        self.driver = None
        self.is_initialized = False
        self.chat_initialized = False
    
    def initialize_browser(self):
        """Initialize Chrome browser - NO HEADLESS"""
        try:
            if self.is_initialized and self.driver:
                print("✅ Browser already initialized")
                return True
                
            chrome_options = Options()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--window-size=1200,800")
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            self.is_initialized = True
            print("✅ Browser initialized (visible mode)")
            return True
            
        except Exception as e:
            print(f"Browser init error: {e}")
            return False
    
    def ensure_chat_ready(self):
        """Make sure we're on ChatGPT and ready to chat"""
        try:
            if not self.is_initialized:
                if not self.initialize_browser():
                    return False
            
            if self.chat_initialized:
                print("✅ Continuing existing chat session")
                return True
            
            print("🌐 Navigating to ChatGPT...")
            self.driver.get("https://chatgpt.com/")
            time.sleep(3)
            
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#prompt-textarea, [contenteditable='true']"))
            )
            
            self.chat_initialized = True
            print("✅ ChatGPT ready for conversation")
            return True
            
        except Exception as e:
            print(f"❌ Error ensuring chat ready: {e}")
            return False
    
    def send_to_chatgpt_stream(self, message):
        """Stream response from ChatGPT with better timeout handling"""
        try:
            if not self.ensure_chat_ready():
                yield "Error: Could not initialize chat session"
                return
            
            # Find input field
            input_selectors = [
                "#prompt-textarea",
                "[contenteditable='true']",
                "div[contenteditable='true']"
            ]
            
            input_field = None
            for selector in input_selectors:
                try:
                    input_field = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    print(f"✅ Found input field with: {selector}")
                    break
                except:
                    continue
            
            if not input_field:
                yield "Error: Could not find input field on ChatGPT"
                return
            
            # Type and send message
            print(f"⌨️ Sending: {message}")
            input_field.clear()
            input_field.send_keys(message)
            
            # Find and click send button
            send_selectors = [
                "button[data-testid='send-button']",
                "#composer-submit-button",
                "button.composer-submit-btn"
            ]
            
            send_button = None
            for selector in send_selectors:
                try:
                    send_button = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    if send_button.is_enabled():
                        send_button.click()
                        print(f"✅ Sent message with: {selector}")
                        break
                except:
                    continue
            
            if not send_button:
                yield "Error: Could not find send button"
                return
            
            # Wait for response to start
            print("⏳ Waiting for response to start...")
            response_started = False
            last_text = ""
            
            for i in range(60):  # Wait up to 60 seconds total
                # Find the latest assistant message
                response_selectors = [
                    "[data-testid='conversation-turn']:last-child [data-message-author-role='assistant']",
                    "[data-message-author-role='assistant']:last-child",
                    ".group:last-child .dark\\:bg-gray-800"
                ]
                
                current_text = ""
                for selector in response_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            current_text = elements[-1].text.strip()
                            if current_text:
                                break
                    except:
                        continue
                
                # If we have text and it's different from last time
                if current_text and current_text != last_text:
                    if not response_started:
                        print("🎯 Response started!")
                        response_started = True
                    
                    # Find what's new (for streaming)
                    if last_text and current_text.startswith(last_text):
                        new_chunk = current_text[len(last_text):]
                    else:
                        new_chunk = current_text
                    
                    if new_chunk:
                        print(f"📝 Streaming chunk: {new_chunk[:50]}...")
                        yield new_chunk
                        last_text = current_text
                
                # Check if response is complete
                typing_indicators = [
                    "[data-testid*='typing']",
                    "[class*='typing']",
                    "[class*='cursor']",
                    ".result-streaming"
                ]
                
                streaming_active = False
                for indicator in typing_indicators:
                    try:
                        if self.driver.find_elements(By.CSS_SELECTOR, indicator):
                            streaming_active = True
                            break
                    except:
                        continue
                
                # If no streaming indicators and text unchanged for 3 seconds, we're done
                if not streaming_active and current_text and current_text == last_text:
                    if i > 10:  # Wait at least 10 seconds before considering complete
                        print("✅ Streaming complete - no more changes")
                        return
                
                # If we have a decent response and no streaming for a while, consider complete
                if last_text and len(last_text) > 50 and not streaming_active:
                    if i > 15:  # Wait at least 15 seconds for longer responses
                        print("✅ Streaming complete - substantial response received")
                        return
                
                time.sleep(1)  # Check every second
            
            # If we get here, timeout occurred but return what we have
            if last_text:
                print(f"⚠️ Timeout but returning collected response: {last_text[:100]}...")
                # Don't yield anything new, just end
            else:
                print("❌ Timeout with no response")
                yield "Error: Timeout waiting for response"
            
        except Exception as e:
            print(f"❌ Error in send_to_chatgpt_stream: {e}")
            yield f"Error: {str(e)}"
    
    def close(self):
        if self.driver:
            self.driver.quit()
            self.is_initialized = False
            self.chat_initialized = False
            print("✅ Browser closed")

external_bot_service = ExternalChatbotService()