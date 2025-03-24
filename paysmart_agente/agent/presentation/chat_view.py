import logging
from rest_framework.views import APIView
from rest_framework import status
from agent.interface_adapters.serializers import ChatMessageSerializer
from agent.utils import standard_response
from agent.usecases.process_chat_message import process_chat_message
from agent.infrastructure.gemini_adapter.start_chat import start_chat
from agent.presentation.config import model

logger = logging.getLogger('agent')

class ChatView(APIView):
    def post(self, request):
        serializer = ChatMessageSerializer(data=request.data)
        if serializer.is_valid():
            user_message = serializer.validated_data['message']
            try:
                model_response = process_chat_message(user_message, model, start_chat)
                return standard_response(
                    status_type="success",
                    data={"response": model_response},
                    message="Chat message processed successfully."
                )
            except Exception as e:
                logger.error(f"Error processing chat message: {e}")
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
