def process_voice_chat(wav_file_path: str, model, start_chat_func, transcribe_func, speech_client, synthesize_func, tts_client) -> (str, bytes):
    user_message = transcribe_func(speech_client, wav_file_path)
    chat_session = start_chat_func(model, history=[])
    response = chat_session.send_message(user_message)
    model_response = response.text.replace('*', '')
    audio_response = synthesize_func(tts_client, model_response)
    chat_session.history.append({"role": "user", "parts": [user_message]})
    chat_session.history.append({"role": "model", "parts": [model_response]})
    return model_response, audio_response
