from rest_framework import permissions
from .models import Recipe
import logging

logger = logging.getLogger(__name__)

class IsRecipeOwnerOrReadOnly(permissions.BasePermission):
    message = "You can only modify your own recipes."

    def has_object_permission(self, request, view, obj):
        try:
            if request.method in permissions.SAFE_METHODS:
                return True
            if isinstance(obj, Recipe):
                return obj.author == request.user
            if hasattr(obj, 'recipe'):
                return obj.recipe.author == request.user
            return False
        except Exception as e:
            logger.error(f"Error checking recipe owner permission: {str(e)}")
            return False

class CanRateRecipe(permissions.BasePermission):
    message = "You cannot rate your own recipe or you must be logged in to rate."

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        try:
            if hasattr(obj, 'recipe'):
                return obj.recipe.author != request.user
            if isinstance(obj, Recipe):
                return obj.author != request.user
            return True
        except Exception as e:
            logger.error(f"Error checking rating permission: {str(e)}")
            return False