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


# Helper: active team ids for a user
#TODO : TURN THIS FUNCTION TO A HELPER FILE TO USE EVERYWHERE
from teams.models import TeamMembership, Team

def active_team_ids(user):
    return list(
        TeamMembership.objects.filter(user=user, active=True)
        .values_list("team_id", flat=True)
    )

class ConversationViewSet(viewsets.ModelViewSet):
    queryset = Conversation.objects.all()
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Users see only conversations they participate in
        return self.queryset.filter(participants=self.request.user)

    def perform_create(self, serializer):
        # Ensure creator is a participant
        participants = list(serializer.validated_data.get('participants', []))
        if self.request.user not in participants:
            participants.append(self.request.user)
        serializer.save(participants=participants)

    @action(detail=False, methods=["post"], url_path="start_dm")
    def start_dm(self, request):
        """Start or fetch a 1:1 conversation with a teammate (must share an active team)."""
        me = request.user
        target_id = request.data.get("user_id")
        if not target_id:
            return Response({"detail": "Missing user_id."}, status=400)

        try:
            from users.models import CustomUser
            target = CustomUser.objects.get(pk=target_id)
        except CustomUser.DoesNotExist:
            return Response({"detail": "User not found."}, status=404)

        if target.id == me.id:
            return Response({"detail": "Cannot start a DM with yourself."}, status=400)

        my_teams = set(active_team_ids(me))
        target_teams = set(active_team_ids(target))
        common = my_teams & target_teams
        if not common:
            return Response({"detail": "Target user must share an active team with you."}, status=400)

        # Find existing DM with exactly 2 participants
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
        """Add participants who share an active team with the requester."""
        conv = get_object_or_404(self.get_queryset(), pk=pk)

        if not conv.is_group_chat:
            return Response({"detail": "Cannot add participants to a direct message."}, status=400)

        ids = request.data.get("participant_ids", []) or []
        if not isinstance(ids, list) or not ids:
            return Response({"detail": "participant_ids must be a non-empty list."}, status=400)

        me = request.user
        my_teams = set(active_team_ids(me))
        if not my_teams:
            return Response({"detail": "Only active team members can add participants."}, status=403)

        from users.models import CustomUser
        existing_ids = set(conv.participants.values_list("id", flat=True))
        candidates = list(CustomUser.objects.filter(id__in=ids).exclude(id__in=existing_ids))
        if not candidates:
            return Response({"detail": "No valid users to add."}, status=400)

        valid_new = []
        for u in candidates:
            if my_teams & set(active_team_ids(u)):
                valid_new.append(u)

        if not valid_new:
            return Response({"detail": "No candidates share an active team with you."}, status=400)

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
    # Users can see announcements for any team they actively belong to
        team_ids = active_team_ids(self.request.user)
        if team_ids:
          return self.queryset.filter(team_id__in=team_ids).order_by("-timestamp")
        return self.queryset.none()

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [IsAuthenticated, IsOwnerOrCoachOrAdmin]
        return super().get_permissions()
    
    def perform_create(self, serializer):
        user = self.request.user
        # If staff/coach: force the announcement team to one of their active teams unless admin
        if user.is_admin():
            # Admin may choose any team; require a valid team in payload
            team = serializer.validated_data.get("team")
            if not team:
                self.permission_denied(self.request, message="Admin must specify a team.")
            serializer.save(sender=user)
            return
    
        teams = active_team_ids(user)
        if not teams:
            self.permission_denied(self.request, message="You must be an active team member to post.")
    
        payload_team = serializer.validated_data.get("team")
        if payload_team:
            if payload_team.id not in teams:
                self.permission_denied(self.request, message="You are not a member of the specified team.")
            serializer.save(sender=user)
        else:
            # If only one active team, use it; if many, ask client to specify
            if len(teams) > 1:
                self.permission_denied(self.request, message="You belong to multiple teams. Specify the team.")
            from teams.models import Team
            team = Team.objects.get(pk=teams[0])
            serializer.save(sender=user, team=team)
    

    # Custom action to mark an announcement as read
    def mark_as_read(self, request, pk=None):
        announcement = get_object_or_404(self.get_queryset(), pk=pk)
        announcement.read_by.add(request.user)
        return Response(AnnouncementSerializer(announcement).data, status=status.HTTP_200_OK)