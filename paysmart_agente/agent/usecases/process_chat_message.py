def process_chat_message(message: str, model, start_chat_func) -> str:
    chat_session = start_chat_func(model, history=[])
    response = chat_session.send_message(message)
    model_response = response.text.replace('*', '')
    chat_session.history.append({"role": "user", "parts": [message]})
    chat_session.history.append({"role": "model", "parts": [model_response]})
    return model_response
