from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConversationViewSet, MessageListView, AnnouncementViewSet

router = DefaultRouter()
router.register(r'conversations', ConversationViewSet, basename='conversation')
router.register(r'announcements', AnnouncementViewSet, basename='announcement')

urlpatterns = [
    path('', include(router.urls)),
    path('conversations/<int:conversation_id>/messages/', MessageListView.as_view(), name='message_list'),
    path('conversations/<int:pk>/add_participants/', ConversationViewSet.add_participants, name='conversation_add_participants'), # Custom action
    path('announcements/<int:pk>/read/', AnnouncementViewSet.mark_as_read, name='announcement_mark_as_read'), # Custom action
]