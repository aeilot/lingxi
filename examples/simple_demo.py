"""
Simple demo showing the chatbot structure without requiring API key
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from proactive_ai.models import PersonalityProfile, Message
from proactive_ai.agents import MemoryAgent, ProactiveAgent


def demo_memory_system():
    """Demonstrate the memory system"""
    print("="*60)
    print("MEMORY SYSTEM DEMONSTRATION")
    print("="*60)
    
    memory_agent = MemoryAgent(max_short_term_messages=5, long_term_threshold=10)
    
    # Simulate a conversation
    conversation = [
        ("user", "Hi, my name is Alice and I like programming"),
        ("assistant", "Nice to meet you Alice! Programming is great."),
        ("user", "I'm particularly interested in AI and machine learning"),
        ("assistant", "Those are fascinating fields! What aspects interest you most?"),
        ("user", "I prefer detailed explanations when learning new concepts"),
        ("assistant", "I'll make sure to provide comprehensive explanations."),
    ]
    
    print("\nAdding messages to memory...")
    for role, content in conversation:
        memory_agent.add_message(role, content)
        print(f"  {role}: {content[:50]}...")
    
    # Show short-term memory
    print("\n--- Short-Term Memory ---")
    short_term = memory_agent.get_short_term_memory()
    print(f"Messages stored: {len(short_term.messages)}")
    for msg in short_term.messages[-3:]:
        print(f"  {msg.role}: {msg.content[:50]}...")
    
    # Add more messages to trigger long-term summarization
    print("\nAdding more messages to trigger long-term summarization...")
    for i in range(5):
        memory_agent.add_message("user", f"Additional message {i}")
        memory_agent.add_message("assistant", f"Response to message {i}")
    
    # Show long-term memory
    print("\n--- Long-Term Memory (M_long) ---")
    long_term = memory_agent.get_long_term_memory()
    print(f"Summaries: {len(long_term.summaries)}")
    if long_term.summaries:
        print(f"  Latest summary: {long_term.summaries[-1]}")
    print(f"Key facts: {long_term.key_facts}")
    print(f"User insights: {long_term.user_insights}")
    

def demo_personality_profile():
    """Demonstrate personality profile updates"""
    print("\n" + "="*60)
    print("PERSONALITY PROFILE DEMONSTRATION")
    print("="*60)
    
    # Initial profile
    profile = PersonalityProfile(
        tone="friendly",
        formality="casual",
        interests=["general"],
        communication_style="conversational"
    )
    
    print("\n--- Initial Personality Profile (P_params) ---")
    print(f"Tone: {profile.tone}")
    print(f"Formality: {profile.formality}")
    print(f"Interests: {profile.interests}")
    print(f"Communication style: {profile.communication_style}")
    print(f"Expertise areas: {profile.expertise_areas}")
    
    # Create proactive agent
    proactive_agent = ProactiveAgent(
        personality_update_threshold=5,
        proactive_trigger_probability=0.5
    )
    
    # Simulate interactions
    print("\nSimulating 10 interactions...")
    for i in range(10):
        proactive_agent.increment_interaction()
    
    # Create mock long-term memory with insights
    from proactive_ai.models import LongTermMemory
    memory = LongTermMemory()
    memory.add_user_insight("interests", "I am interested in programming and AI")
    memory.add_user_insight("preferences", "I prefer detailed technical explanations")
    memory.add_key_fact("User is a Python developer")
    memory.add_key_fact("User likes machine learning")
    
    # Update personality
    print("\nUpdating personality based on user interactions...")
    updated_profile = proactive_agent.update_personality_profile(profile, memory)
    
    print("\n--- Updated Personality Profile (P_params) ---")
    print(f"Tone: {updated_profile.tone}")
    print(f"Formality: {updated_profile.formality}")
    print(f"Interests: {updated_profile.interests}")
    print(f"Communication style: {updated_profile.communication_style}")
    print(f"Expertise areas: {updated_profile.expertise_areas}")
    print(f"User preferences: {updated_profile.user_preferences}")


def demo_proactive_agent():
    """Demonstrate proactive agent functionality"""
    print("\n" + "="*60)
    print("PROACTIVE AGENT DEMONSTRATION")
    print("="*60)
    
    proactive_agent = ProactiveAgent(
        personality_update_threshold=5,
        proactive_trigger_probability=1.0  # Always trigger for demo
    )
    
    # Create a personality profile and memory
    profile = PersonalityProfile(interests=["tech"])
    from proactive_ai.models import LongTermMemory
    memory = LongTermMemory()
    memory.add_summary("User discussed Python and AI")
    
    # Generate proactive context
    print("\nGenerating proactive engagement context...")
    context = proactive_agent.generate_proactive_context(memory, profile)
    
    if context:
        print(f"\n--- Proactive Context ---")
        print(f"Trigger type: {context.trigger_type}")
        print(f"Reason: {context.reason}")
        if context.suggested_prompt:
            print(f"Suggested prompt: {context.suggested_prompt}")
    
    # Show multiple proactive contexts
    print("\n--- Different Proactive Scenarios ---")
    
    # Scenario 1: Few interests
    profile1 = PersonalityProfile(interests=[])
    context1 = proactive_agent._determine_proactive_type(memory, profile1)
    print(f"\n1. Limited interests scenario:")
    print(f"   Type: {context1.trigger_type}")
    print(f"   Prompt: {context1.suggested_prompt}")
    
    # Scenario 2: Few preferences
    profile2 = PersonalityProfile(interests=["tech", "ai", "ml"], user_preferences={})
    context2 = proactive_agent._determine_proactive_type(memory, profile2)
    print(f"\n2. Limited preferences scenario:")
    print(f"   Type: {context2.trigger_type}")
    print(f"   Prompt: {context2.suggested_prompt}")


def main():
    """Run all demonstrations"""
    print("\n" + "="*70)
    print(" PROACTIVE AI - MULTI-AGENT HAYSTACK RAG CHATBOT DEMO")
    print("="*70)
    
    demo_memory_system()
    demo_personality_profile()
    demo_proactive_agent()
    
    print("\n" + "="*70)
    print(" DEMONSTRATION COMPLETE")
    print("="*70)
    print("\nThis demo showed the three main agents:")
    print("  1. Memory Agent - Short-term and Long-term memory (M_long)")
    print("  2. Proactive Agent - Personality updates (P_params)")
    print("  3. (Conversation Agent requires OpenAI API key)")
    print("\nTo use the full chatbot with RAG, see examples/demo.py")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
