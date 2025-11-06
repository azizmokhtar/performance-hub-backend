from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.shortcuts import get_object_or_404

from .models import Conversation, Message, Announcement
from .serializers import ConversationSerializer, MessageSerializer, AnnouncementSerializer
from users.permissions import IsCoachOrAdmin, IsTeamMember # Adjust import path

class ConversationViewSet(viewsets.ModelViewSet):
    queryset = Conversation.objects.all()
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Users can only see conversations they are part of
        return self.queryset.filter(participants=self.request.user)

    def perform_create(self, serializer):
        # When creating a new conversation, the creator is automatically a participant
        participants = serializer.validated_data.get('participants', [])
        if self.request.user not in participants:
            participants.append(self.request.user)
        serializer.save(participants=participants)

    # Custom action to add/remove participants (PUT /api/conversations/{id}/participants/)
    def add_participants(self, request, pk=None):
        conversation = get_object_or_404(Conversation, pk=pk)
        self.check_object_permissions(request, conversation) # Ensure user is participant/admin

        if not conversation.is_group_chat and conversation.participants.count() >= 2:
            return Response({"detail": "Cannot add participants to a direct message that already has two."},
                            status=status.HTTP_400_BAD_REQUEST)

        participant_ids = request.data.get('participant_ids', [])
        new_participants = []
        for user_id in participant_ids:
            try:
                user = self.request.user.team.members.get(id=user_id) # Only add members from same team
                new_participants.append(user)
            except Exception:
                pass # Ignore invalid user IDs

        conversation.participants.add(*new_participants)
        return Response(self.get_serializer(conversation).data, status=status.HTTP_200_OK)

class MessageListView(generics.ListCreateAPIView):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        conversation_id = self.kwargs['conversation_id']
        conversation = get_object_or_404(Conversation, pk=conversation_id)
        # Ensure user is a participant of the conversation
        if not conversation.participants.filter(id=self.request.user.id).exists():
            self.permission_denied(self.request, message="You are not a participant of this conversation.")
        return Message.objects.filter(conversation=conversation).order_by('timestamp')

    def perform_create(self, serializer):
        conversation_id = self.kwargs['conversation_id']
        conversation = get_object_or_404(Conversation, pk=conversation_id)
        if not conversation.participants.filter(id=self.request.user.id).exists():
            self.permission_denied(self.request, message="You are not a participant of this conversation.")
        serializer.save(sender=self.request.user, conversation=conversation)
        # Update conversation's updated_at to bring it to top of list
        conversation.save()

class AnnouncementViewSet(viewsets.ModelViewSet):
    queryset = Announcement.objects.all()
    serializer_class = AnnouncementSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Users can only see announcements for their own team
        if self.request.user.team:
            return self.queryset.filter(team=self.request.user.team).order_by('-timestamp')
        return self.queryset.none()

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [IsAuthenticated, IsCoachOrAdmin]
        return super().get_permissions()

    def perform_create(self, serializer):
        # Automatically assign sender and ensure team consistency for coaches
        if self.request.user.is_coach():
            serializer.save(sender=self.request.user, team=self.request.user.team)
        elif self.request.user.is_admin():
            # Admins can create announcements for any team, assuming 'team' is in payload
            team = serializer.validated_data.get('team')
            if not team:
                self.permission_denied(self.request, message="Admin must specify a team for the announcement.")
            serializer.save(sender=self.request.user)
        else:
            self.permission_denied(self.request, message="Only Coaches or Admins can create announcements.")


    # Custom action to mark an announcement as read
    def mark_as_read(self, request, pk=None):
        announcement = get_object_or_404(self.get_queryset(), pk=pk)
        announcement.read_by.add(request.user)
        return Response(AnnouncementSerializer(announcement).data, status=status.HTTP_200_OK)