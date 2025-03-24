import os
import logging
import base64
from rest_framework.views import APIView
from rest_framework import status
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from agent.interface_adapters.serializers import VoiceChatSerializer
from agent.utils import standard_response
from agent.usecases.process_voice_chat import process_voice_chat
from agent.infrastructure.gemini_adapter.start_chat import start_chat
from agent.infrastructure.google_speech_to_text.transcribe_audio import transcribe_audio
from agent.infrastructure.google_text_to_speech.synthesize_text import synthesize_text
from agent.infrastructure.audio_converter.convert_m4a_to_wav import convert_m4a_to_wav
from agent.presentation.config import model, speech_client, tts_client

logger = logging.getLogger('agent')

class VoiceChatView(APIView):
    def post(self, request):
        serializer = VoiceChatSerializer(data=request.data)
        if serializer.is_valid():
            audio_file = serializer.validated_data['audio_file']
            try:
                file_name = default_storage.save('temp_audio.m4a', ContentFile(audio_file.read()))
                file_path = default_storage.path(file_name)
                wav_file_path = file_path.replace('.m4a', '.wav')
                convert_m4a_to_wav(file_path, wav_file_path)
                model_response, audio_response = process_voice_chat(
                    wav_file_path,
                    model,
                    start_chat,
                    transcribe_audio,
                    speech_client,
                    synthesize_text,
                    tts_client
                )
                default_storage.delete(file_name)
                os.remove(wav_file_path)
                audio_base64 = base64.b64encode(audio_response).decode('utf-8')
                return standard_response(
                    status_type="success",
                    data={"audio_response": audio_base64},
                    message="Voice chat message processed successfully."
                )
            except Exception as e:
                logger.error(f"Error processing voice chat message: {e}")
                return standard_response(
                    status_type="error",
                    data={"error": str(e)},
                    message="An error occurred while processing your request.",
                    http_status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        logger.warning(f"Invalid voice chat data: {serializer.errors}")
        return standard_response(
            status_type="error",
            data=serializer.errors,
            message="Invalid voice chat data.",
            http_status=status.HTTP_400_BAD_REQUEST
        )
