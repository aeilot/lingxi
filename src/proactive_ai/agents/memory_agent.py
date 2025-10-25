"""
Memory Agent - Summarizes chats into Short-Term and Long-Term Memory
"""

from typing import List, Optional
from ..models import Message, ShortTermMemory, LongTermMemory


class MemoryAgent:
    """
    Memory Agent that manages both Short-Term and Long-Term Memory.
    Summarizes conversations and extracts key information.
    """
    
    def __init__(
        self,
        max_short_term_messages: int = 10,
        long_term_threshold: int = 50
    ):
        """
        Initialize the Memory Agent.
        
        Args:
            max_short_term_messages: Maximum messages in short-term memory
            long_term_threshold: Number of messages before summarizing to long-term
        """
        self.short_term_memory = ShortTermMemory(max_size=max_short_term_messages)
        self.long_term_memory = LongTermMemory()
        self.long_term_threshold = long_term_threshold
        self.total_messages = 0
    
    def add_message(self, role: str, content: str):
        """
        Add a message to short-term memory.
        
        Args:
            role: Message role (user/assistant)
            content: Message content
        """
        self.short_term_memory.add_message(role, content)
        self.total_messages += 1
        
        # Check if we need to summarize to long-term memory
        if self.total_messages >= self.long_term_threshold:
            self._summarize_to_long_term()
    
    def _summarize_to_long_term(self):
        """Summarize short-term memory to long-term memory"""
        messages = self.short_term_memory.messages
        
        if not messages:
            return
        
        # Create a simple summary
        summary = self._create_summary(messages)
        self.long_term_memory.add_summary(summary)
        
        # Extract key facts and insights
        facts = self._extract_facts(messages)
        for fact in facts:
            self.long_term_memory.add_key_fact(fact)
        
        # Extract user insights
        insights = self._extract_user_insights(messages)
        for key, value in insights.items():
            self.long_term_memory.add_user_insight(key, value)
        
        # Reset counter
        self.total_messages = 0
    
    def _create_summary(self, messages: List[Message]) -> str:
        """
        Create a summary of the conversation.
        
        Args:
            messages: List of messages to summarize
            
        Returns:
            Summary string
        """
        # Simple summary based on message count and topics
        user_messages = [m for m in messages if m.role == "user"]
        assistant_messages = [m for m in messages if m.role == "assistant"]
        
        summary = f"Conversation with {len(messages)} messages "
        summary += f"({len(user_messages)} from user, {len(assistant_messages)} from assistant). "
        
        # Extract key topics (simple keyword extraction)
        topics = self._extract_topics(messages)
        if topics:
            summary += f"Topics discussed: {', '.join(topics[:5])}."
        
        return summary
    
    def _extract_topics(self, messages: List[Message]) -> List[str]:
        """
        Extract topics from messages.
        
        Args:
            messages: List of messages
            
        Returns:
            List of topics
        """
        # Simple topic extraction based on common words
        # In a production system, this would use NLP techniques
        topics = set()
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'is', 'are', 'was', 'were', 'i', 'you', 'we', 'they'}
        
        for msg in messages:
            words = msg.content.lower().split()
            for word in words:
                if len(word) > 4 and word not in common_words:
                    topics.add(word)
        
        return list(topics)
    
    def _extract_facts(self, messages: List[Message]) -> List[str]:
        """
        Extract key facts from messages.
        
        Args:
            messages: List of messages
            
        Returns:
            List of facts
        """
        facts = []
        
        # Look for factual statements in user messages
        for msg in messages:
            if msg.role == "user":
                # Simple heuristic: sentences with "I am", "I like", "I have", etc.
                content = msg.content
                if any(phrase in content.lower() for phrase in ["i am", "i like", "i have", "i prefer", "my name is"]):
                    facts.append(content)
        
        return facts[:5]  # Return up to 5 facts
    
    def _extract_user_insights(self, messages: List[Message]) -> dict:
        """
        Extract user insights from messages.
        
        Args:
            messages: List of messages
            
        Returns:
            Dictionary of insights
        """
        insights = {}
        
        # Look for patterns in user messages
        for msg in messages:
            if msg.role == "user":
                content = msg.content.lower()
                
                # Extract preferences
                if "i like" in content or "i love" in content:
                    insights["preferences"] = msg.content
                
                # Extract interests
                if "interested in" in content or "hobby" in content:
                    insights["interests"] = msg.content
                
                # Extract name
                if "my name is" in content or "i am" in content:
                    insights["identity"] = msg.content
        
        return insights
    
    def get_short_term_memory(self) -> ShortTermMemory:
        """Get short-term memory"""
        return self.short_term_memory
    
    def get_long_term_memory(self) -> LongTermMemory:
        """Get long-term memory (M_long)"""
        return self.long_term_memory
    
    def get_context_for_conversation(self) -> str:
        """
        Get memory context for conversation.
        
        Returns:
            Context string combining short and long-term memory
        """
        context = ""
        
        # Add long-term memory context
        if self.long_term_memory.summaries or self.long_term_memory.key_facts:
            context += self.long_term_memory.get_context()
            context += "\n"
        
        return context
    
    def force_summarize(self):
        """Force a summarization to long-term memory"""
        self._summarize_to_long_term()
