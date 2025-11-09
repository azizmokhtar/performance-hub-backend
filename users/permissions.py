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

class IsTeamMember(permissions.BasePermission):
    """
    Allows access only to users who are members of the requested team.
    Assumes the view has a `team_id` or `pk` in its kwargs referring to a Team.
    """
    def has_object_permission(self, request, view, obj):
        # obj could be a Team, or an object with a .team attribute
        if hasattr(obj, 'team'):
            return request.user.team == obj.team
        elif isinstance(obj, type(request.user.team)): # If obj is a Team instance itself
             return request.user.team == obj
        return False

class IsOwnerOrCoachOrAdmin(permissions.BasePermission):
    """
    Allows access to the object owner, or a coach/admin from the same team.
    Assumes the object has a 'user' or 'player' field.
    """
    def has_object_permission(self, request, view, obj):
        # Allow owner to view/edit their own object
        if hasattr(obj, 'player') and obj.player == request.user:
            return True
        if hasattr(obj, 'user') and obj.user == request.user: # e.g., for CustomUser itself
            return True
        if hasattr(obj, 'sender') and obj.sender == request.user: # e.g., for a Message
            return True

        # Allow coaches/admins from the same team to view/edit
        if request.user.is_coach() or request.user.is_admin():
            if hasattr(obj, 'team') and obj.team == request.user.team:
                return True
            if hasattr(obj, 'player') and obj.player.team == request.user.team:
                return True
            if hasattr(obj, 'sender') and obj.sender.team == request.user.team:
                return True
            if isinstance(obj, type(request.user)): # For user profiles
                return obj.team == request.user.team

        return False

class IsSelfOrCoachOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # Always allow admins
        if request.user.is_admin():
            return True

        # Allow self
        if obj == request.user:
            return True

        # Allow coaches for users in their team
        if request.user.is_coach():
            return getattr(obj, "team_id", None) == request.user.team_id

        return False



from rest_framework import permissions

class IsCoachOwnerMemberOrAdmin(permissions.BasePermission):
    """
    Allow COACH, ADMIN, the team's OWNER, or any user whose .team matches the team.
    Expects `obj` to be a Team instance.
    """
    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_admin() or user.is_coach():
            return True
        if getattr(obj, "owner_id", None) == user.id:
            return True
        return getattr(user, "team_id", None) == obj.id
