from agent.models import AgentConfiguration, ChatSession, ChatInformation
from django.utils import timezone
from django.db import models
import openai
from markdown_it import MarkdownIt

def generate_response(user_message, agent_config, session, api_key=None, base_url=None):
    """Generate a response from the OpenAI API based on user message and agent configuration."""
    # If no API key is provided, fall back to simulated response
    if not api_key:
        return f"Simulated response to: {user_message}"
    
    try:
        # Configure OpenAI client
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        
        client = openai.OpenAI(**client_kwargs)
        
        # Get recent chat history from session (limit to last 20 messages for performance)
        messages = []
        
        # Add system message with personality prompt if configured
        personality_prompt = agent_config.parameters.get("personality_prompt", "")
        if personality_prompt:
            messages.append({"role": "system", "content": personality_prompt + "\n Reply with the specified personality in mind. Reply with plain text and don't wrap it in a code block. Reply in the sender's language."})

        chat_history = session.chat_infos.order_by('-chat_date')[:20]
        # Reverse to get chronological order
        for chat in reversed(chat_history):
            role = "user" if chat.is_user else "assistant"
            messages.append({"role": role, "content": chat.message})
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        # Get model from agent configuration or use default
        model = agent_config.parameters.get("model", "gpt-3.5-turbo")

        # Call OpenAI API
        response = client.chat.completions.create(
            model=model,
            messages=messages
        )
        text = response.choices[0].message.content
        md = (
            MarkdownIt('commonmark', {'breaks':True,'html':False})
            .enable('table')
        )
        return md.render(text)
        # print(text)
        # return text
    
    except openai.AuthenticationError:
        return "Error calling OpenAI API: Invalid API key. Please check your settings."
    except openai.APIConnectionError:
        return "Error calling OpenAI API: Connection error. Please check your network or base URL."
    except openai.RateLimitError:
        return "Error calling OpenAI API: Rate limit exceeded. Please try again later."
    except Exception as e:
        # Return generic error message without exposing internal details
        return "Error calling OpenAI API: An unexpected error occurred. Please check your settings."

def generate_session_summary(session, agent_config, api_key=None, base_url=None):
    """Generate or update a summary of the chat session using OpenAI API."""
    # Get recent messages (last 10 messages)
    recent_messages = session.chat_infos.order_by('chat_date')
    
    if recent_messages.count() == 0:
        return "New conversation"
    
    # If no API key is provided, create a simple fallback summary
    if not api_key:
        first_user_msg = recent_messages.filter(is_user=True).first()
        if first_user_msg:
            # Truncate to first 50 characters
            return first_user_msg.message[:50] + "..." if len(first_user_msg.message) > 50 else first_user_msg.message
        return "Chat session"
    
    try:
        # Configure OpenAI client
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        
        client = openai.OpenAI(**client_kwargs)
        
        # Build conversation history for summarization
        conversation_text = ""
        for chat in recent_messages:
            role = "User" if chat.is_user else "AI"
            conversation_text += f"{role}: {chat.message}\n"
        
        # Create summarization prompt
        existing_summary = session.summary or ""
        if existing_summary:
            prompt = f"""You are summarizing a chat conversation. Here is the existing summary:
"{existing_summary}"

Here are the recent messages from the conversation:
{conversation_text}

Please provide an updated summary that incorporates the new messages. The summary should be brief (1-2 sentences, max 100 characters) and capture the main topic of the conversation. Return only the summary text, nothing else."""
        else:
            prompt = f"""You are summarizing a chat conversation. Here are the messages:
{conversation_text}

Please provide a brief summary (1-2 sentences, max 100 characters) that captures the main topic of the conversation. Return only the summary text, nothing else."""
        
        # Get model from agent configuration
        model = agent_config.parameters.get("model", "gpt-3.5-turbo")
        
        # Call OpenAI API for summarization
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that creates brief, concise summaries of conversations. Keep summaries under 100 characters."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=50,
            temperature=0.5
        )
        
        summary = response.choices[0].message.content.strip()
        
        # Ensure summary is not too long (truncate if needed)
        if len(summary) > 100:
            summary = summary[:97] + "..."
        
        return summary
    
    except Exception as e:
        # Fallback to simple summary on error
        first_user_msg = recent_messages.filter(is_user=True).first()
        if first_user_msg:
            return first_user_msg.message[:50] + "..." if len(first_user_msg.message) > 50 else first_user_msg.message
        return "Chat session"

def create_summary(session):
    """Generate a summary of the chat session."""
    messages = session.chat_infos.order_by('timestamp').values_list('message', flat=True)
    # do something
    summary = " | ".join(messages[:5])  # Simple summary: first 5 messages concatenated
    return summary

def should_update_agent_config(old_config, new_config):
    """Determine if the agent configuration needs to be updated."""
    # do something
    return old_config.parameters != new_config.parameters


def DecisionModule(session, agent_config, api_key=None, base_url=None):
    """
    Make an AI-based decision on whether to proactively continue or start a new topic.
    
    This function analyzes the chat summary and user settings to determine the best action
    when the user has stopped chatting.
    
    Args:
        session: ChatSession object
        agent_config: AgentConfiguration object
        api_key: OpenAI API key (optional)
        base_url: OpenAI base URL (optional)
    
    Returns:
        dict: Decision result with keys:
            - action: 'continue', 'new_topic', or 'wait'
            - reason: explanation for the decision
            - suggested_message: optional message to send (if action is 'continue' or 'new_topic')
    """
    # Get session summary and recent activity
    summary = session.summary or "No summary available"
    message_count = session.message_count
    
    # Get timing configuration from agent config
    timings = agent_config.timings or {}
    inactivity_threshold = timings.get('inactivity_check_minutes', 5)
    
    # Calculate inactivity duration
    from django.utils import timezone
    from datetime import timedelta
    
    if not session.last_activity_at:
        return {
            'action': 'wait',
            'reason': 'No activity recorded yet',
            'suggested_message': None
        }
    
    time_since_activity = timezone.now() - session.last_activity_at
    minutes_inactive = time_since_activity.total_seconds() / 60
    
    # If not enough time has passed, wait
    if minutes_inactive < inactivity_threshold:
        return {
            'action': 'wait',
            'reason': f'Only {minutes_inactive:.1f} minutes inactive, threshold is {inactivity_threshold}',
            'suggested_message': None
        }
    
    # If no API key provided, use simple rule-based decision
    if not api_key:
        # Simple fallback: if conversation has fewer than 5 messages, suggest waiting
        if message_count < 5:
            return {
                'action': 'wait',
                'reason': 'Conversation too short to make a decision (no API key)',
                'suggested_message': None
            }
        else:
            return {
                'action': 'continue',
                'reason': 'Sufficient conversation history (no API key)',
                'suggested_message': 'Would you like to continue our discussion, or is there anything else I can help you with?'
            }
    
    try:
        # Configure OpenAI client
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        
        client = openai.OpenAI(**client_kwargs)
        
        # Get recent chat history
        recent_messages = session.chat_infos.order_by('-chat_date')[:10]
        conversation_text = ""
        for chat in reversed(recent_messages):
            role = "User" if chat.is_user else "AI"
            conversation_text += f"{role}: {chat.message}\n"
        
        # Get user preferences from agent config
        # proactive_behavior can be: 'conservative', 'balanced', 'aggressive'
        # This preference guides how eagerly the AI should initiate conversations
        user_preferences = agent_config.parameters.get('proactive_behavior', 'balanced')
        
        # Create decision prompt
        prompt = f"""You are analyzing a chat conversation to decide whether the AI should proactively continue the conversation.

Current summary: {summary}
Message count: {message_count}
Minutes inactive: {minutes_inactive:.1f}
User preference for proactivity: {user_preferences}

Recent conversation:
{conversation_text}

Based on this information, decide whether the AI should:
1. 'continue' - proactively continue the current topic with a relevant follow-up
2. 'new_topic' - suggest starting a new related topic
3. 'wait' - wait for the user to respond

Consider:
- Is the conversation at a natural stopping point?
- Are there unanswered questions or incomplete thoughts?
- Would a follow-up add value or feel pushy?
- What is the user's preference level for proactive behavior?

Respond ONLY with a JSON object in this exact format:
{{"action": "continue|new_topic|wait", "reason": "brief explanation", "suggested_message": "message to send or null"}}"""

        # Get model from agent configuration
        model = agent_config.parameters.get("model", "gpt-3.5-turbo")
        
        # Call OpenAI API for decision making
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that makes smart decisions about proactive conversation engagement. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Parse JSON response
        import json
        try:
            result = json.loads(result_text)
        except json.JSONDecodeError as e:
            # If JSON parsing fails, return wait action with error details
            return {
                'action': 'wait',
                'reason': f'Failed to parse AI response: {str(e)}',
                'suggested_message': None
            }
        
        # Validate response structure
        if 'action' not in result or result['action'] not in ['continue', 'new_topic', 'wait']:
            raise ValueError("Invalid action in response")
        
        return result
    
    except Exception as e:
        # Fallback to simple decision on error
        return {
            'action': 'wait',
            'reason': f'Error making AI decision: {str(e)}',
            'suggested_message': None
        }


# etc.