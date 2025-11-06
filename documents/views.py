from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q

from .models import Document
from .serializers import DocumentSerializer
from users.permissions import IsCoachOrAdmin, IsAdmin, IsTeamMember # Adjust import path

class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_admin():
            return self.queryset # Admins can see all documents
        elif user.is_coach() or user.is_staff_member():
            # Coaches/staff can see documents uploaded to their team
            # and documents explicitly shared with them (if they were players in another team, though unlikely)
            return self.queryset.filter(Q(team=user.team) | Q(shared_with_players=user)).distinct()
        elif user.is_player():
            # Players can see documents uploaded to their team AND explicitly shared with them
            return self.queryset.filter(Q(team=user.team) | Q(shared_with_players=user)).distinct()
        return self.queryset.none() # No team or role

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            # Only coaches/admins/staff can upload/manage documents
            self.permission_classes = [IsAuthenticated, IsCoachOrAdmin]
            if self.action == 'destroy': # Potentially only Admin can delete some docs
                self.permission_classes = [IsAuthenticated, IsAdmin] # Or allow uploader to delete their own
        return super().get_permissions()

    def perform_create(self, serializer):
        user = self.request.user
        team_instance = serializer.validated_data.get('team')

        if user.is_coach() or user.is_staff_member():
            # Coaches/Staff can upload for their own team
            if team_instance and team_instance != user.team:
                self.permission_denied(self.request, message="You can only upload documents for your own team.")
            serializer.save(uploaded_by=user, team=user.team)
        elif user.is_admin():
            # Admins can upload for any team (team can be provided in payload)
            if not team_instance: # If admin doesn't specify team, it's a global doc or needs explicit shares
                 serializer.save(uploaded_by=user)
            else:
                serializer.save(uploaded_by=user, team=team_instance)
        else:
            self.permission_denied(self.request, message="Only authorized personnel can upload documents.")