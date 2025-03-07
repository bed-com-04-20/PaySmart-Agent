import os
import logging
import google.generativeai as genai
from rest_framework.views import APIView
from rest_framework import status
from django.conf import settings
from .serializers import ChatMessageSerializer, VoiceChatSerializer
from .utils import standard_response
from google.cloud import translate_v3
from google.cloud import texttospeech_v1
from google.cloud import speech_v1p1beta1 as speech
import base64
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from pydub import AudioSegment

# Initialize logger
logger = logging.getLogger('api')

# Load credentials from Django settings
GOOGLE_APPLICATION_CREDENTIALS = settings.GOOGLE_APPLICATION_CREDENTIALS
GOOGLE_CLOUD_PROJECT_ID = settings.GOOGLE_CLOUD_PROJECT_ID
GEMINI_API_KEY = settings.GEMINI_API_KEY

# Configure Gemini API
if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY is not set in the environment variables.")
    raise EnvironmentError("GEMINI_API_KEY is not set.")

genai.configure(api_key=GEMINI_API_KEY)

# Gemini model with configuration
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

try:
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash-exp",
        generation_config=generation_config,
        system_instruction=(
            "Your name is Paysmart, an expert in financial services, digital payments, and customer support,"
            "You greet customers warmly and provide clear, practical answers to their questions about payments, transactions, account management, and financial tips,"
            "Keep responses short and simple unless more detail is needed,"
            "Focus on practical advice and avoid unnecessary technical jargon,"
            "Use relatable examples and tips to make understanding financial processes easy,"
            "Tailor your responses to the customer's needs and suggest real-world solutions for seamless payments, financial planning, and better money management,"
            "Be friendly, insightful, and supportive, ensuring customers feel confident and assisted."
        ),
    )
except Exception as e:
    logger.error(f"Failed to initialize Gemini model: {e}")
    raise

# Google Cloud Translation, Text-to-Speech, and Speech-to-Text clients
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = GOOGLE_APPLICATION_CREDENTIALS
translate_client = translate_v3.TranslationServiceClient()
tts_client = texttospeech_v1.TextToSpeechClient()
speech_client = speech.SpeechClient()

parent = f"projects/{GOOGLE_CLOUD_PROJECT_ID}/locations/global"

def translate_text(text, target_language):
    response = translate_client.translate_text(
        request={
            "parent": parent,
            "contents": [text],
            "mime_type": "text/plain",
            "target_language_code": target_language,
        }
    )
    return response.translations[0].translated_text

def text_to_speech(text, language_code="en-US"):
    synthesis_input = texttospeech_v1.SynthesisInput(text=text)
    voice = texttospeech_v1.VoiceSelectionParams(
        language_code=language_code,
        ssml_gender=texttospeech_v1.SsmlVoiceGender.NEUTRAL
    )
    audio_config = texttospeech_v1.AudioConfig(
        audio_encoding=texttospeech_v1.AudioEncoding.MP3
    )
    response = tts_client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config
    )
    return response.audio_content

def speech_to_text(audio_file):
    with open(audio_file, "rb") as audio:
        content = audio.read()
    audio = speech.RecognitionAudio(content=content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code="en-US",
    )
    response = speech_client.recognize(config=config, audio=audio)
    return response.results[0].alternatives[0].transcript

class ChatView(APIView):
    """
    API view to handle chat messages and communicate with Google Gemini.
    """ 

    def post(self, request):
        serializer = ChatMessageSerializer(data=request.data)
        if serializer.is_valid():
            user_message = serializer.validated_data['message']
            try:
                # Start new chat 
                chat_session = model.start_chat(history=[])

                # Get response 
                response = chat_session.send_message(user_message)
                model_response = response.text

                # Update history 
                chat_session.history.append({"role": "user", "parts": [user_message]})
                chat_session.history.append({"role": "model", "parts": [model_response]})

                # Return response
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
        # Return error response with validation errors
        logger.warning(f"Invalid chat message data: {serializer.errors}")
        return standard_response(
            status_type="error",
            data=serializer.errors,
            message="Invalid chat message data.",
            http_status=status.HTTP_400_BAD_REQUEST
        )

class ChatTranslationView(APIView):
    """
    API view to handle chat messages in Chichewa, translate them to English,
    communicate with Google Gemini, and translate the response back to Chichewa.
    """

    def post(self, request):
        serializer = ChatMessageSerializer(data=request.data)
        if serializer.is_valid():
            user_message = serializer.validated_data['message']
            try:
                # Translate Chichewa to English
                translated_message = translate_text(user_message, "en")

                # Start new chat 
                chat_session = model.start_chat(history=[])

                # Get response 
                response = chat_session.send_message(translated_message)
                model_response = response.text

                # Translate English to Chichewa
                translated_response = translate_text(model_response, "ny")

                # Update history 
                chat_session.history.append({"role": "user", "parts": [translated_message]})
                chat_session.history.append({"role": "model", "parts": [model_response]})

                # Return translated response
                return standard_response(
                    status_type="success",
                    data={"response": translated_response},
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
        # Return error response with validation errors
        logger.warning(f"Invalid chat message data: {serializer.errors}")
        return standard_response(
            status_type="error",
            data=serializer.errors,
            message="Invalid chat message data.",
            http_status=status.HTTP_400_BAD_REQUEST
        )
  

class VoiceChatView(APIView):
    """
    API view to handle voice-based chat messages and communicate with Google Gemini.
    """

    def post(self, request):
        serializer = VoiceChatSerializer(data=request.data)
        if serializer.is_valid():
            audio_file = serializer.validated_data['audio_file']
            try:
                # Save the uploaded audio file temporarily
                file_name = default_storage.save('temp_audio.m4a', ContentFile(audio_file.read()))
                file_path = default_storage.path(file_name)
                logger.info(f"File saved at: {file_path}")

                # Convert .m4a to .wav
                wav_file_path = file_path.replace('.m4a', '.wav')
                try:
                    audio = AudioSegment.from_file(file_path, format="m4a")
                    audio.export(wav_file_path, format="wav", parameters=["-ac", "1", "-ar", "16000"])
                    logger.info(f"Converted file saved at: {wav_file_path}")
                except Exception as e:
                    logger.error(f"Error converting .m4a to .wav: {e}")
                    return standard_response(
                        status_type="error",
                        data={"error": "Failed to convert audio file."},
                        message="An error occurred while processing your request.",
                        http_status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )

                # Convert speech to text
                user_message = speech_to_text(wav_file_path)
                logger.info(f"Converted text: {user_message}")

                # Start a new chat session with Gemini
                chat_session = model.start_chat(history=[])

                # Get response from Gemini model
                response = chat_session.send_message(user_message)
                model_response = response.text

                # Convert text to speech
                audio_response = text_to_speech(model_response)

                # Clean up the temporary files
                default_storage.delete(file_name)
                os.remove(wav_file_path)

                # Encode the audio response in base64 for Postman
                audio_base64 = base64.b64encode(audio_response).decode('utf-8')

                # Return the base64-encoded audio response
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
        # Return error response with validation errors
        logger.warning(f"Invalid voice chat data: {serializer.errors}")
        return standard_response(
            status_type="error",
            data=serializer.errors,
            message="Invalid voice chat data.",
            http_status=status.HTTP_400_BAD_REQUEST
        )