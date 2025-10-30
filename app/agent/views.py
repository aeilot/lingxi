from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from .models import ChatSession, ChatInformation, AgentConfiguration
from django.utils import timezone
from urllib.parse import unquote
from .core import generate_response, generate_session_summary, DecisionModule, decide_personality_update
from django.conf import settings
from datetime import timedelta


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
    
    context = {
        'sessions': sessions,
        'agent_config': agent_config
    }
    return render(request, "chat_ui.html", context)

def handle_user_input(request):
    if request.method == "POST":
        user_message = unquote(request.POST.get("message", ""))
        session_id = unquote(request.POST.get("session_id", None))

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
        
        # Save user message
        user_chat = ChatInformation.objects.create(
            message=user_message,
            is_user=True,
            is_agent=False
        )
        session.chat_infos.add(user_chat)
        
        # Generate response using OpenAI API or simulated response
        model_response = generate_response(user_message, agent_config, session, api_key=api_key, base_url=base_url)
        
        # Save AI response
        ai_chat = ChatInformation.objects.create(
            message=model_response,
            is_user=False,
            is_agent=True
        )
        session.chat_infos.add(ai_chat)
        
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
        
        response_data = {
            "response": model_response,
            "session_id": session.id,
            "user_message_id": user_chat.id,
            "ai_message_id": ai_chat.id
        }
        
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
        
        history = []
        for msg in messages:
            history.append({
                "id": msg.id,
                "message": msg.message,
                "is_user": msg.is_user,
                "is_agent": msg.is_agent,
                "chat_date": msg.chat_date.isoformat()
            })
        
        return JsonResponse({
            "session_id": session.id,
            "started_at": session.started_at.isoformat(),
            "messages": history
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
        
        # Use summary if available, otherwise fall back to last message
        display_text = session.summary if session.summary else (last_message.message if last_message else "No messages yet")
        
        sessions_data.append({
            "id": session.id,
            "started_at": session.started_at.isoformat(),
            "message_count": message_count,
            "summary": display_text,
            "last_message_date": last_message.chat_date.isoformat() if last_message else None
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


