from rest_framework import viewsets, generics
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .models import Team
from .serializers import TeamSerializer, TeamSquadSerializer, TeamStaffSerializer, AddMemberSerializer, RemoveMemberSerializer
from users.permissions import IsAdmin, IsCoachOwnerMemberOrAdmin, IsOwnerOrCoachOrAdmin
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from users.models import CustomUser
from users.serializers import UserTeamListSerializer

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
    def perform_create(self, serializer):
        team = serializer.save()
        # Sync owner.team -> team
        if team.owner and team.owner.team_id != team.id:
            team.owner.team = team
            team.owner.save(update_fields=["team"])

    def perform_update(self, serializer):
        team = serializer.save()
        if team.owner and team.owner.team_id != team.id:
            team.owner.team = team
            team.owner.save(update_fields=["team"])
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsOwnerOrCoachOrAdmin])
    def add_member(self, request, pk=None):
        team = self.get_object()  # permission checks object-level
        ser = AddMemberSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = get_object_or_404(CustomUser, pk=ser.validated_data['user_id'])

        # Assign role and team
        user.role = ser.validated_data['role']
        user.team = team
        user.save(update_fields=["role", "team"])

        return Response(UserTeamListSerializer(user).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsOwnerOrCoachOrAdmin])
    def remove_member(self, request, pk=None):
        team = self.get_object()
        ser = RemoveMemberSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = get_object_or_404(CustomUser, pk=ser.validated_data['user_id'])

        # Only detach if currently in this team
        if user.team_id == team.id:
            user.team = None
            user.save(update_fields=["team"])
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(
        detail=True, methods=["post"],
        permission_classes=[IsAuthenticated, IsOwnerOrCoachOrAdmin]
    )
    def create_member(self, request, pk=None):
        team = self.get_object()
        ser = TeamMemberCreateSerializer(data=request.data, context={"team": team})
        ser.is_valid(raise_exception=True)
        user = ser.save()
        return Response(UserTeamListSerializer(user).data, status=status.HTTP_201_CREATED)

    @action(
        detail=True, methods=["patch"],
        permission_classes=[IsAuthenticated, IsOwnerOrCoachOrAdmin]
    )
    def update_member(self, request, pk=None):
        team = self.get_object()
        user_id = request.data.get("user_id")
        if not user_id:
            return Response({"user_id": ["This field is required."]}, status=400)

        user = get_object_or_404(CustomUser, pk=user_id, team=team)
        ser = TeamMemberUpdateSerializer(user, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(UserTeamListSerializer(user).data, status=200)

class TeamSquadListView(generics.RetrieveAPIView):
    queryset = Team.objects.all()
    serializer_class = TeamSquadSerializer
    permission_classes = [IsAuthenticated, IsCoachOwnerMemberOrAdmin] 



class TeamStaffListView(generics.RetrieveAPIView):
    queryset = Team.objects.all()
    serializer_class = TeamStaffSerializer
    permission_classes = [IsAuthenticated, IsCoachOwnerMemberOrAdmin]  # <-- changed



from rest_framework import generics
from rest_framework.exceptions import PermissionDenied

class MyTeamView(generics.RetrieveAPIView):
    serializer_class = TeamSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        user = self.request.user
        # If user is a member of a team, prefer that
        if getattr(user, "team_id", None):
            return Team.objects.get(pk=user.team_id)
        # Else, if user owns a team, return the first owned team
        owned = Team.objects.filter(owner=user).order_by("id").first()
        if owned:
            return owned
        raise PermissionDenied("You don’t belong to or own any team.")
