from rest_framework import serializers
from .models import Team
from users.serializers import UserTeamListSerializer # Reusing for squad/staff lists

class TeamSerializer(serializers.ModelSerializer):
    head_coach_name = serializers.CharField(source='head_coach.get_full_name', read_only=True)
    head_coach_email = serializers.EmailField(source='head_coach.email', read_only=True)

    class Meta:
        model = Team
        fields = (
            'id', 'name', 'club_crest', 'head_coach', 'head_coach_name',
            'head_coach_email', 'established_date', 'location', 'created_at', 'updated_at'
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