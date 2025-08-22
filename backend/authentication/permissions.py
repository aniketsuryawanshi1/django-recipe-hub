from rest_framework import permissions
import logging

logger = logging.getLogger(__name__)

class IsSellerUser(permissions.BasePermission):
    """
    Grants access ONLY to authenticated users 
    who are identified as 'sellers'.
    """
    message = "You must be a seller to access this resource."

    def has_permission(self, request, view):
        try:
            return (
                request.user and 
                request.user.is_authenticated and 
                request.user.is_seller
            )
        except Exception as e:
            logger.error(f"Error checking seller permission: {str(e)}")
            return False


class IsCustomerUser(permissions.BasePermission):
    """
    Grants access ONLY to authenticated users 
    who are identified as 'customers'.
    """
    message = "You must be a customer to access this resource."

    def has_permission(self, request, view):
        try:
            return (
                request.user and 
                request.user.is_authenticated and 
                request.user.is_customer
            )
        except Exception as e:
            logger.error(f"Error checking customer permission: {str(e)}")
            return False


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Object-level permission:
    - SAFE methods (GET, HEAD, OPTIONS) are allowed to everyone.
    - Write methods (POST, PUT, DELETE) are allowed only to the object's owner.
    """
    message = "You can only modify your own resources."

    def has_object_permission(self, request, view, obj):
        try:
            # Read-only access for safe methods
            if request.method in permissions.SAFE_METHODS:
                return True
            
            # Write access only if user is the object owner
            # Check multiple possible owner attributes
            if hasattr(obj, 'user'):
                return obj.user == request.user
            elif hasattr(obj, 'created_by'):
                return obj.created_by == request.user
            elif hasattr(obj, 'owner'):
                return obj.owner == request.user
            else:
                # If no owner attribute found, deny access
                logger.warning(f"Object {obj} has no owner attribute")
                return False
                
        except Exception as e:
            logger.error(f"Error checking object permission: {str(e)}")
            return False


class IsSellerOrReadOnly(permissions.BasePermission):
    """
    Allows write access only to sellers, but read access to everyone.
    """
    message = "You must be a seller to perform this action."

    def has_permission(self, request, view):
        try:
            if request.method in permissions.SAFE_METHODS:
                return True
            
            return (
                request.user and 
                request.user.is_authenticated and 
                request.user.is_seller
            )
        except Exception as e:
            logger.error(f"Error checking seller or read-only permission: {str(e)}")
            return False


class IsOwnerOrSellerReadOnly(permissions.BasePermission):
    """
    Object-level permission that allows:
    - Full access to the owner
    - Read access to sellers
    - No access to customers for other users' objects
    """
    message = "You don't have permission to access this resource."

    def has_object_permission(self, request, view, obj):
        try:
            # Check if user is the owner
            owner = None
            if hasattr(obj, 'user'):
                owner = obj.user
            elif hasattr(obj, 'created_by'):
                owner = obj.created_by
            elif hasattr(obj, 'owner'):
                owner = obj.owner
            
            if owner == request.user:
                return True
            
            # If not owner, check if it's a safe method and user is seller
            if request.method in permissions.SAFE_METHODS:
                return request.user.is_authenticated and request.user.is_seller
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking owner or seller read-only permission: {str(e)}")
            return False