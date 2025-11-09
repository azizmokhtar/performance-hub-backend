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

from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.shortcuts import get_object_or_404

from .models import Conversation, Message, Announcement
from .serializers import ConversationSerializer, MessageSerializer, AnnouncementSerializer
from users.models import CustomUser
from users.permissions import IsOwnerOrCoachOrAdmin

# communication/views.py
from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404

from .models import Conversation, Message, Announcement
from .serializers import ConversationSerializer, MessageSerializer, AnnouncementSerializer
from users.permissions import IsCoachOrAdmin, IsTeamMember

class ConversationViewSet(viewsets.ModelViewSet):
    queryset = Conversation.objects.all()
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Users can only see conversations they are part of
        return self.queryset.filter(participants=self.request.user)

    def perform_create(self, serializer):
        # Ensure creator is a participant
        participants = list(serializer.validated_data.get('participants', []))
        if self.request.user not in participants:
            participants.append(self.request.user)
        serializer.save(participants=participants)

    @action(detail=False, methods=["post"], url_path="start_dm")
    def start_dm(self, request):
        """Start or fetch a 1:1 conversation with a teammate."""
        me = request.user
        target_id = request.data.get("user_id")
        if not target_id:
            return Response({"detail": "Missing user_id."}, status=400)

        try:
            target = me.team.members.get(id=target_id) if me.team_id else None
        except Exception:
            target = None
        if not target:
            return Response({"detail": "Target user must be in the same team."}, status=400)
        if target.id == me.id:
            return Response({"detail": "Cannot start a DM with yourself."}, status=400)

        # Find existing DM: exactly 2 participants (me, target), not a group
        qs = (
            Conversation.objects.filter(is_group_chat=False, participants=me)
            .filter(participants=target)
            .annotate(pcount=Count("participants"))
            .filter(pcount=2)
        )
        conv = qs.first()
        if not conv:
            conv = Conversation.objects.create(is_group_chat=False, name=None)
            conv.participants.set([me, target])

        return Response(ConversationSerializer(conv).data, status=200)

    @action(detail=True, methods=["post"], url_path="add_participants")
    def add_participants(self, request, pk=None):
        """Add teammates to an existing group conversation."""
        conv = get_object_or_404(self.get_queryset(), pk=pk)

        # Must be a group chat
        if not conv.is_group_chat:
            return Response({"detail": "Cannot add participants to a direct message."}, status=400)

        # Only allow adding teammates
        ids = request.data.get("participant_ids", []) or []
        if not isinstance(ids, list) or not ids:
            return Response({"detail": "participant_ids must be a non-empty list."}, status=400)

        me = request.user
        if not me.team_id:
            return Response({"detail": "Only team members can add participants."}, status=403)

        valid_new = list(me.team.members.filter(id__in=ids).exclude(id__in=conv.participants.values_list("id", flat=True)))
        if not valid_new:
            return Response({"detail": "No valid teammates to add."}, status=400)

        conv.participants.add(*valid_new)
        conv.save(update_fields=["updated_at"])
        return Response(ConversationSerializer(conv).data, status=200)

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
            self.permission_classes = [IsAuthenticated, IsOwnerOrCoachOrAdmin]
        return super().get_permissions()
    
    def perform_create(self, serializer):
        user = self.request.user
        # Safety: permissions already required by get_permissions
        if not getattr(user, "team_id", None):
            self.permission_denied(self.request, message="Staff must belong to a team to post announcements.")
        # Force sender & team; ignore any client-provided team
        serializer.save(sender=user, team=user.team)


    # Custom action to mark an announcement as read
    def mark_as_read(self, request, pk=None):
        announcement = get_object_or_404(self.get_queryset(), pk=pk)
        announcement.read_by.add(request.user)
        return Response(AnnouncementSerializer(announcement).data, status=status.HTTP_200_OK)