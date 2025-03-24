import os
from django.conf import settings
from google.cloud import translate_v3, texttospeech_v1
from google.cloud import speech_v1p1beta1 as speech
from agent.infrastructure.gemini_adapter.init_gemini import init_gemini

# External settings
GOOGLE_APPLICATION_CREDENTIALS = settings.GOOGLE_APPLICATION_CREDENTIALS
GOOGLE_CLOUD_PROJECT_ID = settings.GOOGLE_CLOUD_PROJECT_ID
GEMINI_API_KEY = settings.GEMINI_API_KEY

if not GEMINI_API_KEY:
    raise EnvironmentError("GEMINI_API_KEY is not set.")

# Gemini configuration
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}
system_instruction = (
    "Your name is Paysmart, an expert in financial services, digital payments, and customer support. "
    "You greet customers warmly and provide clear, practical answers to their questions about payments, transactions, account management, and financial tips. "
    "Keep responses short and simple unless more detail is needed. "
    "Focus on practical advice and avoid unnecessary technical jargon. "
    "Use relatable examples and tips to make understanding financial processes easy. "
    "Tailor your responses to the customer's needs and suggest real-world solutions for seamless payments, financial planning, and better money management. "
    "Be friendly, insightful, and supportive, ensuring customers feel confident and assisted."
)

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = GOOGLE_APPLICATION_CREDENTIALS

# Initialize Google Cloud clients
translate_client = translate_v3.TranslationServiceClient()
tts_client = texttospeech_v1.TextToSpeechClient()
speech_client = speech.SpeechClient()
parent = f"projects/{GOOGLE_CLOUD_PROJECT_ID}/locations/global"

# Initialize Gemini model
model = init_gemini(GEMINI_API_KEY, generation_config, system_instruction)
