from rest_framework import serializers
from .models import Team
from users.serializers import UserTeamListSerializer # Reusing for squad/staff lists


class TeamSerializer(serializers.ModelSerializer):
    head_coach_name = serializers.CharField(source='head_coach.get_full_name', read_only=True)
    head_coach_email = serializers.EmailField(source='head_coach.email', read_only=True)

    owner_name = serializers.CharField(source='owner.get_full_name', read_only=True)   # <---
    owner_email = serializers.EmailField(source='owner.email', read_only=True)         # <---

    class Meta:
        model = Team
        fields = (
            'id', 'name', 'club_crest',
            'head_coach', 'head_coach_name', 'head_coach_email',
            'owner', 'owner_name', 'owner_email',                # <--- include owner id + read-only fields
            'established_date', 'location', 'created_at', 'updated_at'
        )
        read_only_fields = ('created_at', 'updated_at')

class TeamSquadSerializer(serializers.ModelSerializer):
    players = UserTeamListSerializer(source='get_squad', many=True, read_only=True)

    class Meta:
        model = Team
        fields = ('id', 'name', 'players')

class TeamStaffSerializer(serializers.ModelSerializer):
    staff = UserTeamListSerializer(source='get_staff', many=True, read_only=True)

    class Meta:
        model = Team
        fields = ('id', 'name', 'staff')

from rest_framework import serializers
from users.models import CustomUser
from .models import Team

class TeamMemberCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        # no password here -> creates user with unusable password (invite later)
        fields = (
            "email", "first_name", "last_name", "role",
            "date_of_birth", "jersey_number", "position", "profile_picture",
        )

    def validate_role(self, v):
        if v not in ("PLAYER", "COACH", "STAFF"):
            raise serializers.ValidationError("Role must be PLAYER, COACH, or STAFF.")
        return v

    def create(self, validated_data):
        team: Team = self.context["team"]
        # create_user() in your manager sets is_staff/is_superuser flags per role
        user = CustomUser.objects.create_user(
            email=validated_data["email"],
            password=None,  # unusable password (invite flow later)
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            role=validated_data["role"],
            date_of_birth=validated_data.get("date_of_birth"),
            jersey_number=validated_data.get("jersey_number"),
            position=validated_data.get("position"),
        )
        if "profile_picture" in validated_data:
            user.profile_picture = validated_data["profile_picture"]
        user.team = team
        user.save()
        return user


class TeamMemberUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ("date_of_birth", "jersey_number", "position", "profile_picture")

class AddMemberSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    role = serializers.ChoiceField(choices=['PLAYER', 'STAFF', 'COACH'])

class RemoveMemberSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()