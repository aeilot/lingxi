from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class AgentConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'agent'
    
    def ready(self):
        """
        Called when the app is ready.
        Import tasks to ensure they are registered with Celery.
        """
        # Import tasks so they are registered with Celery
        try:
            from . import tasks
            logger.info("Celery tasks registered")
        except Exception as e:
            logger.error(f"Failed to register Celery tasks: {str(e)}")


