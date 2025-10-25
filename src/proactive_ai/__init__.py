"""
Proactive AI - Multi-agent Haystack RAG Chatbot
"""

__version__ = "0.1.0"

from .agents.conversation_agent import ConversationAgent
from .agents.memory_agent import MemoryAgent
from .agents.proactive_agent import ProactiveAgent
from .chatbot import ProactiveRAGChatbot

__all__ = [
    "ConversationAgent",
    "MemoryAgent",
    "ProactiveAgent",
    "ProactiveRAGChatbot",
]
