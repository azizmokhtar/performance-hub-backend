from django.urls import path
from .views import (
    UserRegisterView,
    UserLoginView,
    UserLogoutView,
    UserChangePasswordView,
    UserProfileMeView,
    UserProfileDetailView,
    UsersByTeamListView,
    UserPasswordResetRequestView,
    UsersListAllView, 
)

urlpatterns = [
    path('auth/register/', UserRegisterView.as_view(), name='user_register'),
    path('auth/login/',    UserLoginView.as_view(),    name='user_login'),
    path('auth/logout/',   UserLogoutView.as_view(),   name='user_logout'),
    path('auth/password/change/', UserChangePasswordView.as_view(), name='user_change_password'),
    path('auth/password/reset/',  UserPasswordResetRequestView.as_view(), name='user_password_reset_request'),

    path('me/', UserProfileMeView.as_view(), name='user_profile_me'),
    path('admin/list/', UsersListAllView.as_view(), name='users_admin_list'),
    path('team/<int:team_id>/', UsersByTeamListView.as_view(), name='users_by_team_list'),
    path('<int:pk>/', UserProfileDetailView.as_view(), name='user_profile_detail'),
]
