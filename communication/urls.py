# communication/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConversationViewSet, MessageListView, AnnouncementViewSet

router = DefaultRouter()
router.register(r'conversations', ConversationViewSet, basename='conversation')
router.register(r'announcements', AnnouncementViewSet, basename='announcement')

urlpatterns = [
    path('', include(router.urls)),
    path('conversations/<int:conversation_id>/messages/', MessageListView.as_view(), name='message_list'),
    # REMOVE manual add_participants path — router now exposes:
    #   POST /communication/conversations/{pk}/add_participants/
    # Router also exposes:
    #   POST /communication/conversations/start_dm/
    # For announcements mark-as-read we keep:
    path('announcements/<int:pk>/read/', AnnouncementViewSet.mark_as_read, name='announcement_mark_as_read'),
]
