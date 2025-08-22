from rest_framework.throttling import UserRateThrottle
import logging

logger = logging.getLogger(__name__)

class CustomerRateThrottle(UserRateThrottle):
    """
    Throttle class for Customers.
    Limits the request rate for authenticated users 
    who are identified as 'customers'.
    """
    scope = 'customer'  # This scope must match the setting in DRF's DEFAULT_THROTTLE_RATES

    def allow_request(self, request, view):
        """
        Check if the request should be allowed.
        Only throttles if user is authenticated AND is a customer.
        """
        try:
            if (request.user and 
                request.user.is_authenticated and 
                hasattr(request.user, 'is_customer') and 
                request.user.is_customer):
                # Apply throttling rules for customers
                return super().allow_request(request, view)
            # No throttling for others
            return True
            
        except Exception as e:
            logger.error(f"Error in CustomerRateThrottle: {str(e)}")
            # Default to allowing the request if there's an error
            return True

    def get_cache_key(self, request, view):
        """
        Generate cache key for throttling.
        """
        try:
            if (request.user and 
                request.user.is_authenticated and 
                hasattr(request.user, 'is_customer') and
                request.user.is_customer):
                return f"throttle_customer_{request.user.pk}"
            return None
            
        except Exception as e:
            logger.error(f"Error generating cache key for customer throttling: {str(e)}")
            return None


class SellerRateThrottle(UserRateThrottle):
    """
    Throttle class for Sellers.
    Limits the request rate for authenticated users 
    who are identified as 'sellers'.
    """
    scope = 'seller'  # This scope must match the setting in DRF's DEFAULT_THROTTLE_RATES

    def allow_request(self, request, view):
        """
        Check if the request should be allowed.
        Only throttles if user is authenticated AND is a seller.
        """
        try:
            if (request.user and 
                request.user.is_authenticated and 
                hasattr(request.user, 'is_seller') and 
                request.user.is_seller):
                # Apply throttling rules for sellers
                return super().allow_request(request, view)
            # No throttling for others
            return True
            
        except Exception as e:
            logger.error(f"Error in SellerRateThrottle: {str(e)}")
            # Default to allowing the request if there's an error
            return True

    def get_cache_key(self, request, view):
        """
        Generate cache key for throttling.
        """
        try:
            if (request.user and 
                request.user.is_authenticated and 
                hasattr(request.user, 'is_seller') and
                request.user.is_seller):
                return f"throttle_seller_{request.user.pk}"
            return None
            
        except Exception as e:
            logger.error(f"Error generating cache key for seller throttling: {str(e)}")
            return None


class AdminRateThrottle(UserRateThrottle):
    """
    Throttle class for Admin users with higher limits.
    """
    scope = 'admin'

    def allow_request(self, request, view):
        """
        Check if the request should be allowed.
        Only throttles if user is authenticated AND is staff/superuser.
        """
        try:
            if (request.user and 
                request.user.is_authenticated and 
                (request.user.is_staff or request.user.is_superuser)):
                return super().allow_request(request, view)
            # No throttling for others (handled by other throttles)
            return True
            
        except Exception as e:
            logger.error(f"Error in AdminRateThrottle: {str(e)}")
            return True

    def get_cache_key(self, request, view):
        """
        Generate cache key for admin throttling.
        """
        try:
            if (request.user and 
                request.user.is_authenticated and 
                (request.user.is_staff or request.user.is_superuser)):
                return f"throttle_admin_{request.user.pk}"
            return None
            
        except Exception as e:
            logger.error(f"Error generating cache key for admin throttling: {str(e)}")
            return None