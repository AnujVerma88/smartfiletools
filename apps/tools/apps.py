import logging
from django.apps import AppConfig

logger = logging.getLogger('apps.tools')


class ToolsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.tools'
    
    def ready(self):
        """
        Import converters to register them with the factory.
        This ensures all @register_converter decorators are executed.
        """
        try:
            # Import converters module to trigger registration decorators
            from apps.tools import converters
            logger.info("File converters imported and registered successfully")
        except Exception as e:
            logger.error(f"Error importing converters: {str(e)}", exc_info=True)
