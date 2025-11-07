from agent.models import AgentConfiguration, ChatSession, ChatInformation
from django.utils import timezone
from django.db import models
import openai
from markdown_it import MarkdownIt
import json
from agent.prompt import (
    SPLIT_MESSAGE_SYSTEM_PROMPT,
    SUMMARIZE_PROMPT_WITH_EXISTING,
    SUMMARIZE_PROMPT_NO_EXISTING,
    PERSONALITY_ANALYSIS_PROMPT,
    PROACTIVE_DECISION_PROMPT,
)


def generate_response(user_message, agent_config, session, api_key=None, base_url=None):
    """
    Generate a response from the OpenAI API based on user message and agent configuration.

    Returns:
        dict or str: If the LLM returns valid JSON with split messages, returns a dict like:
                     {"messages": ["msg1", "msg2", ...]}
                     Otherwise returns a plain string response.
    """
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
        system_message = ""

        if personality_prompt:
            system_message = personality_prompt + "\n\n"

        system_message += SPLIT_MESSAGE_SYSTEM_PROMPT

        messages.append({"role": "system", "content": system_message})

        chat_history = session.chat_infos.order_by("-chat_date")[:20]
        # Reverse to get chronological order
        for chat in reversed(chat_history):
            role = "user" if chat.is_user else "assistant"
            messages.append({"role": role, "content": chat.message})

        # Add current user message
        messages.append({"role": "user", "content": user_message})

        # Get model from agent configuration or use default
        model = agent_config.parameters.get("model", "gpt-3.5-turbo")

        # Call OpenAI API
        response = client.chat.completions.create(model=model, messages=messages)
        text = response.choices[0].message.content

        # Try to parse as JSON first to check if LLM returned split messages
        try:
            # Strip any markdown code block markers if present
            cleaned_text = text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.startswith("```"):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
            cleaned_text = cleaned_text.strip()

            # Try to parse as JSON
            parsed = json.loads(cleaned_text)

            # Validate the structure
            if isinstance(parsed, dict) and "messages" in parsed:
                messages_list = parsed["messages"]
                if isinstance(messages_list, list) and len(messages_list) > 0:
                    # All items should be strings
                    if all(isinstance(msg, str) for msg in messages_list):
                        return {"messages": messages_list}

            # If structure is invalid, fall back to plain text
            return text
        except (json.JSONDecodeError, ValueError):
            # Not JSON, return as plain text
            return text

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
    recent_messages = session.chat_infos.order_by("chat_date")

    if recent_messages.count() == 0:
        return "New conversation"

    # If no API key is provided, create a simple fallback summary
    if not api_key:
        first_user_msg = recent_messages.filter(is_user=True).first()
        if first_user_msg:
            # Truncate to first 50 characters
            return (
                first_user_msg.message[:50] + "..."
                if len(first_user_msg.message) > 50
                else first_user_msg.message
            )
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
            prompt = SUMMARIZE_PROMPT_WITH_EXISTING.format(existing_summary=existing_summary)
        else:
            prompt = SUMMARIZE_PROMPT_NO_EXISTING.format(conversation_text=conversation_text)

        # Get model from agent configuration
        model = agent_config.parameters.get("model", "gpt-3.5-turbo")

        # Call OpenAI API for summarization
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that creates brief, concise summaries of conversations. Keep summaries under 100 characters.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=50,
            temperature=0.5,
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
            return (
                first_user_msg.message[:50] + "..."
                if len(first_user_msg.message) > 50
                else first_user_msg.message
            )
        return "Chat session"

def decide_personality_update(session, agent_config, api_key=None, base_url=None):
    """
    Analyze the conversation and decide whether the agent's personality should be updated.

    This function is called after a certain number of chat rounds to determine if the
    agent's personality prompt should be adjusted based on the conversation patterns.

    Args:
        session: ChatSession object
        agent_config: AgentConfiguration object
        api_key: OpenAI API key (optional)
        base_url: OpenAI base URL (optional)

    Returns:
        dict: Decision result with keys:
            - should_update: bool indicating if personality should be updated
            - reason: explanation for the decision
            - suggested_personality: optional suggested personality prompt
            - confidence: confidence score (0.0 to 1.0)
    """
    # Get session information
    message_count = session.message_count
    current_personality = agent_config.parameters.get("personality_prompt", "")

    # Only consider updating after a minimum number of messages
    MIN_MESSAGES_FOR_UPDATE = 20

    if message_count < MIN_MESSAGES_FOR_UPDATE:
        return {
            "should_update": False,
            "reason": f"Not enough messages yet (need at least {MIN_MESSAGES_FOR_UPDATE}, have {message_count})",
            "suggested_personality": None,
            "confidence": 0.0,
        }

    # If no API key provided, use simple heuristic
    if not api_key:
        # Simple heuristic: suggest update every 50 messages if personality is empty or basic
        if message_count % 50 == 0:
            if not current_personality:
                return {
                    "should_update": True,
                    "reason": "No personality set, consider adding one based on conversation",
                    "suggested_personality": "You are a helpful and friendly assistant.",
                    "confidence": 0.5,
                }

        return {
            "should_update": False,
            "reason": "No API key available for advanced analysis",
            "suggested_personality": None,
            "confidence": 0.0,
        }

    try:
        # Configure OpenAI client
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url

        client = openai.OpenAI(**client_kwargs)

        # Get recent chat history (last 30 messages for analysis)
        recent_messages = session.chat_infos.order_by("-chat_date")[:30]
        conversation_text = ""
        for chat in reversed(recent_messages):
            role = "User" if chat.is_user else "AI"
            conversation_text += f"{role}: {chat.message}\n"

        # Analyze conversation patterns
        current_personality_text = (
            current_personality
            if current_personality
            else "No specific personality set"
        )

        prompt = PERSONALITY_ANALYSIS_PROMPT.format(
            current_personality_text=current_personality_text,
            message_count=message_count,
            session_summary=session.summary or "No summary available",
            conversation_text=conversation_text,
        )

        # Get model from agent configuration
        model = agent_config.parameters.get("model", "gpt-3.5-turbo")

        # Call OpenAI API for analysis
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at analyzing conversations and determining optimal AI personality configurations. Always respond with valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )

        result_text = response.choices[0].message.content.strip()

        # Parse JSON response
        import json

        try:
            result = json.loads(result_text)
        except json.JSONDecodeError as e:
            # If JSON parsing fails, return no update
            return {
                "should_update": False,
                "reason": f"Failed to parse AI response: {str(e)}",
                "suggested_personality": None,
                "confidence": 0.0,
            }

        # Validate response structure
        required_keys = [
            "should_update",
            "reason",
            "suggested_personality",
            "confidence",
        ]
        if not all(key in result for key in required_keys):
            raise ValueError("Missing required keys in response")

        return result

    except Exception as e:
        # Fallback on error
        return {
            "should_update": False,
            "reason": f"Error analyzing conversation: {str(e)}",
            "suggested_personality": None,
            "confidence": 0.0,
        }


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
    # Check for unread messages first
    # If there are unread AI messages (messages sent by AI that user hasn't read yet),
    # we should NOT send new proactive messages based on inactivity
    unread_ai_messages = session.chat_infos.filter(is_agent=True, is_read=False)
    has_unread_messages = unread_ai_messages.exists()
    unread_count = unread_ai_messages.count()

    # Get session summary and recent activity
    summary = session.summary or "No summary available"
    message_count = session.message_count

    # Get timing configuration from agent config
    timings = agent_config.timings or {}
    inactivity_threshold = timings.get("inactivity_check_minutes", 5)

    # Calculate inactivity duration
    from django.utils import timezone
    from datetime import timedelta

    if not session.last_activity_at:
        return {
            "action": "wait",
            "reason": "No activity recorded yet",
            "suggested_message": None,
        }

    time_since_activity = timezone.now() - session.last_activity_at
    minutes_inactive = time_since_activity.total_seconds() / 60

    # If there are unread messages, do NOT send new messages based on inactivity
    # Only time-based scheduling should trigger messages in this case
    if has_unread_messages:
        return {
            "action": "wait",
            "reason": f"User has {unread_count} unread message(s). Waiting for user to read them first.",
            "suggested_message": None,
            "unread_count": unread_count,
        }

    # If not enough time has passed, wait
    if minutes_inactive < inactivity_threshold:
        return {
            "action": "wait",
            "reason": f"Only {minutes_inactive:.1f} minutes inactive, threshold is {inactivity_threshold}",
            "suggested_message": None,
        }

    # If no API key provided, use simple rule-based decision
    if not api_key:
        # Simple fallback: if conversation has fewer than 5 messages, suggest waiting
        if message_count < 5:
            return {
                "action": "wait",
                "reason": "Conversation too short to make a decision (no API key)",
                "suggested_message": None,
            }
        else:
            return {
                "action": "continue",
                "reason": "Sufficient conversation history (no API key)",
                "suggested_message": "Would you like to continue our discussion, or is there anything else I can help you with?",
            }

    try:
        # Configure OpenAI client
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url

        client = openai.OpenAI(**client_kwargs)

        # Get recent chat history
        recent_messages = session.chat_infos.order_by("-chat_date")[:10]
        conversation_text = ""
        for chat in reversed(recent_messages):
            role = "User" if chat.is_user else "AI"
            conversation_text += f"{role}: {chat.message}\n"

        # Get user preferences from agent config
        # proactive_behavior can be: 'conservative', 'balanced', 'aggressive'
        # This preference guides how eagerly the AI should initiate conversations
        user_preferences = agent_config.parameters.get("proactive_behavior", "balanced")

        # Add unread message information to prompt if applicable
        unread_info = ""
        if has_unread_messages:
            unread_info = f"\nNote: User has {unread_count} unread AI message(s). This information is provided for context."

        # Create decision prompt
        prompt = PROACTIVE_DECISION_PROMPT.format(
            summary=summary,
            message_count=message_count,
            minutes_inactive=minutes_inactive,
            user_preferences=user_preferences,
            unread_info=unread_info,
            conversation_text=conversation_text,
        )

        # Get model from agent configuration
        model = agent_config.parameters.get("model", "gpt-3.5-turbo")

        # Call OpenAI API for decision making
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that makes smart decisions about proactive conversation engagement. Always respond with valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )

        result_text = response.choices[0].message.content.strip()

        # Parse JSON response
        import json

        try:
            result = json.loads(result_text)
        except json.JSONDecodeError as e:
            # If JSON parsing fails, return wait action with error details
            return {
                "action": "wait",
                "reason": f"Failed to parse AI response: {str(e)}",
                "suggested_message": None,
            }

        # Validate response structure
        if "action" not in result or result["action"] not in [
            "continue",
            "new_topic",
            "wait",
        ]:
            raise ValueError("Invalid action in response")

        return result

    except Exception as e:
        # Fallback to simple decision on error
        return {
            "action": "wait",
            "reason": f"Error making AI decision: {str(e)}",
            "suggested_message": None,
        }


# etc.
