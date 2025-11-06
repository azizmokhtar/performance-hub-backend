from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404

from .models import CustomUser
from .serializers import (
    UserRegisterSerializer,
    UserLoginSerializer,
    UserProfileSerializer,
    UserTeamListSerializer
)
from users.permissions import (
    IsCoachOrAdmin, IsSelfOrCoachOrAdmin, IsTeamMember
) # Adjust import path as necessary

class UserRegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserRegisterSerializer
    permission_classes = [AllowAny] # Or IsAdmin if only admins can register users

class UserLoginView(generics.GenericAPIView):
    serializer_class = UserLoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        user = authenticate(request, email=email, password=password)

        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': UserProfileSerializer(user).data
            }, status=status.HTTP_200_OK)
        else:
            return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)



class UserLogoutView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Must receive a refresh token in body
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"detail": "Missing 'refresh' token in request body."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = RefreshToken(refresh_token)
            # Blacklist the refresh token (requires token_blacklist app + migrations)
            token.blacklist()
        except TokenError as e:
            # Invalid / already blacklisted / expired
            return Response(
                {"detail": f"Invalid refresh token: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except AttributeError:
            # If token_blacklist is not installed, .blacklist() doesn't exist
            # Treat logout as stateless success (client will drop tokens)
            return Response(status=status.HTTP_205_RESET_CONTENT)

        # 205: client should reset state (you already clear store + navigate)
        return Response(status=status.HTTP_205_RESET_CONTENT)


class UserChangePasswordView(generics.UpdateAPIView):
    serializer_class = UserProfileSerializer # Reuse for password validation logic
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        self.object = self.get_object()
        serializer = self.get_serializer(data=request.data, partial=True) # Partial update
        serializer.is_valid(raise_exception=True)
        self.object.set_password(serializer.validated_data['password'])
        self.object.save()
        return Response({"detail": "Password updated successfully."}, status=status.HTTP_200_OK)

# Password reset functionality typically involves sending an email,
# which is more complex and might be deferred post-MVP or use a library like `djoser`.
# For now, we'll keep the view endpoint but without full implementation.
class UserPasswordResetRequestView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    def post(self, request):
        # Placeholder: In a real app, this would trigger an email with a reset link
        return Response({"detail": "Password reset email sent (placeholder)."}, status=status.HTTP_200_OK)

class UserProfileMeView(generics.RetrieveUpdateAPIView):
    queryset = CustomUser.objects.all() # Redundant, but good practice
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

class UserProfileDetailView(generics.RetrieveUpdateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated, IsSelfOrCoachOrAdmin]

class UsersByTeamListView(generics.ListAPIView):
    serializer_class = UserTeamListSerializer
    permission_classes = [IsAuthenticated, IsCoachOrAdmin] # Only coaches/admins can list team members

    def get_queryset(self):
        team_id = self.kwargs['team_id']
        team = get_object_or_404(self.request.user.team.all(), id=team_id) if self.request.user.team else None # For multi-team scenario
        # If user is admin, they can see any team. If coach, only their team.
        if self.request.user.is_admin():
            return CustomUser.objects.filter(team_id=team_id)
        elif self.request.user.is_coach() and self.request.user.team.id == team_id:
            return CustomUser.objects.filter(team_id=team_id)
        return CustomUser.objects.none() # No permission