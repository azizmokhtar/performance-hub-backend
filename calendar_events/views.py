from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q

from .models import Event, Attendance
from .serializers import EventSerializer, AttendanceSerializer
from users.permissions import IsCoachOrAdmin # Adjust import path


from teams.models import TeamMembership, Team
#TODO: TURN THIS FUNCTION TO A HELPER FILE TO USE EVERYWHERE
def active_team_ids(user):
    return list(
        TeamMembership.objects.filter(user=user, active=True)
        .values_list("team_id", flat=True)
    )

class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        team_ids = active_team_ids(self.request.user)
        if team_ids:
            return self.queryset.filter(team_id__in=team_ids)
        return self.queryset.none()


    def get_permissions(self):
        # Only Coaches or Admins can create, update, delete events
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [IsAuthenticated, IsCoachOrAdmin]
        return super().get_permissions()

    def perform_create(self, serializer):
        user = self.request.user
        if user.is_admin():
            team = serializer.validated_data.get('team')
            if not team:
                self.permission_denied(self.request, message="Admin must specify a team for the event.")
            serializer.save(created_by=user)
            return

        if user.is_coach():
            payload_team = serializer.validated_data.get('team')
            my_teams = set(active_team_ids(user))
            if payload_team:
                if payload_team.id not in my_teams:
                    self.permission_denied(self.request, message="You are not a coach of the specified team.")
                serializer.save(created_by=user)
            else:
                # If single active team, use it; otherwise require explicit team
                if len(my_teams) != 1:
                    self.permission_denied(self.request, message="Specify team (you have multiple/zero active teams).")
                team = Team.objects.get(pk=list(my_teams)[0])
                serializer.save(created_by=user, team=team)
            return

        self.permission_denied(self.request, message="Only Coaches or Admins can create events.")


class AttendanceListView(generics.ListAPIView):
    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated, IsCoachOrAdmin] # Only coaches/admins can view all attendance

    def get_queryset(self):
        event_id = self.kwargs['event_id']
        # requester must belong to the event team
        event = get_object_or_404(Event, pk=event_id)
        if event.team_id not in active_team_ids(self.request.user):
            self.permission_denied(self.request, message="You are not a member of this team's event.")
        return Attendance.objects.filter(event=event)


class AttendanceUpdateView(generics.UpdateAPIView):
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        event_id = self.kwargs['event_id']
        player_id = self.kwargs['player_id']
        event = get_object_or_404(Event, pk=event_id)
    
        # Ensure requester belongs to the event's team
        if event.team_id not in active_team_ids(self.request.user):
            self.permission_denied(self.request, message="You are not a member of this team's event.")
    
        obj = get_object_or_404(self.get_queryset(), event=event, player_id=player_id)
    
        # A player can update their own status; coach/admin of the event team can update any
        if not (
            obj.player_id == self.request.user.id
            or self.request.user.is_admin()
            or TeamMembership.objects.filter(
                user_id=self.request.user.id, team_id=event.team_id, role_on_team='COACH', active=True
              ).exists()
        ):
            self.permission_denied(self.request, message="You do not have permission to update this attendance.")
    
        return obj
    
    
    def perform_update(self, serializer):
        serializer.save(reported_by=self.request.user)