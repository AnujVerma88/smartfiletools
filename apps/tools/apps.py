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
            from apps.tools.utils.converter_factory import list_converters
            
            # Get all registered converters
            registered = list_converters()
            converter_names = list(registered.keys())
            
            logger.info(f"File converters imported successfully. Total registered: {len(registered)}")
            logger.info(f"Registered converters: {', '.join(converter_names)}")
            
            # Check if video compression is available
            if 'compress_video' not in registered:
                logger.warning(
                    "[WARNING] compress_video converter not registered - video compression unavailable. "
                    "Check logs above for VideoCompressor import errors."
                )
            else:
                logger.info("[OK] Video compression (compress_video) is available")
                
        except Exception as e:
            logger.error(f"Error importing converters: {str(e)}", exc_info=True)
