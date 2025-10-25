"""
Main Proactive RAG Chatbot that orchestrates all three agents
"""

from typing import Optional, Dict, Any
from .agents import ConversationAgent, MemoryAgent, ProactiveAgent
from .models import PersonalityProfile, Message


class ProactiveRAGChatbot:
    """
    Multi-agent Haystack RAG Chatbot that combines:
    - Conversation Agent: RAG-based responses with personality
    - Memory Agent: Short and Long-term memory management
    - Proactive Agent: Dynamic personality updates and proactive engagement
    """
    
    def __init__(
        self,
        api_key: str,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        llm_model: str = "gpt-3.5-turbo",
        max_short_term_messages: int = 10,
        summarization_interval: int = 5,
        personality_update_threshold: int = 20,
        proactive_trigger_interval: int = 10
    ):
        """
        Initialize the Proactive RAG Chatbot.
        
        Args:
            api_key: OpenAI API key
            embedding_model: Model for embeddings
            llm_model: LLM model name
            max_short_term_messages: Max messages in short-term memory
            summarization_interval: Number of turns before summarizing to long-term (e.g., 5)
            personality_update_threshold: Interactions before personality update
            proactive_trigger_interval: Turns between proactive engagements (e.g., 10)
        """
        # Initialize the three agents
        self.conversation_agent = ConversationAgent(
            api_key=api_key,
            embedding_model=embedding_model,
            llm_model=llm_model
        )
        
        self.memory_agent = MemoryAgent(
            max_short_term_messages=max_short_term_messages,
            summarization_interval=summarization_interval
        )
        
        self.proactive_agent = ProactiveAgent(
            personality_update_threshold=personality_update_threshold,
            proactive_trigger_interval=proactive_trigger_interval
        )
        
        self.is_initialized = True
    
    def add_knowledge(self, documents: list):
        """
        Add documents to the RAG knowledge base.
        
        Args:
            documents: List of document strings
        """
        self.conversation_agent.add_knowledge(documents)
    
    def chat(self, user_message: str) -> Dict[str, Any]:
        """
        Process a user message and generate a response.
        
        Args:
            user_message: User's message
            
        Returns:
            Dictionary with transparent response parts and metadata
        """
        # Add user message to memory
        self.memory_agent.add_message("user", user_message)
        
        # Check if proactive personality update is needed
        if self.proactive_agent.should_update_personality():
            long_term_memory = self.memory_agent.get_long_term_memory()
            current_profile = self.conversation_agent.personality_profile
            
            # Update personality profile
            updated_profile = self.proactive_agent.update_personality_profile(
                current_profile,
                long_term_memory
            )
            self.conversation_agent.update_personality(updated_profile)
        
        # Get conversation history from short-term memory
        history = self.memory_agent.get_short_term_memory().messages
        
        # Generate response using conversation agent (returns dict with parts)
        response_parts = self.conversation_agent.chat(user_message, history)
        
        # Add assistant response to memory
        self.memory_agent.add_message("assistant", response_parts["full"])
        
        # Increment interaction counter
        self.proactive_agent.increment_interaction()
        
        # Check for proactive chat opportunity
        proactive_context = self.proactive_agent.generate_proactive_context(
            self.memory_agent.get_long_term_memory(),
            self.conversation_agent.personality_profile
        )
        
        # Format transparent output: Part 1 (Factual)#Part 2 (Personality)#Part 3 (Proactive)
        transparent_output = f"[Factual Context]\n{response_parts['factual']}\n\n"
        transparent_output += f"[Personality Context]\n{response_parts['personality']}\n\n"
        
        proactive_part = ""
        if proactive_context and proactive_context.suggested_prompt:
            proactive_part = f"[Proactive Engagement]\n{proactive_context.suggested_prompt}"
        else:
            proactive_part = "[Proactive Engagement]\nNo proactive engagement at this turn."
        transparent_output += proactive_part
        
        return {
            "response": response_parts["full"],
            "transparent_output": transparent_output,
            "factual_part": response_parts["factual"],
            "personality_part": response_parts["personality"],
            "proactive_part": proactive_part,
            "proactive_context": proactive_context,
            "personality_updated": self.proactive_agent.should_update_personality(),
            "interaction_count": self.proactive_agent.interaction_count,
            "turn_count": self.memory_agent.turn_count
        }
    
    def get_proactive_message(self) -> Optional[str]:
        """
        Get a proactive message if one should be triggered.
        
        Returns:
            Proactive message or None
        """
        proactive_context = self.proactive_agent.generate_proactive_context(
            self.memory_agent.get_long_term_memory(),
            self.conversation_agent.personality_profile
        )
        
        if proactive_context and proactive_context.suggested_prompt:
            return proactive_context.suggested_prompt
        
        return None
    
    def get_personality_profile(self) -> PersonalityProfile:
        """Get current personality profile"""
        return self.conversation_agent.personality_profile
    
    def get_memory_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the memory state.
        
        Returns:
            Dictionary with memory information
        """
        short_term = self.memory_agent.get_short_term_memory()
        long_term = self.memory_agent.get_long_term_memory()
        
        return {
            "short_term_messages": len(short_term.messages),
            "long_term_summaries": len(long_term.summaries),
            "key_facts": long_term.key_facts,
            "user_insights": long_term.user_insights,
            "conversation_count": long_term.conversation_count
        }
    
    def force_personality_update(self):
        """Force a personality profile update"""
        long_term_memory = self.memory_agent.get_long_term_memory()
        current_profile = self.conversation_agent.personality_profile
        
        updated_profile = self.proactive_agent.update_personality_profile(
            current_profile,
            long_term_memory
        )
        self.conversation_agent.update_personality(updated_profile)
