import logging
from rest_framework.views import APIView
from rest_framework import status
from agent.interface_adapters.serializers import ChatMessageSerializer
from agent.utils import standard_response
from agent.usecases.process_chat_translation import process_chat_translation
from agent.infrastructure.gemini_adapter.start_chat import start_chat
from agent.infrastructure.google_translator.translate_text import translate_text
from agent.presentation.config import model, translate_client, parent

logger = logging.getLogger('agent')

class ChatTranslationView(APIView):
    def post(self, request):
        serializer = ChatMessageSerializer(data=request.data)
        if serializer.is_valid():
            user_message = serializer.validated_data['message']
            try:
                translated_response = process_chat_translation(
                    user_message,
                    model,
                    start_chat,
                    translate_text,
                    translate_client,
                    parent,
                    target_language="ny"
                )
                return standard_response(
                    status_type="success",
                    data={"response": translated_response},
                    message="Chat translation processed successfully."
                )
            except Exception as e:
                logger.error(f"Error processing chat translation: {e}")
                return standard_response(
                    status_type="error",
                    data={"error": "An internal error occurred."},
                    message="An error occurred while processing your request.",
                    http_status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        logger.warning(f"Invalid chat message data: {serializer.errors}")
        return standard_response(
            status_type="error",
            data=serializer.errors,
            message="Invalid chat message data.",
            http_status=status.HTTP_400_BAD_REQUEST
        )
