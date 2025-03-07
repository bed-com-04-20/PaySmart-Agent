# api/urls.py

from django.urls import path
from .views import ChatView, ChatTranslationView, VoiceChatView

urlpatterns = [
    path('chat/', ChatView.as_view(), name='chat_api'),
    path('ch-translator/', ChatTranslationView.as_view(), name='ch-translator_api'),
    path('voice-cmds/', VoiceChatView.as_view(), name='voice-cmds_api'),
]
