def convert_m4a_to_wav(input_path: str, output_path: str) -> None:
    from pydub import AudioSegment
    audio = AudioSegment.from_file(input_path, format="m4a")
    audio.export(output_path, format="wav", parameters=["-ac", "1", "-ar", "16000"])
