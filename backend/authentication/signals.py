from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import User, UserProfile
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=User)
def create_profile_on_user_create(sender, instance, created, **kwargs):
    """
    Automatically create a profile for each new user.
    Django signals cannot be async because the ORM is not async-safe here.
    """
    if created:
        try:
            # Check if profile already exists (in case of race conditions)
            if not hasattr(instance, 'profile') or not UserProfile.objects.filter(user=instance).exists():
                UserProfile.objects.create(user=instance)
                logger.info(f"Profile created for user: {instance.email}")
            else:
                logger.info(f"Profile already exists for user: {instance.email}")
                
        except Exception as e:
            logger.error(f"Failed to create profile for user {instance.email}: {str(e)}")
            # Don't raise the exception to prevent user creation failure
            # In production, you might want to queue this for retry


@receiver(post_save, sender=User)
def send_welcome_email(sender, instance, created, **kwargs):
    """
    Send welcome email to new users.
    """
    if created:
        try:
            subject = "Welcome to Our Platform!"
            message = f"""
            Hello {instance.get_full_name() or instance.username},

            Welcome to our platform! Your account has been created successfully.

            Account Details:
            - Email: {instance.email}
            - Role: {instance.get_role_display()}

            Thank you for joining us!

            Best regards,
            The Team
            """
            
            # Only send if email settings are configured
            if (hasattr(settings, 'EMAIL_HOST_USER') and 
                settings.EMAIL_HOST_USER and
                hasattr(settings, 'EMAIL_HOST_PASSWORD') and
                settings.EMAIL_HOST_PASSWORD):
                
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[instance.email],
                    fail_silently=True  # Don't raise exception if email fails
                )
                logger.info(f"Welcome email sent to: {instance.email}")
            else:
                logger.warning("Email settings not configured, skipping welcome email")
                
        except Exception as e:
            logger.error(f"Failed to send welcome email to {instance.email}: {str(e)}")
            # Don't raise the exception to prevent user creation failure


@receiver(pre_delete, sender=User)
def cleanup_user_data(sender, instance, **kwargs):
    """
    Cleanup user-related data before deleting user.
    """
    try:
        logger.info(f"Cleaning up data for user: {instance.email}")
        
        # Delete profile picture if exists
        if hasattr(instance, 'profile') and instance.profile.profile_picture:
            try:
                instance.profile.profile_picture.delete(save=False)
            except Exception as e:
                logger.error(f"Failed to delete profile picture for {instance.email}: {str(e)}")
        
        logger.info(f"User data cleanup completed for: {instance.email}")
        
    except Exception as e:
        logger.error(f"Failed to cleanup data for user {instance.email}: {str(e)}")


@receiver(post_save, sender=UserProfile)
def log_profile_update(sender, instance, created, **kwargs):
    """
    Log profile updates for audit purposes.
    """
    try:
        if created:
            logger.info(f"New profile created for user: {instance.user.email}")
        else:
            logger.info(f"Profile updated for user: {instance.user.email}")
    except Exception as e:
        logger.error(f"Failed to log profile update: {str(e)}")