import google.generativeai as genai

def init_gemini(api_key, generation_config, system_instruction, model_name="gemini-2.0-flash-exp"):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name=model_name,
        generation_config=generation_config,
        system_instruction=system_instruction,
    )
    return model
