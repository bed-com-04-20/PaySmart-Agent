from django.urls import path
from agent.presentation.chat_view import ChatView
from agent.presentation.chat_translation_view import ChatTranslationView
from agent.presentation.voice_chat_view import VoiceChatView

urlpatterns = [
    path('chat/', ChatView.as_view(), name='chat_api'),
    # path('ch-translator/', ChatTranslationView.as_view(), name='ch-translator_api'),
    # path('voice-cmds/', VoiceChatView.as_view(), name='voice-cmds_api'),
]
