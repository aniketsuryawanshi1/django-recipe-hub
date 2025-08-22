from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class RecipesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'recipes'
    verbose_name = 'Recipes'
    
    def ready(self):
        """Import signals when app is ready"""
        try:
            import recipes.signals
            logger.info("Recipe app signals loaded successfully")
        except Exception as e:
            logger.error(f"Error loading recipe signals: {str(e)}")