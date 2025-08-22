from celery import shared_task
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta
import csv
import os
from PIL import Image, ImageOps
from .models import Recipe, RecipeImage
from .utils import resize_image
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

@shared_task(bind=True, max_retries=3)
def process_recipe_image(self, recipe_image_id):
    """
    Asynchronous task to resize recipe image after upload
    """
    try:
        recipe_image = RecipeImage.objects.get(id=recipe_image_id)
        
        if not recipe_image.image:
            logger.warning(f"No image found for RecipeImage {recipe_image_id}")
            return f"No image found for RecipeImage {recipe_image_id}"
        
        # Get original image path
        original_path = recipe_image.image.path
        
        if not os.path.exists(original_path):
            logger.error(f"Image file not found: {original_path}")
            return f"Image file not found: {original_path}"
        
        # Open and process image
        with Image.open(original_path) as img:
            # Convert to RGB if necessary (for JPEG compatibility)
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # Auto-orient image based on EXIF data
            img = ImageOps.exif_transpose(img)
            
            # Resize image while maintaining aspect ratio
            max_size = (800, 600)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Save the optimized image back to the same path
            img.save(original_path, 'JPEG', quality=85, optimize=True)
            
            logger.info(f"Recipe image processed successfully: {recipe_image_id}")
            return f"Image processed successfully for RecipeImage {recipe_image_id}"
        
    except RecipeImage.DoesNotExist:
        logger.error(f"RecipeImage not found: {recipe_image_id}")
        return f"RecipeImage not found: {recipe_image_id}"
    except Exception as exc:
        logger.error(f"Error processing recipe image {recipe_image_id}: {str(exc)}")
        # Retry task if it fails
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (self.request.retries + 1))
        return f"Failed to process image after {self.max_retries} retries: {str(exc)}"

@shared_task(bind=True)
def send_daily_email(self):
    """
    Send daily email to all users (except weekends)
    Scheduled to run at 6:00 AM every day
    """
    try:
        now = timezone.now()
        
        # Skip weekends (Saturday=5, Sunday=6)
        if now.weekday() in [5, 6]:
            logger.info("Skipping daily email on weekend")
            return "Skipped - Weekend"
        
        # Get all active users
        users = User.objects.filter(is_active=True).select_related('profile')
        
        if not users.exists():
            logger.info("No active users found for daily email")
            return "No users"
        
        # Get recent recipes (last 7 days)
        week_ago = now - timedelta(days=7)
        recent_recipes = Recipe.objects.filter(
            created_at__gte=week_ago,
            is_published=True
        ).select_related('author', 'category').prefetch_related('images')[:5]
        
        # Get featured recipes
        featured_recipes = Recipe.objects.filter(
            is_published=True,
            is_featured=True
        ).select_related('author', 'category').prefetch_related('images')[:3]
        
        email_subject = f"Daily Recipe Updates - {now.strftime('%B %d, %Y')}"
        
        sent_count = 0
        failed_count = 0
        
        for user in users:
            try:
                # Prepare context for email template
                context = {
                    'user': user,
                    'recent_recipes': recent_recipes,
                    'featured_recipes': featured_recipes,
                    'date': now,
                    'site_name': 'Recipe Platform',
                }
                
                # Create plain text content
                text_content = f"""
Dear {user.get_full_name() or user.username},

Here are your daily recipe updates for {now.strftime('%B %d, %Y')}:

Recent Recipes:
"""
                
                for recipe in recent_recipes:
                    text_content += f"- {recipe.title} by {recipe.author.get_full_name() or recipe.author.username}\n"
                
                if featured_recipes:
                    text_content += "\nFeatured Recipes:\n"
                    for recipe in featured_recipes:
                        text_content += f"- {recipe.title} by {recipe.author.get_full_name() or recipe.author.username}\n"
                
                text_content += f"""

Visit our platform to explore more recipes!

Best regards,
Recipe Platform Team
"""
                
                # Send email
                send_mail(
                    subject=email_subject,
                    message=text_content,
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
                
                sent_count += 1
                logger.info(f"Daily email sent to {user.email}")
                
            except Exception as e:
                logger.error(f"Failed to send daily email to {user.email}: {str(e)}")
                failed_count += 1
        
        result = f"Daily emails sent: {sent_count}, Failed: {failed_count}"
        logger.info(result)
        return result
        
    except Exception as e:
        logger.error(f"Error in send_daily_email task: {str(e)}")
        return f"Error: {str(e)}"

@shared_task(bind=True)
def export_user_data_weekly(self):
    """
    Weekly task to export user data to CSV
    Runs every Sunday at 2:00 AM
    """
    try:
        now = timezone.now()
        
        # Create CSV filename with timestamp
        filename = f"user_data_export_{now.strftime('%Y%m%d_%H%M%S')}.csv"
        exports_dir = os.path.join(settings.MEDIA_ROOT, 'exports')
        
        # Create exports directory if it doesn't exist
        os.makedirs(exports_dir, exist_ok=True)
        
        filepath = os.path.join(exports_dir, filename)
        
        # Get all users with related data
        users = User.objects.select_related().prefetch_related(
            'recipes', 'ratings', 'favorites'
        ).all()
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'user_id', 'username', 'email', 'role', 'is_active',
                'full_name', 'created_at', 'last_login',
                'total_recipes', 'total_ratings_given', 'total_favorites',
                'avg_rating_received'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            exported_count = 0
            
            for user in users:
                try:
                    # Calculate user statistics
                    total_recipes = user.recipes.count() if hasattr(user, 'recipes') else 0
                    total_ratings_given = user.ratings.count() if hasattr(user, 'ratings') else 0
                    total_favorites = user.favorites.count() if hasattr(user, 'favorites') else 0
                    
                    # Calculate average rating received for seller's recipes
                    avg_rating_received = 0
                    if user.role == 'seller' and total_recipes > 0:
                        from django.db.models import Avg
                        avg_data = Recipe.objects.filter(author=user).aggregate(
                            avg_rating=Avg('ratings__rating')
                        )
                        avg_rating_received = round(avg_data['avg_rating'] or 0, 2)
                    
                    writer.writerow({
                        'user_id': str(user.id),
                        'username': user.username,
                        'email': user.email,
                        'role': user.role,
                        'is_active': user.is_active,
                        'full_name': user.get_full_name(),
                        'created_at': user.created_at.strftime('%Y-%m-%d %H:%M:%S') if user.created_at else '',
                        'last_login': user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else '',
                        'total_recipes': total_recipes,
                        'total_ratings_given': total_ratings_given,
                        'total_favorites': total_favorites,
                        'avg_rating_received': avg_rating_received
                    })
                    
                    exported_count += 1
                    
                except Exception as e:
                    logger.error(f"Error exporting user {user.email}: {str(e)}")
                    continue
        
        result = f"User data exported: {exported_count} users to {filename}"
        logger.info(result)
        
        # Send notification email to admins
        try:
            admin_users = User.objects.filter(is_superuser=True)
            if admin_users.exists():
                send_mail(
                    subject='Weekly User Data Export Completed',
                    message=f'Weekly user data export has been completed.\n\nFile: {filename}\nUsers exported: {exported_count}\nLocation: {filepath}',
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[admin.email for admin in admin_users],
                    fail_silently=True
                )
        except Exception as e:
            logger.error(f"Failed to send export notification: {str(e)}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in export_user_data_weekly task: {str(e)}")
        return f"Error: {str(e)}"

@shared_task(bind=True)
def cleanup_old_exports(self):
    """
    Clean up old export files (keep last 4 weeks)
    """
    try:
        exports_dir = os.path.join(settings.MEDIA_ROOT, 'exports')
        if not os.path.exists(exports_dir):
            return "No exports directory found"
        
        cutoff_date = timezone.now() - timedelta(days=28)  # 4 weeks
        deleted_count = 0
        
        for filename in os.listdir(exports_dir):
            if filename.startswith('user_data_export_') and filename.endswith('.csv'):
                filepath = os.path.join(exports_dir, filename)
                
                try:
                    # Check file modification time
                    file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                    file_time = timezone.make_aware(file_time) if timezone.is_naive(file_time) else file_time
                    
                    if file_time < cutoff_date:
                        os.remove(filepath)
                        deleted_count += 1
                        logger.info(f"Deleted old export file: {filename}")
                except Exception as e:
                    logger.error(f"Failed to delete {filename}: {str(e)}")
        
        result = f"Cleaned up {deleted_count} old export files"
        logger.info(result)
        return result
        
    except Exception as e:
        logger.error(f"Error in cleanup_old_exports task: {str(e)}")
        return f"Error: {str(e)}"