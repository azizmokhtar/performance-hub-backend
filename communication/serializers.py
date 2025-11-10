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
        Ensure all participants share at least one common active team.
        Also auto-include request.user if not present (DM/group creation).
        """
        participants = list(attrs.get('participants', []))
        if not participants:
            raise serializers.ValidationError({"participants": ["At least one participant is required."]})
    
        req = self.context.get('request')
        if req and req.user.is_authenticated and req.user not in participants:
            participants.append(req.user)
    
        from teams.models import TeamMembership
        def ids(u):
            return set(TeamMembership.objects.filter(user=u, active=True).values_list('team_id', flat=True))
    
        common = None
        for u in participants:
            tid = ids(u)
            if common is None:
                common = tid
            else:
                common &= tid
    
        if not common:
            raise serializers.ValidationError({"participants": ["All participants must share an active team."]})
    
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
