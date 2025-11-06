from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EventViewSet, AttendanceListView, AttendanceUpdateView

router = DefaultRouter()
router.register(r'events', EventViewSet, basename='event')

urlpatterns = [
    path('', include(router.urls)),
    path('events/<int:event_id>/attendance/', AttendanceListView.as_view(), name='event_attendance_list'),
    path('events/<int:event_id>/attendance/<int:player_id>/', AttendanceUpdateView.as_view(), name='event_attendance_update'),
]