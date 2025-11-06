from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TeamViewSet, TeamSquadListView, TeamStaffListView

router = DefaultRouter()
router.register(r'', TeamViewSet, basename='team') # No prefix, so /api/teams/

urlpatterns = [
    path('', include(router.urls)),
    path('<int:pk>/squad/', TeamSquadListView.as_view(), name='team_squad_list'),
    path('<int:pk>/staff/', TeamStaffListView.as_view(), name='team_staff_list'),
]