from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models import Q
from datetime import date, timedelta

from .models import DailyWellnessEntry
from .serializers import DailyWellnessEntry, TeamWellnessOverviewSerializer
from users.permissions import IsPlayer, IsCoachOrAdmin, IsOwnerOrCoachOrAdmin # Adjust import path

class PlayerWellnessEntryView(generics.ListCreateAPIView):
    serializer_class = DailyWellnessEntry
    permission_classes = [IsAuthenticated, IsPlayer]

    def get_queryset(self):
        # Players can only see their own wellness entries
        return DailyWellnessEntry.objects.filter(player=self.request.user).order_by('-entry_date')

    def perform_create(self, serializer):
        # Prevent multiple entries for the same day
        today = date.today()
        if DailyWellnessEntry.objects.filter(player=self.request.user, entry_date=today).exists():
            raise serializers.ValidationError({"detail": "You have already submitted a wellness entry for today."})
        serializer.save(player=self.request.user, entry_date=today)

class PlayerWellnessDetailUpdateView(generics.RetrieveUpdateAPIView):
    queryset = DailyWellnessEntry.objects.all()
    serializer_class = DailyWellnessEntry
    permission_classes = [IsAuthenticated, IsOwnerOrCoachOrAdmin] # Player can update their own, coach/admin can update their team's

    def get_object(self):
        # Allow player to retrieve/update their own entry for the given date
        entry_date = self.kwargs.get('entry_date')
        if not entry_date:
            raise Http404("Date not provided")

        obj = get_object_or_404(
            DailyWellnessEntry,
            player=self.request.user,
            entry_date=entry_date
        )
        self.check_object_permissions(self.request, obj) # Ensures coach/admin check also
        return obj

    def update(self, request, *args, **kwargs):
        # Only allow updates for entries today or very recently, not historical (e.g., 24hr window)
        obj = self.get_object()
        if obj.entry_date != date.today() and (date.today() - obj.entry_date) > timedelta(days=1):
            return Response({"detail": "Cannot update past wellness entries."}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)


class TeamWellnessOverviewListView(generics.ListAPIView):
    serializer_class = TeamWellnessOverviewSerializer
    permission_classes = [IsAuthenticated, IsCoachOrAdmin] # Only coaches/admins can see team overview
    filterset_fields = ['entry_date'] # Allow filtering by date

    def get_queryset(self):
        # Coaches/Admins can see the latest wellness entry for all players in their team
        team = self.request.user.team
        if not team:
            return DailyWellnessEntry.objects.none()

        # Get the latest entry for each player in the team
        # This is a bit complex for default Django ORM, might need raw SQL or a subquery
        # For simplicity in MVP, let's get all entries for the team and let the frontend filter,
        # or filter for a specific date (e.g., today)
        entry_date = self.request.query_params.get('entry_date', str(date.today()))
        return DailyWellnessEntry.objects.filter(player__team=team, entry_date=entry_date).select_related('player')


class PlayerWellnessHistoryView(generics.ListAPIView):
    serializer_class = DailyWellnessEntry
    permission_classes = [IsAuthenticated, IsCoachOrAdmin] # Coaches/Admins can view player history

    def get_queryset(self):
        player_id = self.kwargs['player_id']
        # Ensure the player belongs to the coach's team
        player = get_object_or_404(self.request.user.team.members.filter(role='PLAYER'), pk=player_id)
        return DailyWellnessEntry.objects.filter(player=player).order_by('-entry_date')