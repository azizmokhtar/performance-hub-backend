from rest_framework import serializers
from .models import Document
from users.serializers import UserProfileSerializer # For uploader/shared_with details

class DocumentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)
    team_name = serializers.CharField(source='team.name', read_only=True)
    # shared_with_players_details = UserProfileSerializer(source='shared_with_players', many=True, read_only=True) # Too much detail for MVP list

    class Meta:
        model = Document
        fields = (
            'id', 'title', 'file', 'uploaded_by', 'uploaded_by_name',
            'team', 'team_name', 'shared_with_players', 'description',
            'file_type', 'uploaded_at'
        )
        read_only_fields = ('uploaded_by', 'uploaded_at', 'file_type', 'team_name', 'uploaded_by_name') # Team might be updated by admin
        extra_kwargs = {'file': {'required': True}} # File is mandatory on creation