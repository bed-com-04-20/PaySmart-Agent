# api/serializers.py

from rest_framework import serializers

class ChatMessageSerializer(serializers.Serializer):
    """
    Serializer for handling chat messages.
    """
    message = serializers.CharField(
        max_length=500,
        required=True,
        allow_blank=False,
        help_text="The chat message from the user."
    )

    def validate_message(self, value):
        if len(value) < 5:
            raise serializers.ValidationError("Message must be at least 5 characters long.")
        return value
        
class VoiceChatSerializer(serializers.Serializer):
    audio_file = serializers.FileField()