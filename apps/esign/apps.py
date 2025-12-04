"""
E-Sign app configuration
"""
from django.apps import AppConfig


class EsignConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.esign'
    verbose_name = 'E-Sign'
    
    def ready(self):
        """
        Import signals and register components when app is ready
        """
        try:
            # Import signals if any
            # from . import signals
            pass
        except Exception as e:
            import logging
            logger = logging.getLogger('apps.esign')
            logger.error(f"Error initializing esign app: {str(e)}")
