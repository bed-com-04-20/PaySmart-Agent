def process_chat_translation(message: str, model, start_chat_func, translator_func, translate_client, parent, target_language="ny") -> str:
    translated_message = translator_func(translate_client, parent, message, "en")
    chat_session = start_chat_func(model, history=[])
    response = chat_session.send_message(translated_message)
    model_response = response.text.replace('*', '')
    translated_response = translator_func(translate_client, parent, model_response, target_language)
    chat_session.history.append({"role": "user", "parts": [translated_message]})
    chat_session.history.append({"role": "model", "parts": [model_response]})
    return translated_response
