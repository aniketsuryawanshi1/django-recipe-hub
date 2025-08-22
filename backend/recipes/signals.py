from django.db.models.signals import post_save, post_delete, pre_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import Recipe, Rating, Favorite, RecipeView, Category
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Recipe)
def recipe_post_save(sender, instance, created, **kwargs):
    """Handle recipe creation/update"""
    try:
        if created:
            logger.info(f"New recipe created: {instance.title} by {instance.author.email}")
            
            # Clear category-related caches
            if instance.category:
                cache.delete(f'category_{instance.category.id}_recipes')
            
            # Clear general caches
            cache.delete('featured_recipes')
            cache.delete('popular_recipes')
            cache.delete('recipe_stats')
        
        else:
            logger.info(f"Recipe updated: {instance.title}")
            
            # Clear recipe-specific caches
            cache.delete(f'recipe_{instance.id}')
            cache.delete('recipe_stats')
    
    except Exception as e:
        logger.error(f"Error in recipe post_save signal: {str(e)}")

@receiver(post_delete, sender=Recipe)
def recipe_post_delete(sender, instance, **kwargs):
    """Handle recipe deletion"""
    try:
        logger.info(f"Recipe deleted: {instance.title}")
        
        # Clear related caches
        cache.delete(f'recipe_{instance.id}')
        cache.delete('featured_recipes')
        cache.delete('popular_recipes')
        cache.delete('recipe_stats')
        
        if instance.category:
            cache.delete(f'category_{instance.category.id}_recipes')
    
    except Exception as e:
        logger.error(f"Error in recipe post_delete signal: {str(e)}")

@receiver(post_save, sender=Rating)
def rating_post_save(sender, instance, created, **kwargs):
    """Handle rating creation/update"""
    try:
        if created:
            logger.info(f"New rating: {instance.user.username} rated {instance.recipe.title} - {instance.rating} stars")
        else:
            logger.info(f"Rating updated: {instance.user.username} updated rating for {instance.recipe.title}")
        
        # Clear recipe-related caches
        cache.delete(f'recipe_{instance.recipe.id}')
        cache.delete('popular_recipes')
        cache.delete('recipe_stats')
    
    except Exception as e:
        logger.error(f"Error in rating post_save signal: {str(e)}")

@receiver(post_delete, sender=Rating)
def rating_post_delete(sender, instance, **kwargs):
    """Handle rating deletion"""
    try:
        logger.info(f"Rating deleted: {instance.user.username} removed rating for {instance.recipe.title}")
        
        # Clear recipe-related caches
        cache.delete(f'recipe_{instance.recipe.id}')
        cache.delete('popular_recipes')
        cache.delete('recipe_stats')
    
    except Exception as e:
        logger.error(f"Error in rating post_delete signal: {str(e)}")

@receiver(post_save, sender=Favorite)
def favorite_post_save(sender, instance, created, **kwargs):
    """Handle favorite creation"""
    try:
        if created:
            logger.info(f"Recipe favorited: {instance.user.username} favorited {instance.recipe.title}")
    
    except Exception as e:
        logger.error(f"Error in favorite post_save signal: {str(e)}")

@receiver(post_delete, sender=Favorite)
def favorite_post_delete(sender, instance, **kwargs):
    """Handle favorite removal"""
    try:
        logger.info(f"Favorite removed: {instance.user.username} unfavorited {instance.recipe.title}")
    
    except Exception as e:
        logger.error(f"Error in favorite post_delete signal: {str(e)}")

@receiver(post_save, sender=RecipeView)
def recipe_view_post_save(sender, instance, created, **kwargs):
    """Handle recipe view tracking"""
    try:
        if created:
            user_info = instance.user.username if instance.user else f"Anonymous ({instance.ip_address})"
            logger.debug(f"Recipe view tracked: {user_info} viewed {instance.recipe.title}")
    
    except Exception as e:
        logger.error(f"Error in recipe_view post_save signal: {str(e)}")

@receiver(pre_delete, sender=Recipe)
def recipe_pre_delete(sender, instance, **kwargs):
    """Clean up recipe files before deletion"""
    try:
        # Delete recipe images
        for image in instance.images.all():
            if image.image:
                try:
                    image.image.delete(save=False)
                except Exception as e:
                    logger.error(f"Failed to delete image file: {str(e)}")
        
        logger.info(f"Cleaned up files for recipe: {instance.title}")
    
    except Exception as e:
        logger.error(f"Error in recipe pre_delete signal: {str(e)}")