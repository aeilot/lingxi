from agent.models import AgentConfiguration, ChatSession, ChatInformation
from django.utils import timezone
from django.db import models
import openai

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
        
        # Get chat history from session
        messages = []
        chat_history = session.chat_infos.order_by('chat_date')
        for chat in chat_history:
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
        
        return response.choices[0].message.content
    
    except Exception as e:
        # Return error message if OpenAI API call fails
        return f"Error calling OpenAI API: {str(e)}"

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


# etc.