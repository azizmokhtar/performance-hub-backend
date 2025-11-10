from rest_framework import serializers
from .models import Event, Attendance
from users.serializers import UserProfileSerializer # For player details

class EventSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    team_name = serializers.CharField(source='team.name', read_only=True)

    class Meta:
        model = Event
        fields = (
            'id', 'title', 'description', 'team', 'team_name', 'event_type',
            'start_time', 'end_time', 'location', 'created_by', 'created_by_name',
            'is_mandatory', 'notes', 'created_at', 'updated_at'
        )
        read_only_fields = ('created_at', 'updated_at', 'created_by')

    def validate(self, data):
        if data['start_time'] >= data['end_time']:
            raise serializers.ValidationError("End time must be after start time.")
        return data

class AttendanceSerializer(serializers.ModelSerializer):
    player_name = serializers.CharField(source='player.get_full_name', read_only=True)
    # player_position removed (was on CustomUser). Optionally compute later via membership in a custom list endpoint.
    event_title = serializers.CharField(source='event.title', read_only=True)
    reported_by_name = serializers.CharField(source='reported_by.get_full_name', read_only=True)

    class Meta:
        model = Attendance
        fields = (
            'id', 'event', 'event_title', 'player', 'player_name',
            'status', 'notes', 'reported_by', 'reported_by_name', 'timestamp'
        )
        read_only_fields = ('timestamp', 'reported_by')
