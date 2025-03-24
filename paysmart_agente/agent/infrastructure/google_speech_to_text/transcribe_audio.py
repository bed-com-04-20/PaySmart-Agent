def transcribe_audio(client, audio_file_path: str) -> str:
    from google.cloud import speech_v1p1beta1 as speech
    with open(audio_file_path, "rb") as audio:
        content = audio.read()
    audio_obj = speech.RecognitionAudio(content=content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code="en-US",
    )
    response = client.recognize(config=config, audio=audio_obj)
    return response.results[0].alternatives[0].transcript
