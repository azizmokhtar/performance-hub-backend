from rest_framework import serializers
from .models import Conversation, Message, Announcement
from users.serializers import UserProfileSerializer # For participant details

class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)
    sender_email = serializers.EmailField(source='sender.email', read_only=True)

    class Meta:
        model = Message
        fields = ('id', 'conversation', 'sender', 'sender_name', 'sender_email', 'content', 'timestamp')
        read_only_fields = ('sender', 'timestamp')

class ConversationSerializer(serializers.ModelSerializer):
    participants_details = UserProfileSerializer(source='participants', many=True, read_only=True)
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ('id', 'name', 'is_group_chat', 'participants', 'participants_details', 'created_at', 'updated_at', 'last_message')
        read_only_fields = ('created_at', 'updated_at', 'last_message', 'participants_details') # Participants can be added via separate endpoint

    def get_last_message(self, obj):
        last_msg = obj.messages.order_by('-timestamp').first()
        if last_msg:
            return MessageSerializer(last_msg).data
        return None

    def create(self, validated_data):
        participants_data = validated_data.pop('participants')
        conversation = Conversation.objects.create(**validated_data)
        conversation.participants.set(participants_data)
        return conversation

class AnnouncementSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)
    team_name = serializers.CharField(source='team.name', read_only=True)
    read_by_count = serializers.SerializerMethodField()

    class Meta:
        model = Announcement
        fields = (
            'id', 'sender', 'sender_name', 'team', 'team_name', 'title',
            'content', 'timestamp', 'is_urgent', 'read_by', 'read_by_count'
        )
        read_only_fields = ('sender', 'timestamp', 'read_by', 'read_by_count')

    def get_read_by_count(self, obj):
        return obj.read_by.count()