from rest_framework import viewsets, generics
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .models import Team
from .serializers import TeamSerializer, TeamSquadSerializer, TeamStaffSerializer
from users.permissions import IsAdmin, IsCoachOrAdmin # Adjust import path

class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.all()
    serializer_class = TeamSerializer
    permission_classes = [IsAuthenticated] # Default for all actions

    def get_permissions(self):
        # Allow any authenticated user to list teams (GET)
        # Only Admin can create, update, delete teams
        if self.action in ['list', 'retrieve']:
            self.permission_classes = [IsAuthenticated]
        elif self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [IsAdmin]
        return super().get_permissions()

class TeamSquadListView(generics.RetrieveAPIView):
    queryset = Team.objects.all()
    serializer_class = TeamSquadSerializer
    permission_classes = [IsAuthenticated, IsCoachOrAdmin] # Coaches/Admins can view squad

    def get_object(self):
        # Ensures that a coach can only see the squad of their own team, not other teams
        obj = get_object_or_404(self.get_queryset(), pk=self.kwargs['pk'])
        if not self.request.user.is_admin() and obj != self.request.user.team:
            self.permission_denied(self.request, message="You do not have permission to view this team's squad.")
        return obj

class TeamStaffListView(generics.RetrieveAPIView):
    queryset = Team.objects.all()
    serializer_class = TeamStaffSerializer
    permission_classes = [IsAuthenticated, IsCoachOrAdmin] # Coaches/Admins can view staff

    def get_object(self):
        obj = get_object_or_404(self.get_queryset(), pk=self.kwargs['pk'])
        if not self.request.user.is_admin() and obj != self.request.user.team:
            self.permission_denied(self.request, message="You do not have permission to view this team's staff.")
        return obj