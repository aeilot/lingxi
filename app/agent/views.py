from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from .models import ChatSession, ChatInformation, AgentConfiguration
from django.utils import timezone
from urllib.parse import unquote
from .core import generate_response, generate_session_summary, DecisionModule
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
        decision = DecisionModule(session, agent_config, api_key=api_key, base_url=base_url)
        
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

