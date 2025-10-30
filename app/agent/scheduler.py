"""
Scheduler module for periodic tasks
"""
from apscheduler.schedulers.background import BackgroundScheduler
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None


def check_all_sessions_inactivity():
    """
    Check all active sessions for inactivity and perform necessary actions.
    This function is called periodically by the scheduler.
    """
    from .models import ChatSession
    from .core import DecisionModule
    
    logger.info("Running scheduled check for session inactivity")
    
    try:
        # Get all sessions that have some activity
        sessions = ChatSession.objects.filter(last_activity_at__isnull=False)
        
        for session in sessions:
            try:
                # Get API settings
                api_key = settings.OPENAI_API_KEY
                base_url = settings.OPENAI_BASE_URL
                
                # Get agent configuration
                agent_config = session.agent_configuration
                
                # Check if session has been inactive for more than 5 minutes
                time_since_activity = timezone.now() - session.last_activity_at
                if time_since_activity > timedelta(minutes=5):
                    logger.info(f"Session {session.id} has been inactive for {time_since_activity.total_seconds()/60:.1f} minutes")
                    
                    # Use DecisionModule to decide what to do
                    try:
                        decision = DecisionModule(session, agent_config, api_key=api_key, base_url=base_url)
                        logger.info(f"Decision for session {session.id}: {decision.get('action')} - {decision.get('reason')}")
                    except Exception as e:
                        logger.error(f"Error in DecisionModule for session {session.id}: {str(e)}")
                        
            except Exception as e:
                logger.error(f"Error checking session {session.id}: {str(e)}")
                
    except Exception as e:
        logger.error(f"Error in check_all_sessions_inactivity: {str(e)}")


def start_scheduler():
    """
    Start the background scheduler for periodic tasks
    """
    global scheduler
    
    if scheduler is not None:
        logger.warning("Scheduler already running")
        return
    
    logger.info("Starting background scheduler")
    scheduler = BackgroundScheduler()
    
    # Get interval from settings
    check_interval = getattr(settings, 'SCHEDULER_CHECK_INTERVAL_MINUTES', 5)
    
    # Schedule the check_all_sessions_inactivity to run at configured interval
    scheduler.add_job(
        check_all_sessions_inactivity,
        'interval',
        minutes=check_interval,
        id='check_session_inactivity',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Background scheduler started successfully")


def stop_scheduler():
    """
    Stop the background scheduler
    """
    global scheduler
    
    if scheduler is not None:
        logger.info("Stopping background scheduler")
        scheduler.shutdown()
        scheduler = None
        logger.info("Background scheduler stopped")
