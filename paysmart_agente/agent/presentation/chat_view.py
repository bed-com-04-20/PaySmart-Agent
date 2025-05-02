import logging
from rest_framework.views import APIView
from rest_framework import status
from agent.interface_adapters.serializers import ChatMessageSerializer
from agent.utils import standard_response
from agent.usecases.process_chat_message import process_chat_message
from agent.usecases.process_tv_payment_request import TVPaymentHandler  
from agent.infrastructure.gemini_adapter.start_chat import start_chat
from agent.presentation.config import model

logger = logging.getLogger('agent')

class ChatView(APIView):
    def post(self, request):
        serializer = ChatMessageSerializer(data=request.data)
        if not serializer.is_valid():
            return standard_response(
                status_type="error",
                data=serializer.errors,
                message="Invalid chat message data.",
                http_status=status.HTTP_400_BAD_REQUEST
            )

        user_message = serializer.validated_data['message']
        session_context = request.session.get('chat_context', {})

        try:
            # TV payment flow
            if any(word in user_message.lower() for word in ["tv", "package", "plan", "subscribe", "channel", "show"]):
                model_response = TVPaymentHandler.handle_payment_flow(
                    user_message,
                    session_context
                )
            # General chat
            else:
                model_response = process_chat_message(
                    user_message, 
                    model, 
                    start_chat
                )

            request.session['chat_context'] = session_context
            request.session.modified = True

            return standard_response(
                status_type="success",
                data={"response": model_response},
                message="Chat message processed successfully."
            )

        except Exception as e:
            logger.error(f"Error processing chat message: {str(e)}", exc_info=True)
            return standard_response(
                status_type="error",
                data={"error": "An internal error occurred."},
                message=str(e),
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
