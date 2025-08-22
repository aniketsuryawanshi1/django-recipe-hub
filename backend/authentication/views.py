from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.throttling import AnonRateThrottle
from django.db import DatabaseError, transaction
from django.core.exceptions import ObjectDoesNotExist, ValidationError as DjangoValidationError
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework.serializers import ValidationError as DRFValidationError

from .models import User, UserProfile, UserRole, SellerProfile
from .serializers import (
    UserSerializer, UserProfileSerializer, UserRegisterSerializer,
    UserLoginSerializer, PasswordChangeSerializer
)
from .throttling import CustomerRateThrottle, SellerRateThrottle
import logging

logger = logging.getLogger(__name__)

class RegisterView(APIView):
    """
    Register a new Customer or Seller.
    """
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]
    
    def post(self, request, *args, **kwargs):
        """
        Register a new Customer or Seller.
        Only return a success message (no user details for security).
        """
        try:
            serializer = UserRegisterSerializer(data=request.data)
            
            if not serializer.is_valid():
                logger.warning(f"Registration failed - validation errors: {serializer.errors}")
                return Response(
                    {"error": "Validation failed", "details": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )

            with transaction.atomic():
                user = serializer.save()
                logger.info(f"User registered successfully: {user.email}")
                
                return Response(
                    {
                        "message": _("User registered successfully. Please login to continue."),
                        "user_id": str(user.id),
                        "email": user.email
                    },
                    status=status.HTTP_201_CREATED
                )

        except DRFValidationError as e:
            logger.error(f"DRF Validation error during registration: {str(e)}")
            return Response(
                {"error": "Registration failed", "details": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except DatabaseError as e:
            logger.error(f"Database error during registration: {str(e)}")
            return Response(
                {"error": _("Database error occurred. Please try again.")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            logger.error(f"Unexpected error during registration: {str(e)}")
            return Response(
                {"error": _("Unexpected error occurred during registration. Please try again.")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LoginView(APIView):
    """
    Authenticate user and return JWT tokens.
    """
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def post(self, request, *args, **kwargs):
        """
        Authenticate user and return JWT tokens with user data.
        """
        try:
            serializer = UserLoginSerializer(data=request.data)
            
            if not serializer.is_valid():
                logger.warning(f"Login failed - validation errors: {serializer.errors}")
                return Response(
                    {"error": "Login failed", "details": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user = serializer.validated_data['user']
            
            try:
                refresh = RefreshToken.for_user(user)
                user_serializer = UserSerializer(user, context={"request": request})
                
                logger.info(f"User logged in successfully: {user.email}")
                
                return Response(
                    {
                        "message": _("Login successful."),
                        "refresh": str(refresh),
                        "access": str(refresh.access_token),
                        "user": user_serializer.data,
                    },
                    status=status.HTTP_200_OK
                )
                
            except Exception as token_error:
                logger.error(f"Error generating tokens for user {user.email}: {str(token_error)}")
                return Response(
                    {"error": _("Failed to generate authentication tokens.")},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except DatabaseError as e:
            logger.error(f"Database error during login: {str(e)}")
            return Response(
                {"error": _("Database error occurred. Please try again.")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            logger.error(f"Unexpected error during login: {str(e)}")
            return Response(
                {"error": _("Unexpected error occurred during login. Please try again.")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CurrentUserView(APIView):
    """
    Get details of the authenticated user.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [CustomerRateThrottle, SellerRateThrottle]

    def get(self, request, *args, **kwargs):
        """
        Get details of the authenticated user.
        """
        try:
            serializer = UserSerializer(request.user, context={"request": request})
            return Response(
                {
                    "message": "User details retrieved successfully.",
                    "user": serializer.data
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Error fetching user details for {request.user.email}: {str(e)}")
            return Response(
                {"error": _("Unable to fetch user details. Please try again.")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProfileUpdateView(APIView):
    """
    Update authenticated user's profile.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [CustomerRateThrottle, SellerRateThrottle]

    def get(self, request, *args, **kwargs):
        """
        Get current user's profile.
        """
        try:
            profile, created = UserProfile.objects.get_or_create(user=request.user)
            if created:
                logger.info(f"Profile created for user {request.user.email}")
            
            serializer = UserProfileSerializer(profile, context={"request": request})
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error fetching profile for user {request.user.email}: {str(e)}")
            return Response(
                {"error": _("Unable to fetch profile. Please try again.")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def put(self, request, *args, **kwargs):
        """
        Update logged-in user's profile.
        """
        try:
            profile, created = UserProfile.objects.get_or_create(user=request.user)
            
            serializer = UserProfileSerializer(
                profile, 
                data=request.data, 
                partial=True, 
                context={"request": request}
            )
            
            if serializer.is_valid():
                with transaction.atomic():
                    serializer.save()
                    logger.info(f"Profile updated for user {request.user.email}")
                    
                    return Response(
                        {
                            "message": "Profile updated successfully.",
                            "profile": serializer.data
                        },
                        status=status.HTTP_200_OK
                    )
            else:
                logger.warning(f"Profile update failed for {request.user.email}: {serializer.errors}")
                return Response(
                    {"error": "Profile update failed", "details": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )

        except DjangoValidationError as e:
            logger.error(f"Validation error updating profile for {request.user.email}: {str(e)}")
            return Response(
                {"error": "Validation failed", "details": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except DatabaseError as e:
            logger.error(f"Database error updating profile for {request.user.email}: {str(e)}")
            return Response(
                {"error": _("Database error occurred. Please try again.")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            logger.error(f"Unexpected error updating profile for {request.user.email}: {str(e)}")
            return Response(
                {"error": _("Profile update failed. Please try again.")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def patch(self, request, *args, **kwargs):
        """
        Partially update logged-in user's profile.
        """
        return self.put(request, *args, **kwargs)


class ChangePasswordView(APIView):
    """
    Change user's password.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [CustomerRateThrottle, SellerRateThrottle]

    def post(self, request, *args, **kwargs):
        """
        Change user's password.
        """
        try:
            serializer = PasswordChangeSerializer(
                data=request.data,
                context={'request': request}
            )
            
            if serializer.is_valid():
                with transaction.atomic():
                    serializer.save()
                    logger.info(f"Password changed for user {request.user.email}")
                    
                    return Response(
                        {"message": "Password changed successfully."},
                        status=status.HTTP_200_OK
                    )
            else:
                logger.warning(f"Password change failed for {request.user.email}: {serializer.errors}")
                return Response(
                    {"error": "Password change failed", "details": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )

        except Exception as e:
            logger.error(f"Error changing password for {request.user.email}: {str(e)}")
            return Response(
                {"error": _("Failed to change password. Please try again.")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LogoutView(APIView):
    """
    Logout user by blacklisting the refresh token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """
        Logout user by blacklisting refresh token.
        """
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response(
                    {"error": "Refresh token is required."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            token = RefreshToken(refresh_token)
            token.blacklist()
            
            logger.info(f"User logged out: {request.user.email}")
            
            return Response(
                {"message": "Logged out successfully."},
                status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(f"Error during logout for {request.user.email}: {str(e)}")
            return Response(
                {"error": _("Logout failed. Please try again.")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )