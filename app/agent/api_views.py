from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone
from .models import AgentConfiguration, ChatSession, ChatInformation
from .serializers import (
    AgentConfigurationSerializer,
    ChatSessionSerializer,
    ChatInformationSerializer,
    ChatMessageSerializer,
    UserSerializer
)
from .core import generate_response, generate_session_summary, decide_personality_update


class AgentConfigurationViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing agent configurations.
    
    list: Get all agents for the authenticated user
    create: Create a new agent
    retrieve: Get a specific agent
    update: Update an agent
    partial_update: Partially update an agent
    destroy: Delete an agent
    """
    serializer_class = AgentConfigurationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return agents for the authenticated user"""
        return AgentConfiguration.objects.filter(user=self.request.user)

    @action(detail=True, methods=['put', 'patch'])
    def personality(self, request, pk=None):
        """Update the personality of an agent"""
        agent = self.get_object()
        personality_prompt = request.data.get('personality_prompt', '')
        
        agent.parameters['personality_prompt'] = personality_prompt
        agent.save()
        
        return Response({
            'success': True,
            'personality_prompt': personality_prompt
        })


class ChatSessionViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing chat sessions.
    
    list: Get all chat sessions for the authenticated user
    create: Create a new chat session
    retrieve: Get a specific chat session with full message history
    destroy: Delete a chat session
    """
    serializer_class = ChatSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return sessions for the authenticated user"""
        return ChatSession.objects.filter(user=self.request.user).order_by('-started_at')

    def retrieve(self, request, pk=None):
        """Get session with messages"""
        session = self.get_object()
        
        # Mark all AI messages as read
        session.chat_infos.filter(is_agent=True, is_read=False).update(is_read=True)
        
        serializer = self.get_serializer(session)
        return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def chat(request):
    """
    Send a message to the AI agent and get a response.
    
    Request body:
    - message: The message to send
    - session_id (optional): ID of existing session to continue
    - agent_id (optional): ID of agent to use (defaults to user's default agent)
    
    Returns:
    - session_id: The session ID
    - response: The AI response (single message)
    - messages (optional): Array of messages if AI split the response
    - summary_updated (optional): True if session summary was updated
    - personality_updated (optional): True if personality was auto-updated
    """
    serializer = ChatMessageSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    user_message = serializer.validated_data['message']
    session_id = serializer.validated_data.get('session_id')
    agent_id = serializer.validated_data.get('agent_id')
    
    # Get API settings
    api_key = settings.OPENAI_API_KEY
    base_url = settings.OPENAI_BASE_URL
    model = settings.OPENAI_MODEL
    
    # Get or create agent configuration
    if agent_id:
        try:
            agent_config = AgentConfiguration.objects.get(id=agent_id, user=request.user)
        except AgentConfiguration.DoesNotExist:
            return Response({'error': 'Agent not found'}, status=status.HTTP_404_NOT_FOUND)
    else:
        # Get or create default agent for this user
        agent_config, _ = AgentConfiguration.objects.get_or_create(
            name="default",
            user=request.user,
            defaults={"parameters": {"model": model, "personality_prompt": ""}}
        )
    
    # Get or create chat session
    if session_id:
        try:
            session = ChatSession.objects.get(id=session_id, user=request.user)
        except ChatSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)
    else:
        session = ChatSession.objects.create(
            user=request.user,
            agent_configuration=agent_config
        )
    
    # Mark all previous AI messages as read
    session.chat_infos.filter(is_agent=True, is_read=False).update(is_read=True)
    
    # Save user message
    user_chat = ChatInformation.objects.create(
        message=user_message,
        is_user=True,
        is_agent=False
    )
    session.chat_infos.add(user_chat)
    
    # Generate response
    model_response = generate_response(user_message, agent_config, session, api_key=api_key, base_url=base_url)
    
    # Handle split messages or single message
    ai_message_ids = []
    messages_list = []
    
    if isinstance(model_response, dict) and "messages" in model_response:
        for msg_text in model_response["messages"]:
            ai_chat = ChatInformation.objects.create(
                message=msg_text,
                is_user=False,
                is_agent=True
            )
            session.chat_infos.add(ai_chat)
            ai_message_ids.append(ai_chat.id)
            messages_list.append(msg_text)
    else:
        ai_chat = ChatInformation.objects.create(
            message=model_response,
            is_user=False,
            is_agent=True
        )
        session.chat_infos.add(ai_chat)
        ai_message_ids.append(ai_chat.id)
        messages_list.append(model_response)
    
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
        decision = decide_personality_update(session, agent_config, api_key=api_key, base_url=base_url)
        
        if session.current_state is None:
            session.current_state = {}
        
        session.current_state['last_personality_check'] = timezone.now().isoformat()
        
        CONFIDENCE_THRESHOLD = 0.8
        if decision.get('should_update') and decision.get('confidence', 0) > CONFIDENCE_THRESHOLD:
            suggested_personality = decision.get('suggested_personality')
            if suggested_personality:
                agent_config.parameters["personality_prompt"] = suggested_personality
                agent_config.save()
                personality_updated = True
                session.current_state['last_personality_auto_update'] = {
                    'timestamp': timezone.now().isoformat(),
                    'personality': suggested_personality,
                    'reason': decision.get('reason'),
                    'confidence': decision.get('confidence')
                }
        else:
            if decision.get('should_update'):
                session.current_state['personality_update_suggestion'] = decision
                personality_suggestion = decision
    
    session.save()
    
    # Build response
    response_data = {
        "session_id": session.id,
        "user_message_id": user_chat.id,
    }
    
    if len(messages_list) == 1:
        response_data["response"] = messages_list[0]
        response_data["ai_message_id"] = ai_message_ids[0]
    else:
        response_data["messages"] = [
            {"id": msg_id, "message": msg_text}
            for msg_id, msg_text in zip(ai_message_ids, messages_list)
        ]
        response_data["response"] = messages_list[0]
        response_data["ai_message_id"] = ai_message_ids[0]
    
    if summary_updated:
        response_data["summary_updated"] = True
        response_data["summary"] = session.summary
    
    if personality_updated:
        response_data["personality_updated"] = True
        response_data["personality_prompt"] = agent_config.parameters.get("personality_prompt")
    elif personality_suggestion:
        response_data["personality_suggestion_available"] = True
    
    return Response(response_data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def chat_history(request):
    """
    Get chat history for the authenticated user.
    
    Query parameters:
    - session_id (optional): Filter by specific session
    - limit (optional): Limit number of messages returned (default: 100)
    
    Returns:
    - sessions: Array of sessions with their messages
    """
    session_id = request.query_params.get('session_id')
    limit = int(request.query_params.get('limit', 100))
    
    if session_id:
        try:
            sessions = ChatSession.objects.filter(id=session_id, user=request.user)
        except ChatSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)
    else:
        sessions = ChatSession.objects.filter(user=request.user).order_by('-started_at')[:limit]
    
    serializer = ChatSessionSerializer(sessions, many=True)
    return Response({'sessions': serializer.data})
