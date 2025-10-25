"""
Proactive Agent - Dynamically updates Personality Profile and triggers proactive chats
"""

import random
from typing import Optional, Dict, Any
from ..models import PersonalityProfile, LongTermMemory, ProactiveContext


class ProactiveAgent:
    """
    Proactive Agent that:
    1. Dynamically updates the Conversation Agent's Personality Profile (P_params)
    2. Triggers proactive chats to collect user data
    """
    
    def __init__(
        self,
        personality_update_threshold: int = 20,
        proactive_trigger_probability: float = 0.3
    ):
        """
        Initialize the Proactive Agent.
        
        Args:
            personality_update_threshold: Number of interactions before updating personality
            proactive_trigger_probability: Probability of triggering proactive chat
        """
        self.personality_update_threshold = personality_update_threshold
        self.proactive_trigger_probability = proactive_trigger_probability
        self.interaction_count = 0
        self.last_personality_update = 0
    
    def should_update_personality(self) -> bool:
        """
        Check if personality profile should be updated.
        
        Returns:
            True if personality should be updated
        """
        return (self.interaction_count - self.last_personality_update) >= self.personality_update_threshold
    
    def update_personality_profile(
        self,
        current_profile: PersonalityProfile,
        long_term_memory: LongTermMemory
    ) -> PersonalityProfile:
        """
        Update personality profile based on long-term memory (M_long).
        
        Args:
            current_profile: Current personality profile
            long_term_memory: Long-term memory to use for updates
            
        Returns:
            Updated personality profile
        """
        # Create a copy of the current profile
        updated_profile = PersonalityProfile(
            tone=current_profile.tone,
            formality=current_profile.formality,
            interests=current_profile.interests.copy(),
            communication_style=current_profile.communication_style,
            expertise_areas=current_profile.expertise_areas.copy(),
            user_preferences=current_profile.user_preferences.copy()
        )
        
        # Update based on user insights
        if long_term_memory.user_insights:
            for key, value in long_term_memory.user_insights.items():
                if key == "preferences":
                    # Extract preferences from the insight
                    preferences = self._extract_preferences(value)
                    updated_profile.user_preferences.update(preferences)
                
                elif key == "interests":
                    # Extract interests
                    interests = self._extract_interests(value)
                    for interest in interests:
                        if interest not in updated_profile.interests:
                            updated_profile.interests.append(interest)
        
        # Update communication style based on conversation patterns
        if long_term_memory.conversation_count > 5:
            # Adjust formality based on user patterns
            updated_profile = self._adjust_communication_style(
                updated_profile,
                long_term_memory
            )
        
        self.last_personality_update = self.interaction_count
        
        return updated_profile
    
    def _extract_preferences(self, text: str) -> Dict[str, str]:
        """Extract preferences from text"""
        preferences = {}
        
        # Simple extraction based on keywords
        if "formal" in text.lower():
            preferences["communication"] = "formal"
        elif "casual" in text.lower():
            preferences["communication"] = "casual"
        
        if "detailed" in text.lower():
            preferences["detail_level"] = "detailed"
        elif "brief" in text.lower() or "short" in text.lower():
            preferences["detail_level"] = "brief"
        
        return preferences
    
    def _extract_interests(self, text: str) -> list:
        """Extract interests from text"""
        interests = []
        
        # Simple keyword extraction
        # In production, this would use NLP
        common_interests = [
            "programming", "coding", "technology", "ai", "machine learning",
            "data science", "music", "sports", "reading", "travel", "cooking",
            "art", "photography", "gaming", "fitness"
        ]
        
        text_lower = text.lower()
        for interest in common_interests:
            if interest in text_lower:
                interests.append(interest)
        
        return interests
    
    def _adjust_communication_style(
        self,
        profile: PersonalityProfile,
        memory: LongTermMemory
    ) -> PersonalityProfile:
        """Adjust communication style based on memory"""
        # Analyze conversation patterns
        if memory.conversation_count > 10:
            # If user has many technical discussions, adjust to more technical style
            technical_keywords = ["code", "programming", "algorithm", "data", "api"]
            technical_count = sum(
                1 for fact in memory.key_facts
                if any(kw in fact.lower() for kw in technical_keywords)
            )
            
            if technical_count > len(memory.key_facts) * 0.5:
                profile.communication_style = "technical"
                if "technology" not in profile.expertise_areas:
                    profile.expertise_areas.append("technology")
        
        return profile
    
    def should_trigger_proactive_chat(self) -> bool:
        """
        Determine if a proactive chat should be triggered.
        
        Returns:
            True if proactive chat should be triggered
        """
        return random.random() < self.proactive_trigger_probability
    
    def generate_proactive_context(
        self,
        long_term_memory: LongTermMemory,
        personality_profile: PersonalityProfile
    ) -> Optional[ProactiveContext]:
        """
        Generate context for a proactive interaction.
        
        Args:
            long_term_memory: Long-term memory
            personality_profile: Current personality profile
            
        Returns:
            ProactiveContext if proactive chat should be triggered, None otherwise
        """
        if not self.should_trigger_proactive_chat():
            return None
        
        # Determine type of proactive interaction needed
        context = self._determine_proactive_type(long_term_memory, personality_profile)
        
        return context
    
    def _determine_proactive_type(
        self,
        memory: LongTermMemory,
        profile: PersonalityProfile
    ) -> ProactiveContext:
        """Determine the type of proactive interaction"""
        
        # If we have few interests, gather more information
        if len(profile.interests) < 3:
            return ProactiveContext(
                trigger_type="information_gathering",
                reason="Limited user interests recorded",
                suggested_prompt="I'd love to know more about your interests. What topics or hobbies are you passionate about?"
            )
        
        # If we have few preferences, gather preferences
        if len(profile.user_preferences) < 3:
            return ProactiveContext(
                trigger_type="information_gathering",
                reason="Limited user preferences recorded",
                suggested_prompt="To better assist you, could you tell me about your preferences? For example, do you prefer detailed explanations or brief summaries?"
            )
        
        # If we should update personality, trigger that
        if self.should_update_personality():
            return ProactiveContext(
                trigger_type="personality_update",
                reason="Scheduled personality update based on interaction threshold",
                suggested_prompt=None
            )
        
        # Follow up on previous topics
        if memory.summaries:
            return ProactiveContext(
                trigger_type="follow_up",
                reason="Following up on previous conversation",
                suggested_prompt="I wanted to follow up on our previous conversation. Is there anything else you'd like to know or discuss?"
            )
        
        # Default: general check-in
        return ProactiveContext(
            trigger_type="information_gathering",
            reason="General user engagement",
            suggested_prompt="How can I help you today? I'm here to assist with any questions or tasks you might have."
        )
    
    def increment_interaction(self):
        """Increment the interaction counter"""
        self.interaction_count += 1
