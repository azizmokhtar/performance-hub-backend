from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TeamViewSet, TeamSquadListView, TeamStaffListView, MyTeamView

router = DefaultRouter()
router.register(r'', TeamViewSet, basename='team') # No prefix, so /api/teams/

urlpatterns = [
    path('my/', MyTeamView.as_view(), name='team_my'),
    path('', include(router.urls)),
    path('<int:pk>/squad/', TeamSquadListView.as_view(), name='team_squad_list'),
    path('<int:pk>/staff/', TeamStaffListView.as_view(), name='team_staff_list'),
]