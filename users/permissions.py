from rest_framework import permissions

class IsCoach(permissions.BasePermission):
    """
    Allows access only to 'COACH' users.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_coach()

class IsPlayer(permissions.BasePermission):
    """
    Allows access only to 'PLAYER' users.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_player()

class IsStaffMember(permissions.BasePermission):
    """
    Allows access only to 'STAFF' users.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_staff_member()

class IsAdmin(permissions.BasePermission):
    """
    Allows access only to 'ADMIN' or superuser accounts.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_admin()

class IsCoachOrAdmin(permissions.BasePermission):
    """
    Allows access only to 'COACH' or 'ADMIN' users.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and (request.user.is_coach() or request.user.is_admin())

# users/permissions.py (snippets)
from teams.models import TeamMembership

class IsTeamMember(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # obj is a Team or has .team
        team_id = getattr(obj, 'id', None) if obj.__class__.__name__ == 'Team' else getattr(obj, 'team_id', None)
        if not team_id:
            return False
        return TeamMembership.objects.filter(user_id=request.user.id, team_id=team_id, active=True).exists()

class IsSelfOrCoachOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.is_admin():
            return True
        if obj == request.user:
            return True
        if request.user.is_coach():
            # coach must be active member of same team as target user
            return TeamMembership.objects.filter(
                user_id=request.user.id, role_on_team='COACH', active=True,
                team_id__in=TeamMembership.objects.filter(user_id=getattr(obj, 'id', None)).values('team_id')
            ).exists()
        return False


from rest_framework import permissions
from teams.models import TeamMembership
from teams.models import Team

class IsOwnerOrCoachOrAdmin(permissions.BasePermission):
    """
    Owner of the object, or a coach/admin from the same team.
    obj is expected to be a Team, or have .team / .player / .sender attributes.
    """
    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_admin():
            return True

        # Direct ownership of the object (common user-linked cases)
        if getattr(obj, 'user', None) == user:   # e.g. user-owned resource
            return True
        if getattr(obj, 'player', None) == user: # e.g. player-owned resource
            return True
        if getattr(obj, 'sender', None) == user: # e.g. message
            return True

        # Determine the team_id of the object
        team_obj = None
        if isinstance(obj, Team):
            team_obj = obj
        elif hasattr(obj, 'team') and isinstance(obj.team, Team):
            team_obj = obj.team
        elif hasattr(obj, 'team_id'):
            try:
                team_obj = Team.objects.get(pk=obj.team_id)
            except Team.DoesNotExist:
                team_obj = None

        if not team_obj:
            return False

        # Is the requester an active COACH on that team?
        is_coach_on_team = TeamMembership.objects.filter(
            user_id=user.id, team_id=team_obj.id,
            role_on_team='COACH', active=True
        ).exists()
        if is_coach_on_team:
            return True

        # Is the requester the OWNER of the team?
        if getattr(team_obj, 'owner_id', None) == user.id:
            return True

        return False

from rest_framework import permissions

class IsCoachOwnerMemberOrAdmin(permissions.BasePermission):
    """
    Allow COACH, ADMIN, the team's OWNER, or any active MEMBER of the team.
    Expects obj to be a Team instance.
    """
    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_admin():
            return True
        if getattr(obj, "owner_id", None) == user.id:
            return True
        # active membership of any role
        return TeamMembership.objects.filter(user_id=user.id, team_id=obj.id, active=True).exists()