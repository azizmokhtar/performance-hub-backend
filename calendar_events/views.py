from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q

from .models import Event, Attendance
from .serializers import EventSerializer, AttendanceSerializer
from users.permissions import IsCoachOrAdmin # Adjust import path

class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Users (players, coaches, staff) can only see events for their own team
        if self.request.user.team:
            return self.queryset.filter(team=self.request.user.team)
        return self.queryset.none()

    def get_permissions(self):
        # Only Coaches or Admins can create, update, delete events
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [IsAuthenticated, IsCoachOrAdmin]
        return super().get_permissions()

    def perform_create(self, serializer):
        # Automatically assign creator and ensure team consistency
        if self.request.user.is_coach():
            serializer.save(created_by=self.request.user, team=self.request.user.team)
        elif self.request.user.is_admin():
            # Admins can create events for any team
            team = serializer.validated_data.get('team')
            if not team:
                self.permission_denied(self.request, message="Admin must specify a team for the event.")
            serializer.save(created_by=self.request.user)
        else:
            self.permission_denied(self.request, message="Only Coaches or Admins can create events.")

class AttendanceListView(generics.ListAPIView):
    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated, IsCoachOrAdmin] # Only coaches/admins can view all attendance

    def get_queryset(self):
        event_id = self.kwargs['event_id']
        event = get_object_or_404(Event, pk=event_id, team=self.request.user.team) # Restrict to user's team
        return Attendance.objects.filter(event=event)

class AttendanceUpdateView(generics.UpdateAPIView):
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        event_id = self.kwargs['event_id']
        player_id = self.kwargs['player_id']
        event = get_object_or_404(Event, pk=event_id, team=self.request.user.team)
        obj = get_object_or_404(self.get_queryset(), event=event, player_id=player_id)

        # A player can update their own status. Coach/Admin can update any player's status in their team.
        if not (obj.player == self.request.user or self.request.user.is_coach() or self.request.user.is_admin()):
            self.permission_denied(self.request, message="You do not have permission to update this attendance.")
        return obj

    def perform_update(self, serializer):
        serializer.save(reported_by=self.request.user)