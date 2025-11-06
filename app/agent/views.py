from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from .models import ChatSession, ChatInformation, AgentConfiguration, Agent
from django.utils import timezone
from urllib.parse import unquote
from .core import generate_response, generate_multi_agent_responses, generate_session_summary, DecisionModule, decide_personality_update
from django.conf import settings
from datetime import timedelta
import json
import logging

logger = logging.getLogger(__name__)


# Create your views here.

@ensure_csrf_cookie
def chat_ui(request):
    # Get or create a default agent configuration
    agent_config, _ = AgentConfiguration.objects.get_or_create(
        name="default",
        defaults={"parameters": {"model": "simulated"}}
    )
    
    # Get all chat sessions for display
    sessions = ChatSession.objects.all().order_by('-started_at')
    
    # Get all agents for the UI
    agents = Agent.objects.filter(is_active=True).order_by('name')
    
    context = {
        'sessions': sessions,
        'agent_config': agent_config,
        'agents': agents,
    }
    return render(request, "chat_ui.html", context)

def handle_user_input(request):
    if request.method == "POST":
        user_message = unquote(request.POST.get("message", ""))
        session_id_raw = request.POST.get("session_id", None)
        session_id = unquote(session_id_raw) if session_id_raw else None

        # Get API settings from Django settings (loaded from .env)
        api_key = settings.OPENAI_API_KEY
        base_url = settings.OPENAI_BASE_URL
        model = settings.OPENAI_MODEL

        # Get or create agent configuration
        agent_config, _ = AgentConfiguration.objects.get_or_create(
            name="default",
            defaults={"parameters": {"model": model, "personality_prompt": ""}}
        )
        
        # Update model if it's different
        if agent_config.parameters.get("model") != model:
            agent_config.parameters["model"] = model
            agent_config.save()
        
        # Get or create chat session
        if session_id:
            try:
                session = ChatSession.objects.get(id=session_id)
            except ChatSession.DoesNotExist:
                session = ChatSession.objects.create(agent_configuration=agent_config)
        else:
            session = ChatSession.objects.create(agent_configuration=agent_config)
        
        # Ensure session has agents assigned
        if session.agents.count() == 0:
            # Assign all active agents to new sessions
            active_agents = Agent.objects.filter(is_active=True)
            session.agents.set(active_agents)
        
        # Mark all previous AI messages as read when user sends a message
        # (User is obviously viewing the conversation)
        session.chat_infos.filter(is_agent=True, is_read=False).update(is_read=True)
        
        # Save user message
        user_chat = ChatInformation.objects.create(
            message=user_message,
            is_user=True,
            is_agent=False
        )
        session.chat_infos.add(user_chat)
        
        # Generate multi-agent responses
        agent_responses = generate_multi_agent_responses(
            user_message, 
            agent_config, 
            session, 
            api_key=api_key, 
            base_url=base_url
        )
        
        # Handle agent responses
        all_messages = []
        
        for agent_response in agent_responses:
            agent = agent_response["agent"]
            model_response = agent_response["response"]
            
            # Handle split messages or single message for each agent
            if isinstance(model_response, dict) and "messages" in model_response:
                # LLM returned split messages
                for msg_text in model_response["messages"]:
                    ai_chat = ChatInformation.objects.create(
                        message=msg_text,
                        is_user=False,
                        is_agent=True,
                        agent=agent
                    )
                    session.chat_infos.add(ai_chat)
                    all_messages.append({
                        "id": ai_chat.id,
                        "message": msg_text,
                        "agent_id": agent.id,
                        "agent_name": agent.name,
                        "agent_emoji": agent.avatar_emoji,
                        "agent_color": agent.color
                    })
            else:
                # Single message (plain text)
                ai_chat = ChatInformation.objects.create(
                    message=model_response,
                    is_user=False,
                    is_agent=True,
                    agent=agent
                )
                session.chat_infos.add(ai_chat)
                all_messages.append({
                    "id": ai_chat.id,
                    "message": model_response,
                    "agent_id": agent.id,
                    "agent_name": agent.name,
                    "agent_emoji": agent.avatar_emoji,
                    "agent_color": agent.color
                })
        
        # Update message count and last activity time
        session.message_count = session.chat_infos.count()
        session.last_activity_at = timezone.now()
        
        # Update summary every 10 messages
        summary_updated = False
        if session.message_count % 10 == 0:
            summary = generate_session_summary(session, agent_config, api_key=api_key, base_url=base_url)
            session.summary = summary
            summary_updated = True
        
        # Check for personality update every 20 messages
        personality_updated = False
        personality_suggestion = None
        if session.message_count % 20 == 0 and session.message_count >= 20:
            # Check if we should suggest or auto-apply a personality update
            decision = decide_personality_update(session, agent_config, api_key=api_key, base_url=base_url)
            
            # Store the decision in session state
            if session.current_state is None:
                session.current_state = {}
            
            session.current_state['last_personality_check'] = timezone.now().isoformat()
            
            # Auto-apply if confidence is high (> 0.8)
            CONFIDENCE_THRESHOLD = 0.8
            if decision.get('should_update') and decision.get('confidence', 0) > CONFIDENCE_THRESHOLD:
                # Automatically apply the personality update
                suggested_personality = decision.get('suggested_personality')
                if suggested_personality:
                    agent_config.parameters["personality_prompt"] = suggested_personality
                    agent_config.save()
                    personality_updated = True
                    # Log the auto-update in session state
                    session.current_state['last_personality_auto_update'] = {
                        'timestamp': timezone.now().isoformat(),
                        'personality': suggested_personality,
                        'reason': decision.get('reason'),
                        'confidence': decision.get('confidence')
                    }
            else:
                # Store suggestion for manual review if confidence is lower
                if decision.get('should_update'):
                    session.current_state['personality_update_suggestion'] = decision
                    personality_suggestion = decision
        
        session.save()
        
        # Build response data
        response_data = {
            "session_id": session.id,
            "user_message_id": user_chat.id,
            "messages": all_messages  # New multi-agent format
        }
        
        # Include backward compatibility fields if there's at least one message
        if all_messages:
            response_data["response"] = all_messages[0]["message"]
            response_data["ai_message_id"] = all_messages[0]["id"]
        
        # Include updated summary if it was changed
        if summary_updated:
            response_data["summary_updated"] = True
            response_data["summary"] = session.summary
        
        # Include personality update information
        if personality_updated:
            response_data["personality_updated"] = True
            response_data["personality_prompt"] = agent_config.parameters.get("personality_prompt")
        elif personality_suggestion:
            response_data["personality_suggestion_available"] = True
        
        return JsonResponse(response_data)
    return JsonResponse({"error": "Invalid request method."}, status=400)

def create_session(request):
    """Create a new chat session"""
    if request.method == "POST":
        model = settings.OPENAI_MODEL
        agent_config, _ = AgentConfiguration.objects.get_or_create(
            name="default",
            defaults={"parameters": {"model": model, "personality_prompt": ""}}
        )
        session = ChatSession.objects.create(agent_configuration=agent_config)
        return JsonResponse({
            "session_id": session.id,
            "started_at": session.started_at.isoformat()
        })
    return JsonResponse({"error": "Invalid request method."}, status=400)

def get_session_history(request, session_id):
    """Get chat history for a specific session"""
    try:
        session = ChatSession.objects.get(id=session_id)
        messages = session.chat_infos.all().order_by('chat_date')
        
        # Get IDs of unread messages before marking them as read
        unread_message_ids = set(session.chat_infos.filter(is_agent=True, is_read=False).values_list('id', flat=True))
        
        # Find the first unread message ID for divider placement
        first_unread_id = min(unread_message_ids) if unread_message_ids else None
        
        # Mark all AI messages as read when user loads session history
        session.chat_infos.filter(is_agent=True, is_read=False).update(is_read=True)
        
        history = []
        for msg in messages:
            msg_data = {
                "id": msg.id,
                "message": msg.message,
                "is_user": msg.is_user,
                "is_agent": msg.is_agent,
                "chat_date": msg.chat_date.isoformat(),
                "was_unread": msg.id in unread_message_ids
            }
            # Add agent information for multi-agent messages
            if msg.agent:
                msg_data["agent_id"] = msg.agent.id
                msg_data["agent_name"] = msg.agent.name
                msg_data["agent_emoji"] = msg.agent.avatar_emoji
                msg_data["agent_color"] = msg.agent.color
            history.append(msg_data)
        
        # Get session agents
        session_agents = list(session.agents.filter(is_active=True).values(
            'id', 'name', 'avatar_emoji', 'color', 'personality_prompt'
        ))
        
        return JsonResponse({
            "session_id": session.id,
            "started_at": session.started_at.isoformat(),
            "messages": history,
            "first_unread_id": first_unread_id,
            "agents": session_agents
        })
    except ChatSession.DoesNotExist:
        return JsonResponse({"error": "Session not found."}, status=404)

def list_sessions(request):
    """List all chat sessions"""
    sessions = ChatSession.objects.all().order_by('-started_at')
    
    sessions_data = []
    for session in sessions:
        message_count = session.chat_infos.count()
        last_message = session.chat_infos.order_by('-chat_date').first()
        
        # Count unread AI messages in this session
        unread_count = session.chat_infos.filter(is_agent=True, is_read=False).count()
        
        # Use summary if available, otherwise fall back to last message
        display_text = session.summary if session.summary else (last_message.message if last_message else "No messages yet")
        
        sessions_data.append({
            "id": session.id,
            "started_at": session.started_at.isoformat(),
            "message_count": message_count,
            "summary": display_text,
            "last_message_date": last_message.chat_date.isoformat() if last_message else None,
            "unread_count": unread_count
        })
    
    return JsonResponse({"sessions": sessions_data})

def delete_session(request, session_id):
    """Delete a chat session"""
    if request.method == "POST":
        try:
            session = ChatSession.objects.get(id=session_id)
            session.delete()
            return JsonResponse({"success": True})
        except ChatSession.DoesNotExist:
            return JsonResponse({"error": "Session not found."}, status=404)
    return JsonResponse({"error": "Invalid request method."}, status=400)

def update_personality_prompt(request):
    """Update the personality prompt for the default agent configuration"""
    if request.method == "POST":
        personality_prompt = request.POST.get("personality_prompt", "").strip()
        
        model = settings.OPENAI_MODEL
        agent_config, _ = AgentConfiguration.objects.get_or_create(
            name="default",
            defaults={"parameters": {"model": model, "personality_prompt": ""}}
        )
        
        # Update the personality prompt
        agent_config.parameters["personality_prompt"] = personality_prompt
        agent_config.save()
        
        return JsonResponse({
            "success": True,
            "personality_prompt": personality_prompt
        })
    return JsonResponse({"error": "Invalid request method."}, status=400)

def get_personality_prompt(request):
    """Get the current personality prompt"""
    model = settings.OPENAI_MODEL
    agent_config, _ = AgentConfiguration.objects.get_or_create(
        name="default",
        defaults={"parameters": {"model": model, "personality_prompt": ""}}
    )
    
    personality_prompt = agent_config.parameters.get("personality_prompt", "")
    return JsonResponse({
        "personality_prompt": personality_prompt
    })

def check_session_inactivity(request, session_id):
    """Check if a session is inactive and should receive a proactive message"""
    try:
        session = ChatSession.objects.get(id=session_id)
        
        # Get API settings
        api_key = settings.OPENAI_API_KEY
        base_url = settings.OPENAI_BASE_URL
        
        # Get or create agent configuration
        agent_config = session.agent_configuration
        
        # Use DecisionModule to decide what to do
        try:
            decision = DecisionModule(session, agent_config, api_key=api_key, base_url=base_url)
        except Exception as e:
            # If DecisionModule fails, return a safe default response
            return JsonResponse({
                "session_id": session.id,
                "action": "wait",
                "reason": f"Error making decision: {str(e)}",
                "suggested_message": None,
                "minutes_inactive": (timezone.now() - session.last_activity_at).total_seconds() / 60 if session.last_activity_at else 0
            })
        
        return JsonResponse({
            "session_id": session.id,
            "action": decision.get("action"),
            "reason": decision.get("reason"),
            "suggested_message": decision.get("suggested_message"),
            "minutes_inactive": (timezone.now() - session.last_activity_at).total_seconds() / 60 if session.last_activity_at else 0
        })
    except ChatSession.DoesNotExist:
        return JsonResponse({"error": "Session not found."}, status=404)

def get_session_summary(request, session_id):
    """Get the current summary for a session"""
    try:
        session = ChatSession.objects.get(id=session_id)
        
        return JsonResponse({
            "session_id": session.id,
            "summary": session.summary or "No summary yet",
            "message_count": session.message_count,
            "last_activity_at": session.last_activity_at.isoformat() if session.last_activity_at else None
        })
    except ChatSession.DoesNotExist:
        return JsonResponse({"error": "Session not found."}, status=404)

def check_personality_update_suggestion(request, session_id):
    """Check if there's a personality update suggestion for a session"""
    try:
        session = ChatSession.objects.get(id=session_id)
        
        # Get the personality update suggestion from session state
        suggestion = None
        if session.current_state and 'personality_update_suggestion' in session.current_state:
            suggestion = session.current_state['personality_update_suggestion']
        
        return JsonResponse({
            "session_id": session.id,
            "has_suggestion": suggestion is not None and suggestion.get('should_update', False),
            "suggestion": suggestion
        })
    except ChatSession.DoesNotExist:
        return JsonResponse({"error": "Session not found."}, status=404)

def apply_personality_update(request, session_id):
    """Apply a suggested personality update to the agent configuration"""
    if request.method == "POST":
        try:
            session = ChatSession.objects.get(id=session_id)
            
            # Get the suggested personality from request or session state
            suggested_personality = request.POST.get("suggested_personality", "").strip()
            
            if not suggested_personality:
                # Try to get it from session state
                if session.current_state and 'personality_update_suggestion' in session.current_state:
                    suggestion = session.current_state['personality_update_suggestion']
                    suggested_personality = suggestion.get('suggested_personality', '')
            
            if not suggested_personality:
                return JsonResponse({"error": "No personality suggestion provided."}, status=400)
            
            # Update the agent configuration
            agent_config = session.agent_configuration
            agent_config.parameters["personality_prompt"] = suggested_personality
            agent_config.save()
            
            # Clear the suggestion from session state
            if session.current_state:
                session.current_state.pop('personality_update_suggestion', None)
                session.save()
            
            return JsonResponse({
                "success": True,
                "personality_prompt": suggested_personality,
                "session_id": session.id
            })
        except ChatSession.DoesNotExist:
            return JsonResponse({"error": "Session not found."}, status=404)
    return JsonResponse({"error": "Invalid request method."}, status=400)

def dismiss_personality_suggestion(request, session_id):
    """Dismiss a personality update suggestion"""
    if request.method == "POST":
        try:
            session = ChatSession.objects.get(id=session_id)
            
            # Clear the suggestion from session state
            if session.current_state and 'personality_update_suggestion' in session.current_state:
                session.current_state.pop('personality_update_suggestion', None)
                session.save()
            
            return JsonResponse({
                "success": True,
                "session_id": session.id
            })
        except ChatSession.DoesNotExist:
            return JsonResponse({"error": "Session not found."}, status=404)
    return JsonResponse({"error": "Invalid request method."}, status=400)

def check_new_messages(request, session_id):
    """Check if there are new proactive messages for a session"""
    try:
        session = ChatSession.objects.get(id=session_id)
        
        # Get proactive messages from session state
        new_messages = []
        if session.current_state and 'proactive_messages' in session.current_state:
            proactive_message_ids = [msg['message_id'] for msg in session.current_state['proactive_messages']]
            
            # Get the actual message objects
            for msg_data in session.current_state['proactive_messages']:
                try:
                    msg = ChatInformation.objects.get(id=msg_data['message_id'])
                    new_messages.append({
                        'id': msg.id,
                        'message': msg.message,
                        'is_read': msg.is_read,
                        'timestamp': msg_data['timestamp'],
                        'action': msg_data.get('action'),
                        'reason': msg_data.get('reason')
                    })
                except ChatInformation.DoesNotExist:
                    pass
        
        return JsonResponse({
            "session_id": session.id,
            "has_new_messages": len(new_messages) > 0,
            "new_messages": new_messages
        })
    except ChatSession.DoesNotExist:
        return JsonResponse({"error": "Session not found."}, status=404)

def acknowledge_new_messages(request, session_id):
    """Acknowledge that new proactive messages have been seen"""
    if request.method == "POST":
        try:
            session = ChatSession.objects.get(id=session_id)
            
            # Mark all AI messages in this session as read
            session.chat_infos.filter(is_agent=True, is_read=False).update(is_read=True)
            
            # Clear proactive messages from session state
            if session.current_state and 'proactive_messages' in session.current_state:
                session.current_state.pop('proactive_messages', None)
                session.save()
            
            return JsonResponse({
                "success": True,
                "session_id": session.id
            })
        except ChatSession.DoesNotExist:
            return JsonResponse({"error": "Session not found."}, status=404)
    return JsonResponse({"error": "Invalid request method."}, status=400)

def export_data(request):
    """Export all personality settings and chat history as JSON"""
    try:
        # Get current timestamp for consistency
        export_timestamp = timezone.now()
        
        # Get the default agent configuration for personality settings
        agent_config = AgentConfiguration.objects.filter(name="default").first()
        
        # Prepare personality settings
        personality_data = {
            "personality_prompt": "",
            "model": settings.OPENAI_MODEL
        }
        
        if agent_config:
            personality_data["personality_prompt"] = agent_config.parameters.get("personality_prompt", "")
            personality_data["model"] = agent_config.parameters.get("model", settings.OPENAI_MODEL)
        
        # Get all chat sessions with their history
        sessions = ChatSession.objects.all().order_by('-started_at')
        sessions_data = []
        
        for session in sessions:
            messages = session.chat_infos.all().order_by('chat_date')
            messages_list = []
            
            for msg in messages:
                messages_list.append({
                    "id": msg.id,
                    "message": msg.message,
                    "is_user": msg.is_user,
                    "is_agent": msg.is_agent,
                    "is_agent_growth": msg.is_agent_growth,
                    "chat_date": msg.chat_date.isoformat(),
                    "is_read": msg.is_read,
                    "metadata": msg.metadata,
                    "critical": msg.critical,
                    "critical_type": msg.critical_type
                })
            
            sessions_data.append({
                "id": session.id,
                "started_at": session.started_at.isoformat(),
                "message_count": session.message_count,
                "summary": session.summary,
                "last_activity_at": session.last_activity_at.isoformat() if session.last_activity_at else None,
                "current_state": session.current_state,
                "messages": messages_list
            })
        
        # Combine all data
        export_data = {
            "export_date": export_timestamp.isoformat(),
            "personality_settings": personality_data,
            "sessions": sessions_data,
            "total_sessions": len(sessions_data),
            "total_messages": sum(s["message_count"] for s in sessions_data)
        }
        
        # Create JSON response with proper headers for download
        response = HttpResponse(
            json.dumps(export_data, indent=2, ensure_ascii=False),
            content_type='application/json'
        )
        response['Content-Disposition'] = f'attachment; filename="lingxi_export_{export_timestamp.strftime("%Y%m%d_%H%M%S")}.json"'
        
        return response
        
    except Exception as e:
        # Log the error internally for debugging
        logger.error(f"Export failed: {str(e)}", exc_info=True)
        # Return generic error message to client
        return JsonResponse({"error": "Export failed. Please try again later."}, status=500)


# Agent Management Endpoints

def list_agents(request):
    """List all available AI agents"""
    agents = Agent.objects.filter(is_active=True).order_by('name')
    agents_data = []
    
    for agent in agents:
        agents_data.append({
            "id": agent.id,
            "name": agent.name,
            "personality_prompt": agent.personality_prompt,
            "avatar_emoji": agent.avatar_emoji,
            "color": agent.color,
            "is_active": agent.is_active
        })
    
    return JsonResponse({"agents": agents_data})


def get_agent(request, agent_id):
    """Get details of a specific agent"""
    try:
        agent = Agent.objects.get(id=agent_id)
        return JsonResponse({
            "id": agent.id,
            "name": agent.name,
            "personality_prompt": agent.personality_prompt,
            "avatar_emoji": agent.avatar_emoji,
            "color": agent.color,
            "is_active": agent.is_active
        })
    except Agent.DoesNotExist:
        return JsonResponse({"error": "Agent not found."}, status=404)


def update_agent(request, agent_id):
    """Update an agent's details"""
    if request.method == "POST":
        try:
            agent = Agent.objects.get(id=agent_id)
            
            # Update fields if provided
            if "personality_prompt" in request.POST:
                agent.personality_prompt = request.POST.get("personality_prompt")
            if "name" in request.POST:
                agent.name = request.POST.get("name")
            if "avatar_emoji" in request.POST:
                agent.avatar_emoji = request.POST.get("avatar_emoji")
            if "color" in request.POST:
                agent.color = request.POST.get("color")
            if "is_active" in request.POST:
                agent.is_active = request.POST.get("is_active").lower() == "true"
            
            agent.save()
            
            return JsonResponse({
                "success": True,
                "agent": {
                    "id": agent.id,
                    "name": agent.name,
                    "personality_prompt": agent.personality_prompt,
                    "avatar_emoji": agent.avatar_emoji,
                    "color": agent.color,
                    "is_active": agent.is_active
                }
            })
        except Agent.DoesNotExist:
            return JsonResponse({"error": "Agent not found."}, status=404)
    return JsonResponse({"error": "Invalid request method."}, status=400)


def update_session_agents(request, session_id):
    """Update which agents are active in a session"""
    if request.method == "POST":
        try:
            session = ChatSession.objects.get(id=session_id)
            
            # Get agent IDs from request
            agent_ids_str = request.POST.get("agent_ids", "")
            if agent_ids_str:
                agent_ids = [int(id.strip()) for id in agent_ids_str.split(",") if id.strip()]
                agents = Agent.objects.filter(id__in=agent_ids, is_active=True)
                session.agents.set(agents)
            else:
                # If no agents specified, assign all active agents
                active_agents = Agent.objects.filter(is_active=True)
                session.agents.set(active_agents)
            
            session.save()
            
            # Return updated agent list
            session_agents = list(session.agents.values('id', 'name', 'avatar_emoji', 'color'))
            
            return JsonResponse({
                "success": True,
                "session_id": session.id,
                "agents": session_agents
            })
        except ChatSession.DoesNotExist:
            return JsonResponse({"error": "Session not found."}, status=404)
    return JsonResponse({"error": "Invalid request method."}, status=400)


