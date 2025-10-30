"""
Celery tasks for the agent application.
"""
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task(name='agent.tasks.check_all_sessions_inactivity_task')
def check_all_sessions_inactivity_task():
    """
    Check all active sessions for inactivity and perform necessary actions.
    This task is called periodically by Celery Beat.
    """
    from agent.models import ChatSession, ChatInformation
    from agent.core import DecisionModule
    
    logger.info("Running Celery task: check_all_sessions_inactivity")
    
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
                        
                        # If decision is to send a message, actually send it
                        if decision.get('action') in ['continue', 'new_topic'] and decision.get('suggested_message'):
                            # Create and save the proactive message
                            proactive_message = ChatInformation.objects.create(
                                message=decision.get('suggested_message'),
                                is_user=False,
                                is_agent=True,
                                is_agent_growth=True,  # Mark as proactive/growth message
                                metadata={'proactive': True, 'action': decision.get('action')}
                            )
                            session.chat_infos.add(proactive_message)
                            
                            # Update session state to indicate new proactive message
                            if session.current_state is None:
                                session.current_state = {}
                            
                            if 'proactive_messages' not in session.current_state:
                                session.current_state['proactive_messages'] = []
                            
                            session.current_state['proactive_messages'].append({
                                'message_id': proactive_message.id,
                                'timestamp': timezone.now().isoformat(),
                                'action': decision.get('action'),
                                'reason': decision.get('reason')
                            })
                            
                            # Update message count but don't update last_activity_at
                            # (we want to track user activity, not proactive messages)
                            session.message_count = session.chat_infos.count()
                            session.save()
                            
                            logger.info(f"Sent proactive message to session {session.id}: {decision.get('suggested_message')[:50]}...")
                            
                    except Exception as e:
                        logger.error(f"Error in DecisionModule for session {session.id}: {str(e)}")
                        
            except Exception as e:
                logger.error(f"Error checking session {session.id}: {str(e)}")
                
    except Exception as e:
        logger.error(f"Error in check_all_sessions_inactivity_task: {str(e)}")


@shared_task(name='agent.tasks.check_personality_updates_task')
def check_personality_updates_task():
    """
    Check all active sessions to determine if personality updates are needed.
    This task is called periodically by Celery Beat.
    """
    from agent.models import ChatSession
    from agent.core import decide_personality_update
    
    logger.info("Running Celery task: check_personality_updates")
    
    try:
        # Get API settings
        api_key = settings.OPENAI_API_KEY
        base_url = settings.OPENAI_BASE_URL
        
        # Get all sessions with sufficient messages
        # Only check sessions that have at least 20 messages
        sessions = ChatSession.objects.filter(
            message_count__gte=20,
            last_activity_at__isnull=False
        )
        
        for session in sessions:
            try:
                agent_config = session.agent_configuration
                
                # Check if we should suggest a personality update
                # Only check sessions that were active in the last 24 hours
                time_since_activity = timezone.now() - session.last_activity_at
                if time_since_activity < timedelta(hours=24):
                    
                    # Get the last time we checked for personality updates
                    last_personality_check = session.current_state.get('last_personality_check') if session.current_state else None
                    
                    # Only check if we haven't checked in the last 24 hours
                    should_check = True
                    if last_personality_check:
                        from datetime import datetime
                        last_check_time = datetime.fromisoformat(last_personality_check)
                        if timezone.now() - last_check_time < timedelta(hours=24):
                            should_check = False
                    
                    if should_check:
                        logger.info(f"Checking personality update for session {session.id}")
                        
                        try:
                            decision = decide_personality_update(
                                session, 
                                agent_config, 
                                api_key=api_key, 
                                base_url=base_url
                            )
                            
                            # Store the decision in session state
                            if session.current_state is None:
                                session.current_state = {}
                            
                            session.current_state['last_personality_check'] = timezone.now().isoformat()
                            session.current_state['personality_update_suggestion'] = decision
                            session.save()
                            
                            logger.info(
                                f"Personality update check for session {session.id}: "
                                f"should_update={decision.get('should_update')}, "
                                f"confidence={decision.get('confidence')}"
                            )
                            
                        except Exception as e:
                            logger.error(f"Error in decide_personality_update for session {session.id}: {str(e)}")
                        
            except Exception as e:
                logger.error(f"Error checking personality update for session {session.id}: {str(e)}")
                
    except Exception as e:
        logger.error(f"Error in check_personality_updates_task: {str(e)}")
