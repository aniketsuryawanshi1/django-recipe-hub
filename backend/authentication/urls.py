from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from .views import (
    RegisterView, LoginView, CurrentUserView, ProfileUpdateView, 
    ChangePasswordView, LogoutView
)

app_name = 'authentication'

urlpatterns = [
    # Authentication endpoints
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),

    # JWT token endpoints
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),

    # User management endpoints
    path("user/current/", CurrentUserView.as_view(), name="current_user"),
    path("user/profile/", ProfileUpdateView.as_view(), name="profile_update"),
    path("user/change-password/", ChangePasswordView.as_view(), name="change_password"),
]