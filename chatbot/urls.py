from django.urls import path
from .views import ChatView,SendMessageView

urlpatterns=[
    path('',ChatView.as_view(),name='chat'),
    path('api/send-message/',SendMessageView.as_view(),name='sendmessage'),
]