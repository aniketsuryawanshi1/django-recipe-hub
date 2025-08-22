from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import User, UserProfile, SellerProfile, UserRole
import logging

logger = logging.getLogger(__name__)

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User Admin"""
    
    list_display = (
        'email', 'username', 'get_full_name', 'role', 
        'is_active', 'is_staff', 'created_at', 'profile_link'
    )
    list_filter = ('role', 'is_active', 'is_staff', 'is_superuser', 'created_at')
    search_fields = ('email', 'username', 'first_name', 'last_name')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at', 'updated_at', 'last_login')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'email', 'username', 'first_name', 'last_name')
        }),
        ('User Type', {
            'fields': ('role',)
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Authentication', {
            'fields': ('auth_provider', 'last_login'),
            'classes': ('collapse',)
        }),
        ('Important dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        ('Create New User', {
            'classes': ('wide',),
            'fields': ('email', 'username', 'first_name', 'last_name', 'role', 'password1', 'password2'),
        }),
        ('Permissions', {
            'classes': ('wide', 'collapse'),
            'fields': ('is_active', 'is_staff', 'is_superuser'),
        }),
    )
    
    filter_horizontal = ('groups', 'user_permissions')
    
    def get_full_name(self, obj):
        """Display full name"""
        return obj.get_full_name() or '-'
    get_full_name.short_description = 'Full Name'
    
    def profile_link(self, obj):
        """Link to user profile"""
        try:
            if hasattr(obj, 'profile'):
                url = reverse('admin:authentication_userprofile_change', args=[obj.profile.id])
                return format_html('<a href="{}">View Profile</a>', url)
            return '-'
        except Exception as e:
            logger.error(f"Error creating profile link for user {obj.email}: {str(e)}")
            return '-'
    profile_link.short_description = 'Profile'
    
    def get_queryset(self, request):
        """Optimize queries"""
        return super().get_queryset(request).select_related('profile')
    
    def save_model(self, request, obj, form, change):
        """Custom save logic"""
        try:
            super().save_model(request, obj, form, change)
            if not change:  # New user
                logger.info(f"New user created by admin: {obj.email}")
        except Exception as e:
            logger.error(f"Error saving user in admin: {str(e)}")
            raise


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """User Profile Admin"""
    
    list_display = (
        'user_email', 'user_username', 'phone_number', 
        'age', 'profile_picture_preview', 'created_at'
    )
    list_filter = ('created_at', 'updated_at')
    search_fields = ('user__email', 'user__username', 'phone_number')
    readonly_fields = ('id', 'age', 'created_at', 'updated_at', 'profile_picture_preview')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('User Information', {
            'fields': ('id', 'user')
        }),
        ('Profile Details', {
            'fields': ('bio', 'phone_number', 'address', 'date_of_birth', 'age')
        }),
        ('Profile Picture', {
            'fields': ('profile_picture', 'profile_picture_preview'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_email(self, obj):
        """Display user email"""
        return obj.user.email
    user_email.short_description = 'Email'
    user_email.admin_order_field = 'user__email'
    
    def user_username(self, obj):
        """Display username"""
        return obj.user.username
    user_username.short_description = 'Username'
    user_username.admin_order_field = 'user__username'
    
    def profile_picture_preview(self, obj):
        """Display profile picture preview"""
        try:
            if obj.profile_picture:
                return format_html(
                    '<img src="{}" width="50" height="50" style="border-radius: 50%; object-fit: cover;" />',
                    obj.profile_picture.url
                )
            return '-'
        except Exception as e:
            logger.error(f"Error displaying profile picture for {obj.user.email}: {str(e)}")
            return 'Error loading image'
    profile_picture_preview.short_description = 'Picture'
    
    def get_queryset(self, request):
        """Optimize queries"""
        return super().get_queryset(request).select_related('user')


@admin.register(SellerProfile)
class SellerProfileAdmin(admin.ModelAdmin):
    """Seller Profile Admin"""
    
    list_display = (
        'business_name', 'user_email', 'gst_number', 
        'is_verified', 'created_at'
    )
    list_filter = ('is_verified', 'created_at', 'updated_at')
    search_fields = ('business_name', 'gst_number', 'user__email', 'user__username')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'business_name')
        }),
        ('Business Details', {
            'fields': ('gst_number', 'business_description', 'business_address', 'business_phone')
        }),
        ('Verification', {
            'fields': ('is_verified',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_email(self, obj):
        """Display user email"""
        return obj.user.email
    user_email.short_description = 'User Email'
    user_email.admin_order_field = 'user__email'
    
    def get_queryset(self, request):
        """Optimize queries"""
        return super().get_queryset(request).select_related('user')
    
    actions = ['verify_sellers', 'unverify_sellers']
    
    def verify_sellers(self, request, queryset):
        """Bulk verify sellers"""
        try:
            updated = queryset.update(is_verified=True)
            self.message_user(request, f'{updated} sellers verified successfully.')
            logger.info(f"Admin {request.user.email} verified {updated} sellers")
        except Exception as e:
            logger.error(f"Error verifying sellers: {str(e)}")
            self.message_user(request, f'Error verifying sellers: {str(e)}', level='ERROR')
    verify_sellers.short_description = "Verify selected sellers"
    
    def unverify_sellers(self, request, queryset):
        """Bulk unverify sellers"""
        try:
            updated = queryset.update(is_verified=False)
            self.message_user(request, f'{updated} sellers unverified successfully.')
            logger.info(f"Admin {request.user.email} unverified {updated} sellers")
        except Exception as e:
            logger.error(f"Error unverifying sellers: {str(e)}")
            self.message_user(request, f'Error unverifying sellers: {str(e)}', level='ERROR')
    unverify_sellers.short_description = "Unverify selected sellers"


# Customize admin site
admin.site.site_header = "Recipe Platform Admin"
admin.site.site_title = "Recipe Platform Admin Portal"
admin.site.index_title = "Welcome to Recipe Platform Administration"