"""
Utility functions for the Proactive AI chatbot
"""

import os
from typing import Optional
from dotenv import load_dotenv


def load_config() -> dict:
    """
    Load configuration from environment variables.
    
    Returns:
        Dictionary with configuration
    """
    load_dotenv()
    
    return {
        "api_key": os.getenv("OPENAI_API_KEY"),
        "embedding_model": os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
        "llm_model": os.getenv("LLM_MODEL", "gpt-3.5-turbo"),
        "max_short_term_messages": int(os.getenv("MAX_SHORT_TERM_MESSAGES", "10")),
        "summarization_interval": int(os.getenv("SUMMARIZATION_INTERVAL", "5")),
        "personality_update_threshold": int(os.getenv("PERSONALITY_UPDATE_THRESHOLD", "20")),
        "proactive_trigger_interval": int(os.getenv("PROACTIVE_TRIGGER_INTERVAL", "10"))
    }


def validate_config(config: dict) -> bool:
    """
    Validate configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        True if valid, False otherwise
    """
    if not config.get("api_key"):
        print("Error: OPENAI_API_KEY not set in environment")
        return False
    
    return True
