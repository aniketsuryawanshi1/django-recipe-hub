from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class AuthenticationConfig(AppConfig):
    """Configuration for the authentication app"""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'authentication'
    verbose_name = 'Authentication'
    
    def ready(self):
        """
        Import signals when the app is ready.
        This ensures that signal handlers are connected.
        """
        try:
            import authentication.signals
            logger.info("Authentication app signals loaded successfully")
        except Exception as e:
            logger.error(f"Error loading authentication signals: {str(e)}")
            
        # Import any other startup code here
        try:
            # You can add any other initialization code here
            pass
        except Exception as e:
            logger.error(f"Error during authentication app initialization: {str(e)}")