from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from users.models import CustomUser
from users.serializers import UserTeamListSerializer
from users.permissions import (
    IsAdmin,
    IsOwnerOrCoachOrAdmin,
    IsCoachOwnerMemberOrAdmin,
)

from profiles.models import Position, PlayerProfile, CoachProfile, StaffProfile

from .models import Team, TeamMembership, Season
from .serializers import (
    TeamSerializer,
    TeamSquadSerializer,
    TeamStaffSerializer,
    AddMemberSerializer,
    RemoveMemberSerializer,
)


class TeamViewSet(viewsets.ModelViewSet):
    """
    Teams CRUD + member management endpoints.

    Permissions:
      - list/retrieve: any authenticated user
      - create/update/destroy: ADMIN only
      - add/remove/create/update member: Owner/Coach/Admin (object-level checked)
      - set_owner: ADMIN only
    """
    queryset = Team.objects.all()
    serializer_class = TeamSerializer
    permission_classes = [IsAuthenticated]

    # ---- Standard permissions per action ----
    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            self.permission_classes = [IsAuthenticated]
        elif self.action in ["create", "update", "partial_update", "destroy"]:
            self.permission_classes = [IsAuthenticated, IsAdmin]
        return super().get_permissions()

    # ---- Create/Update ----
    def perform_create(self, serializer):
        team = serializer.save()

    def perform_update(self, serializer):
        team = serializer.save()

    # ---- Admin-only: set the team owner ----
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsAdmin])
    def set_owner(self, request, pk=None):
        """
        Admin-only: set owner of this team.
        Payload: {"owner_id": <user_id>}
        Ensures an active TeamMembership for the owner (role_on_team=STAFF by default).
        """
        team = self.get_object()
        owner_id = request.data.get("owner_id")
        if not owner_id:
            return Response({"owner_id": ["This field is required."]}, status=400)

        user = get_object_or_404(CustomUser, pk=owner_id)
        if user.role == "ADMIN":
            return Response({"detail": "ADMIN cannot be assigned as team owner."}, status=400)

        team.owner = user
        team.save(update_fields=["owner"])

        with transaction.atomic():
            m, created = TeamMembership.objects.get_or_create(
                user=user,
                team=team,
                defaults={"role_on_team": "STAFF", "active": True},
            )
            if not created and not m.active:
                m.active = True
                m.role_on_team = m.role_on_team or "STAFF"
                m.end_date = None
                m.save(update_fields=["active", "role_on_team", "end_date"])

        return Response(TeamSerializer(team).data, status=200)

    # ---- Attach an existing user as member (reactivate if exists) ----
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsOwnerOrCoachOrAdmin])
    def add_member(self, request, pk=None):
        """
        Attach an existing user to this team via TeamMembership.
        If an inactive membership exists, reactivate it.
        Payload: {"user_id": <int>, "role": "PLAYER"|"STAFF"|"COACH"}
        """
        team = self.get_object()
        ser = AddMemberSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        user = get_object_or_404(CustomUser, pk=ser.validated_data["user_id"])
        role = ser.validated_data["role"]

        with transaction.atomic():
            m = (
                TeamMembership.objects.filter(user=user, team=team)
                .order_by("-id")
                .first()
            )
            if m and not m.active:
                m.active = True
                m.role_on_team = role
                m.end_date = None
                m.save(update_fields=["active", "role_on_team", "end_date"])
            elif not m:
                TeamMembership.objects.create(
                    user=user, team=team, role_on_team=role, active=True
                )

        return Response(UserTeamListSerializer(user).data, status=200)

    # ---- Detach (deactivate) a member ----
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsOwnerOrCoachOrAdmin])
    def remove_member(self, request, pk=None):
        """
        Deactivate the active membership for a given user from this team.
        Payload: {"user_id": <int>}
        """
        team = self.get_object()
        ser = RemoveMemberSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = get_object_or_404(CustomUser, pk=ser.validated_data["user_id"])

        with transaction.atomic():
            m = TeamMembership.objects.filter(user=user, team=team, active=True).first()
            if m:
                m.active = False
                m.end_date = m.end_date or timezone.now().date()
                m.save(update_fields=["active", "end_date"])

        return Response(status=status.HTTP_204_NO_CONTENT)

    # ---- Create a brand-new user + membership (owner/coach/admin) ----
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsOwnerOrCoachOrAdmin])
    def create_member(self, request, pk=None):
        """
        Create a *new* user and attach membership.
        Accepts optional membership fields: jersey_number, primary_position (Position.id), squad_status.
        """
        team = self.get_object()
        from teams.serializers import TeamMemberCreateSerializer  # local import to avoid cycles
        ser = TeamMemberCreateSerializer(data=request.data, context={"team": team})
        ser.is_valid(raise_exception=True)
        user = ser.save()

        with transaction.atomic():
            m, created = TeamMembership.objects.get_or_create(
                user=user,
                team=team,
                defaults={"role_on_team": user.role, "active": True},
            )

            extras = getattr(user, "_membership_initial", {}) or {}
            changed = []
            if "jersey_number" in extras:
                m.jersey_number = extras["jersey_number"]
                changed.append("jersey_number")
            if "primary_position" in extras:
                pid = extras["primary_position"]
                m.primary_position = Position.objects.filter(pk=pid).first() if pid else None
                changed.append("primary_position")
            if "squad_status" in extras:
                m.squad_status = extras["squad_status"] or ""
                changed.append("squad_status")
            if created and not m.active:
                m.active = True
                changed.append("active")
            if changed:
                m.save(update_fields=changed)
            # Write PlayerProfile.dob if present and role is PLAYER
            if extras.get("dob"):
                if user.role == "PLAYER":
                    PlayerProfile.objects.update_or_create(user=user, defaults={"dob": extras["dob"]})
                elif user.role == "COACH":
                    CoachProfile.objects.update_or_create(user=user, defaults={"dob": extras["dob"]})
                elif user.role == "STAFF":
                    StaffProfile.objects.update_or_create(user=user, defaults={"dob": extras["dob"]})


        return Response(UserTeamListSerializer(user).data, status=status.HTTP_201_CREATED)

    # ---- Update a member's membership fields (not user core data) ----
    @action(detail=True, methods=["patch"], permission_classes=[IsAuthenticated, IsOwnerOrCoachOrAdmin])
    def update_member(self, request, pk=None):
        """
        Update membership fields for an active member:
        Payload can include: user_id, jersey_number, primary_position (Position.id), squad_status
        """
        team = self.get_object()
        user_id = request.data.get("user_id")
        if not user_id:
            return Response({"user_id": ["This field is required."]}, status=400)

        user = get_object_or_404(CustomUser, pk=user_id)
        m = get_object_or_404(TeamMembership, team=team, user=user, active=True)

        jersey = request.data.get("jersey_number", None)
        pos_id = request.data.get("primary_position", None)
        squad_status = request.data.get("squad_status", None)

        changed = []
        if jersey is not None:
            m.jersey_number = int(jersey) if jersey != "" else None
            changed.append("jersey_number")

        if pos_id is not None:
            m.primary_position = Position.objects.filter(pk=pos_id).first() if pos_id else None
            changed.append("primary_position")

        if squad_status is not None:
            m.squad_status = squad_status
            changed.append("squad_status")

        if changed:
            m.save(update_fields=changed)

        # Keep response shape (user record) for current UI
        return Response(UserTeamListSerializer(user).data, status=200)


class TeamSquadListView(generics.RetrieveAPIView):
    """
    Returns { id, name, players: [User-like records] } for squad members.
    Optional query param: ?season=<id>
    """
    queryset = Team.objects.all()
    serializer_class = TeamSquadSerializer
    permission_classes = [IsAuthenticated, IsCoachOwnerMemberOrAdmin]

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        season_id = self.request.query_params.get("season")
        if season_id:
            ctx["season"] = Season.objects.filter(pk=season_id).first()
        return ctx


class TeamStaffListView(generics.RetrieveAPIView):
    """
    Returns { id, name, staff: [User-like records] } for non-players.
    Optional query param: ?season=<id>
    """
    queryset = Team.objects.all()
    serializer_class = TeamStaffSerializer
    permission_classes = [IsAuthenticated, IsCoachOwnerMemberOrAdmin]

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        season_id = self.request.query_params.get("season")
        if season_id:
            ctx["season"] = Season.objects.filter(pk=season_id).first()
        return ctx


class MyTeamView(generics.RetrieveAPIView):
    """
    Returns the user's current active team (via membership).
    If none, returns the first team they own.
    """
    serializer_class = TeamSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        user = self.request.user
        m = (
            TeamMembership.objects
            .filter(user=user, active=True)
            .select_related("team")
            .order_by("-id")
            .first()
        )
        if m:
            return m.team

        owned = Team.objects.filter(owner=user).order_by("id").first()
        if owned:
            return owned

        raise PermissionDenied("You don’t belong to or own any team.")
