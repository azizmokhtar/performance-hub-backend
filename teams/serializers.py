from rest_framework import serializers
from .models import Team
from users.serializers import UserTeamListSerializer # Reusing for squad/staff lists
from rest_framework import serializers
from users.models import CustomUser
from .models import Team, TeamMembership
from profiles.models import Position

from rest_framework import serializers
from users.models import CustomUser
from .models import Team
class TeamSerializer(serializers.ModelSerializer):
    head_coach_name = serializers.CharField(source='head_coach.get_full_name', read_only=True)
    head_coach_email = serializers.EmailField(source='head_coach.email', read_only=True)

    owner_name = serializers.CharField(source='owner.get_full_name', read_only=True)   
    owner_email = serializers.EmailField(source='owner.email', read_only=True)    

    class Meta:
        model = Team
        fields = (
            'id', 'name', 'club_crest',
            'head_coach', 'head_coach_name', 'head_coach_email',
            'owner', 'owner_name', 'owner_email',         
            'established_date', 'location', 'created_at', 'updated_at'
        )
        read_only_fields = ('created_at', 'updated_at')

    def validate_head_coach(self, user):
        if user and user.role != "COACH":
            raise serializers.ValidationError("Selected user is not a COACH.")
        return user

class TeamMemberCreateSerializer(serializers.ModelSerializer):
    # membership extras
    jersey_number = serializers.IntegerField(required=False, allow_null=True)
    primary_position = serializers.IntegerField(required=False, allow_null=True)
    squad_status = serializers.CharField(required=False, allow_blank=True)
    dob = serializers.DateField(required=False, allow_null=True)

    class Meta:
        model = CustomUser
        fields = (
            "email", "first_name", "last_name", "role",
            "profile_picture", "jersey_number", "primary_position", "squad_status", "dob",
        )

    def validate_role(self, v):
        if v not in ("PLAYER", "COACH", "STAFF"):
            raise serializers.ValidationError("Role must be PLAYER, COACH, or STAFF.")
        return v

    def validate_primary_position(self, v):
        if v in (None, ''):
            return None
        if not Position.objects.filter(pk=v).exists():
            raise serializers.ValidationError("Invalid position id.")
        return v

    def create(self, validated_data):
        jersey_number = validated_data.pop("jersey_number", None)
        primary_position = validated_data.pop("primary_position", None)
        squad_status = validated_data.pop("squad_status", "")
        dob = validated_data.pop("dob", None)

        user = CustomUser.objects.create_user(
            email=validated_data["email"],
            password=None,
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            role=validated_data["role"],
        )
        if "profile_picture" in validated_data:
            user.profile_picture = validated_data["profile_picture"]
            user.save(update_fields=["first_name","last_name","profile_picture","role"])
        else:
            user.save(update_fields=["first_name","last_name","role"])

        # stash membership extras for the view
        user._membership_initial = {
            "jersey_number": jersey_number,
            "primary_position": primary_position,
            "squad_status": squad_status,
            "dob": dob,   # pass through: view will write PlayerProfile.dob
        }
        return user

class AddMemberSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    role = serializers.ChoiceField(choices=['PLAYER', 'STAFF', 'COACH'])

class RemoveMemberSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()

class SquadMemberAsUserSerializer(UserTeamListSerializer):
    """
    Extendss UserTeamListSerializer but overrides jersey_number & position
    from the membership instance so the frontend keeps the same shape.
    """
    jersey_number = serializers.SerializerMethodField()
    position = serializers.SerializerMethodField()

    class Meta(UserTeamListSerializer.Meta):
        fields = UserTeamListSerializer.Meta.fields + ('jersey_number', 'position')

    def get_jersey_number(self, obj):
        membership = self.context.get('membership_map', {}).get(obj.id)
        return membership.jersey_number if membership else None

    def get_position(self, obj):
        membership = self.context.get('membership_map', {}).get(obj.id)
        if membership and membership.primary_position:
            return membership.primary_position.line
        return None

class TeamSquadSerializer(serializers.ModelSerializer):
    players = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = ('id', 'name', 'players')

    def get_players(self, team: Team):
        season = self.context.get('season')
        memberships = team.get_squad(season)
        # build a map user_id -> membership
        m_by_user = {m.user_id: m for m in memberships}
        users = [m.user for m in memberships]
        ctx = {**self.context, 'membership_map': m_by_user}
        return SquadMemberAsUserSerializer(users, many=True, context=ctx).data


class TeamStaffSerializer(serializers.ModelSerializer):
    staff = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = ('id', 'name', 'staff')

    def get_staff(self, team: Team):
        season = self.context.get('season')
        memberships = team.get_staff(season)
        m_by_user = {m.user_id: m for m in memberships}
        users = [m.user for m in memberships]
        ctx = {**self.context, 'membership_map': m_by_user}
        return SquadMemberAsUserSerializer(users, many=True, context=ctx).data