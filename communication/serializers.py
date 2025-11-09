from rest_framework import serializers
from .models import Conversation, Message, Announcement
from users.serializers import UserProfileSerializer

class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)
    sender_email = serializers.EmailField(source='sender.email', read_only=True)

    class Meta:
        model = Message
        fields = ('id', 'conversation', 'sender', 'sender_name', 'sender_email', 'content', 'timestamp')
        # Make 'conversation' read-only because perform_create assigns it
        read_only_fields = ('sender', 'timestamp', 'conversation')


class ConversationSerializer(serializers.ModelSerializer):
    participants_details = UserProfileSerializer(source='participants', many=True, read_only=True)
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = (
            'id', 'name', 'is_group_chat', 'participants',
            'participants_details', 'created_at', 'updated_at', 'last_message'
        )
        read_only_fields = ('created_at', 'updated_at', 'last_message', 'participants_details')

    def get_last_message(self, obj):
        last_msg = obj.messages.order_by('-timestamp').first()
        if last_msg:
            return MessageSerializer(last_msg).data
        return None

    def validate(self, attrs):
        """
        Ensure all participants are from the same (non-null) team.
        For DM, exactly 2 participants (will be finalized in the view’s perform_create).
        """
        participants = attrs.get('participants', [])
        if not participants:
            raise serializers.ValidationError({"participants": ["At least one participant is required."]})

        # Include the request.user if not already present (mirror your perform_create).
        req = self.context.get('request')
        if req and req.user.is_authenticated and req.user not in participants:
            participants = list(participants) + [req.user]

        team_ids = {getattr(u, 'team_id', None) for u in participants}
        # All must share the same team_id and it cannot be None
        if len(team_ids) != 1 or None in team_ids:
            raise serializers.ValidationError({"participants": ["All participants must belong to the same team."]})

        # Optionally forbid participants==1 for group chats
        # (we’ll allow draft 1→add later; you can tighten if needed)
        return attrs

    def create(self, validated_data):
        participants = validated_data.pop('participants')
        conversation = Conversation.objects.create(**validated_data)
        conversation.participants.set(participants)
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
