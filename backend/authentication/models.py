from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser, BaseUserManager, PermissionsMixin, Group, Permission
)
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import date
import uuid
import logging

logger = logging.getLogger(__name__)

AUTH_PROVIDERS = {
    'email': 'email'
}

class UserRole(models.TextChoices):
    CUSTOMER = 'customer', _('Customer')
    SELLER = 'seller', _('Seller')

class UserManager(BaseUserManager):
    def create_user(self, username, email, password=None, role=None, **extra_fields):
        """
        Create and return a regular user with an email and password.
        """
        try:
            if not email:
                raise ValueError('Please provide an email address')
            if not username:
                raise ValueError('Please provide a username')
            if not role:
                raise ValueError('Please provide a user role')

            # Validate role
            if role not in [choice[0] for choice in UserRole.choices]:
                raise ValueError(f'Invalid role: {role}')

            email = self.normalize_email(email)
            user = self.model(
                username=username,
                email=email,
                role=role,
                **extra_fields
            )
            user.set_password(password)
            user.save(using=self._db)
            logger.info(f"User created successfully: {email}")
            return user
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            raise

    def create_superuser(self, username, email, password=None, role=None, **extra_fields):
        """
        Create and return a superuser with an email and password.
        """
        try:
            extra_fields.setdefault('is_staff', True)
            extra_fields.setdefault('is_superuser', True)
            extra_fields.setdefault('is_active', True)
            
            if extra_fields.get('is_staff') is not True:
                raise ValueError('Superuser must have is_staff=True.')
            if extra_fields.get('is_superuser') is not True:
                raise ValueError('Superuser must have is_superuser=True.')
            
            if not role:
                role = UserRole.CUSTOMER  # Default to customer if not provided
                
            return self.create_user(username, email, password, role, **extra_fields)
        except Exception as e:
            logger.error(f"Error creating superuser: {str(e)}")
            raise

class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=255, db_index=True)  # Not unique
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(max_length=255, unique=True, db_index=True)
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.CUSTOMER,
        db_index=True
    )
    is_staff = models.BooleanField(default=False, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    is_superuser = models.BooleanField(default=False)
    auth_provider = models.CharField(max_length=50, default=AUTH_PROVIDERS.get('email'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'role']

    objects = UserManager()

    class Meta:
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["username"]),
            models.Index(fields=["role"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["role", "is_active"]),
            models.Index(fields=["username", "email"]),
            models.Index(fields=["created_at"]),
        ]
        ordering = ["-created_at"]

    def clean(self):
        """
        Validate the model before saving.
        """
        super().clean()
        if self.role and self.role not in [choice[0] for choice in UserRole.choices]:
            raise ValidationError({'role': 'Invalid role selected.'})
        
        if self.email:
            self.email = self.email.lower()

    def save(self, *args, **kwargs):
        """
        Override save method to include validation.
        """
        try:
            self.full_clean()
            super().save(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error saving user {self.email}: {str(e)}")
            raise

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"

    @property
    def is_customer(self):
        return self.role == UserRole.CUSTOMER

    @property
    def is_seller(self):
        return self.role == UserRole.SELLER

    def get_full_name(self):
        """
        Return the full name for the user.
        """
        full_name = f"{self.first_name or ''} {self.last_name or ''}".strip()
        return full_name if full_name else self.username

    def get_short_name(self):
        """
        Return the short name for the user.
        """
        return self.first_name or self.username

    def tokens(self):
        """
        Generate JWT tokens for the user.
        """
        try:
            refresh = RefreshToken.for_user(self)
            return {
                'refresh': str(refresh), 
                'access': str(refresh.access_token)
            }
        except Exception as e:
            logger.error(f"Error generating tokens for user {self.email}: {str(e)}")
            raise

    # Fix for Django's auth system compatibility
    groups = models.ManyToManyField(
        Group, 
        related_name='custom_auth_users', 
        blank=True,
        help_text='The groups this user belongs to.'
    )
    user_permissions = models.ManyToManyField(
        Permission, 
        related_name='custom_auth_users', 
        blank=True,
        help_text='Specific permissions for this user.'
    )

class UserProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    bio = models.TextField(blank=True, null=True, max_length=1000)
    phone_number = models.CharField(max_length=15, blank=True, null=True, db_index=True)
    address = models.TextField(blank=True, null=True, max_length=500)
    profile_picture = models.ImageField(upload_to="profiles/", blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["phone_number"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["user", "phone_number"]),
        ]
        ordering = ["-created_at"]

    def clean(self):
        """
        Validate the model before saving.
        """
        super().clean()
        if self.date_of_birth and self.date_of_birth > date.today():
            raise ValidationError({'date_of_birth': 'Date of birth cannot be in the future.'})
        
        # Validate phone number format (basic validation)
        if self.phone_number and not self.phone_number.replace('+', '').replace('-', '').replace(' ', '').isdigit():
            raise ValidationError({'phone_number': 'Enter a valid phone number.'})

    def save(self, *args, **kwargs):
        """
        Override save method to include validation.
        """
        try:
            self.full_clean()
            super().save(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error saving profile for user {self.user.email}: {str(e)}")
            raise

    def __str__(self):
        return f"Profile of {self.user.username}"

    @property
    def age(self):
        """
        Calculate age based on date of birth.
        """
        if self.date_of_birth:
            try:
                today = date.today()
                return today.year - self.date_of_birth.year - (
                    (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
                )
            except Exception as e:
                logger.error(f"Error calculating age for user {self.user.email}: {str(e)}")
                return None
        return None

    @property
    def profile_picture_url(self):
        """
        Return profile picture URL if exists.
        """
        try:
            return self.profile_picture.url if self.profile_picture else None
        except Exception as e:
            logger.error(f"Error getting profile picture URL for user {self.user.email}: {str(e)}")
            return None

    @property
    def short_bio(self):
        """
        Return truncated bio.
        """
        if self.bio and len(self.bio) > 50:
            return self.bio[:50] + "..."
        return self.bio

class SellerProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="seller_profile")
    gst_number = models.CharField(max_length=50, unique=True, db_index=True)
    business_name = models.CharField(max_length=255, db_index=True)
    business_description = models.TextField(blank=True, null=True, max_length=1000)
    business_address = models.TextField(blank=True, null=True, max_length=500)
    business_phone = models.CharField(max_length=15, blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["gst_number"]),
            models.Index(fields=["business_name"]),
            models.Index(fields=["is_verified"]),
            models.Index(fields=["created_at"]),
        ]
        ordering = ["-created_at"]

    def clean(self):
        """
        Validate the model before saving.
        """
        super().clean()
        # Basic GST number validation (15 characters)
        if self.gst_number and len(self.gst_number) != 15:
            raise ValidationError({'gst_number': 'GST number must be 15 characters long.'})
        
        # Ensure user is a seller
        if self.user and self.user.role != UserRole.SELLER:
            raise ValidationError({'user': 'User must be a seller to have a seller profile.'})

    def save(self, *args, **kwargs):
        """
        Override save method to include validation.
        """
        try:
            self.full_clean()
            super().save(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error saving seller profile for user {self.user.email}: {str(e)}")
            raise

    def __str__(self):
        return f"SellerProfile: {self.business_name} ({self.gst_number})"