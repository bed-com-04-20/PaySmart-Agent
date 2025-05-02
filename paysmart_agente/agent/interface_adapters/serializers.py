from rest_framework import serializers

class ChatMessageSerializer(serializers.Serializer):
    message = serializers.CharField(
        max_length=500,
        required=True,
        allow_blank=False,
        help_text="The chat message from the user."
    )

    def validate_message(self, value):
    # No length restriction
     return value


class VoiceChatSerializer(serializers.Serializer):
    audio_file = serializers.FileField()
