from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import User, UserProfile, SellerProfile, UserRole
import logging

logger = logging.getLogger(__name__)

class UserProfileSerializer(serializers.ModelSerializer):
    age = serializers.SerializerMethodField()
    short_bio = serializers.SerializerMethodField()
    profile_picture_url = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            "id", "bio", "phone_number", "address", "profile_picture",
            "profile_picture_url", "date_of_birth", "age", "short_bio",
            "created_at", "updated_at"
        ]
        read_only_fields = ["id", "created_at", "updated_at", "age", "short_bio", "profile_picture_url"]

    def get_age(self, obj):
        try:
            return obj.age
        except Exception as e:
            logger.error(f"Error getting age for profile {obj.id}: {str(e)}")
            return None

    def get_short_bio(self, obj):
        try:
            return obj.short_bio
        except Exception as e:
            logger.error(f"Error getting short bio for profile {obj.id}: {str(e)}")
            return None

    def get_profile_picture_url(self, obj):
        try:
            return obj.profile_picture_url
        except Exception as e:
            logger.error(f"Error getting profile picture URL for profile {obj.id}: {str(e)}")
            return None

    def validate_phone_number(self, value):
        if value:
            # Remove spaces, hyphens, and plus signs for validation
            cleaned = value.replace(' ', '').replace('-', '').replace('+', '')
            if not cleaned.isdigit():
                raise serializers.ValidationError("Phone number should contain only digits, spaces, hyphens, or plus sign.")
            if len(cleaned) < 10 or len(cleaned) > 15:
                raise serializers.ValidationError("Phone number should be between 10 and 15 digits.")
        return value

    def validate_bio(self, value):
        if value and len(value) > 1000:
            raise serializers.ValidationError("Bio cannot exceed 1000 characters.")
        return value


class SellerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = SellerProfile
        fields = [
            "id", "gst_number", "business_name", "business_description", 
            "business_address", "business_phone", "is_verified", 
            "created_at", "updated_at"
        ]
        read_only_fields = ["id", "is_verified", "created_at", "updated_at"]

    def validate_gst_number(self, value):
        if value:
            # Basic GST number validation
            if len(value) != 15:
                raise serializers.ValidationError("GST number must be 15 characters long.")
            if not value.isalnum():
                raise serializers.ValidationError("GST number should contain only alphanumeric characters.")
        return value.upper() if value else value

    def validate_business_name(self, value):
        if value and len(value.strip()) < 2:
            raise serializers.ValidationError("Business name must be at least 2 characters long.")
        return value


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    seller_profile = SellerProfileSerializer(read_only=True)
    full_name = serializers.SerializerMethodField()
    tokens = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "username", "first_name", "last_name", "full_name",
            "email", "role", "auth_provider", "is_active", "created_at",
            "profile", "seller_profile", "tokens"
        ]
        read_only_fields = ["id", "tokens", "created_at"]

    def get_full_name(self, obj):
        try:
            return obj.get_full_name()
        except Exception as e:
            logger.error(f"Error getting full name for user {obj.email}: {str(e)}")
            return obj.username

    def get_tokens(self, obj):
        try:
            return obj.tokens()
        except Exception as e:
            logger.error(f"Error getting tokens for user {obj.email}: {str(e)}")
            return {"refresh": "", "access": ""}


class UserRegisterSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    Includes password + confirm_password validation.
    """
    password = serializers.CharField(
        write_only=True, 
        style={"input_type": "password"},
        help_text="Password must be at least 8 characters long."
    )
    confirm_password = serializers.CharField(
        write_only=True, 
        style={"input_type": "password"}
    )
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    role = serializers.ChoiceField(choices=UserRole.choices)
    
    # Seller specific fields
    gst_number = serializers.CharField(required=False, write_only=True)
    business_name = serializers.CharField(required=False, write_only=True)

    class Meta:
        model = User
        fields = [
            "username", "email", "first_name", "last_name",
            "role", "password", "confirm_password",
            "gst_number", "business_name"
        ]

    def validate_username(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Username must be at least 3 characters long.")
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value

    def validate(self, data):
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        
        # Validate seller specific fields
        if data["role"] == UserRole.SELLER:
            if not data.get("gst_number"):
                raise serializers.ValidationError({"gst_number": "GST number is required for sellers."})
            if not data.get("business_name"):
                raise serializers.ValidationError({"business_name": "Business name is required for sellers."})
            
            # Validate GST number
            gst_number = data["gst_number"].strip()
            if len(gst_number) != 15:
                raise serializers.ValidationError({"gst_number": "GST number must be 15 characters long."})
            if SellerProfile.objects.filter(gst_number=gst_number.upper()).exists():
                raise serializers.ValidationError({"gst_number": "A seller with this GST number already exists."})
        
        return data

    def create(self, validated_data):
        try:
            # Remove non-user fields
            confirm_password = validated_data.pop("confirm_password")
            gst_number = validated_data.pop("gst_number", None)
            business_name = validated_data.pop("business_name", None)
            
            # Create user
            user = User.objects.create_user(**validated_data)
            
            # Create seller profile if needed
            if user.role == UserRole.SELLER and gst_number and business_name:
                SellerProfile.objects.create(
                    user=user,
                    gst_number=gst_number.upper(),
                    business_name=business_name.strip()
                )
            
            logger.info(f"User registered successfully: {user.email}")
            return user
            
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            raise serializers.ValidationError({"error": "Failed to create user. Please try again."})


class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate(self, data):
        try:
            email = data.get("email", "").lower()
            password = data.get("password", "")
            
            if not email or not password:
                raise serializers.ValidationError("Email and password are required.")
            
            # Try to authenticate with email
            user = authenticate(username=email, password=password)
            if not user:
                # Try to find user by email and check password manually
                try:
                    user = User.objects.get(email=email)
                    if not user.check_password(password):
                        user = None
                except User.DoesNotExist:
                    user = None
            
            if not user:
                raise serializers.ValidationError("Invalid email or password.")
            
            if not user.is_active:
                raise serializers.ValidationError("User account is disabled.")
            
            data["user"] = user
            return data
            
        except serializers.ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error during login validation: {str(e)}")
            raise serializers.ValidationError("Login failed. Please try again.")


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, style={"input_type": "password"})
    new_password = serializers.CharField(write_only=True, style={"input_type": "password"})
    confirm_new_password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value

    def validate_new_password(self, value):
        try:
            validate_password(value, self.context['request'].user)
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value

    def validate(self, data):
        if data['new_password'] != data['confirm_new_password']:
            raise serializers.ValidationError({"new_password": "New passwords do not match."})
        return data

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user