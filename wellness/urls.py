from django.urls import path
from .views import (
    PlayerWellnessEntryView,
    PlayerWellnessDetailUpdateView,
    TeamWellnessOverviewListView,
    PlayerWellnessHistoryView
)

urlpatterns = [
    # Player specific views
    path('mine/', PlayerWellnessEntryView.as_view(), name='player_wellness_list_create'),
    path('mine/<str:entry_date>/', PlayerWellnessDetailUpdateView.as_view(), name='player_wellness_detail_update'), # Format YYYY-MM-DD

    # Coach/Admin specific views
    path('team/', TeamWellnessOverviewListView.as_view(), name='team_wellness_overview'), # For listing today's wellness for all players
    path('player/<int:player_id>/history/', PlayerWellnessHistoryView.as_view(), name='player_wellness_history'),
]