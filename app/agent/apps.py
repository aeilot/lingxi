from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class AgentConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'agent'
    
    def ready(self):
        """
        Called when the app is ready. Start the background scheduler here.
        """
        # Only start scheduler in the main process, not in management commands
        import sys
        
        # Avoid starting scheduler during migrations, tests, or other management commands
        if 'runserver' in sys.argv or 'gunicorn' in sys.argv[0]:
            from .scheduler import start_scheduler
            try:
                start_scheduler()
                logger.info("Scheduler started in ready()")
            except Exception as e:
                logger.error(f"Failed to start scheduler: {str(e)}")

