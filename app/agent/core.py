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
            messages.append({"role": "system", "content": personality_prompt + "\n Reply with the specified personality in mind. Reply with HTML. Reply in the sender's language."})

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
        # md = (
            # MarkdownIt('commonmark', {'breaks':True,'html':False})
            # .enable('table')
        # )
        # return md.render(text)
        # print(text)
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