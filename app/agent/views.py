from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from .models import ChatSession, ChatInformation, AgentConfiguration
from django.utils import timezone
from .core import generate_response

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
        user_message = request.POST.get("message", "")
        session_id = request.POST.get("session_id", None)
        
        # Get API settings from cookies
        api_key = request.COOKIES.get("openai_api_key", None)
        base_url = request.COOKIES.get("openai_base_url", None)
        model = request.COOKIES.get("openai_model", "gpt-3.5-turbo")
        
        # Get or create agent configuration
        agent_config, _ = AgentConfiguration.objects.get_or_create(
            name="default",
            defaults={"parameters": {"model": model}}
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
        
        return JsonResponse({
            "response": model_response,
            "session_id": session.id,
            "user_message_id": user_chat.id,
            "ai_message_id": ai_chat.id
        })
    return JsonResponse({"error": "Invalid request method."}, status=400)

def create_session(request):
    """Create a new chat session"""
    if request.method == "POST":
        agent_config, _ = AgentConfiguration.objects.get_or_create(
            name="default",
            defaults={"parameters": {"model": "simulated"}}
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
        
        sessions_data.append({
            "id": session.id,
            "started_at": session.started_at.isoformat(),
            "message_count": message_count,
            "last_message": last_message.message if last_message else None,
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
