"""
Demonstration of the Multi-Agent System with Transparent Output
This shows the three-part response format: Factual#Personality#Proactive
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from proactive_ai.models import PersonalityProfile, LongTermMemory
from proactive_ai.agents import MemoryAgent, ProactiveAgent


def demonstrate_transparent_output():
    """Demonstrate the transparent three-part output format"""
    print("="*70)
    print(" MULTI-AGENT CONVERSATIONAL AI DEMONSTRATION")
    print(" Transparent Output: Factual # Personality # Proactive")
    print("="*70)
    
    # Initialize agents
    print("\n1. Initializing Memory & Summarization Agent")
    print(f"   - Summarization interval: Every 5 turns")
    memory_agent = MemoryAgent(
        max_short_term_messages=10,
        summarization_interval=5
    )
    
    print("\n2. Initializing Proactive & Personality Agent")
    print(f"   - Proactive trigger interval: Every 10 turns (deterministic)")
    print(f"   - Personality update: Every 20 interactions")
    proactive_agent = ProactiveAgent(
        personality_update_threshold=20,
        proactive_trigger_interval=10
    )
    
    # Simulate a conversation with personality evolution
    print("\n" + "="*70)
    print(" CONVERSATION SIMULATION")
    print("="*70)
    
    conversation = [
        ("user", "Hi, my name is Alice and I love programming in Python"),
        ("assistant", "Nice to meet you Alice! Python is a great language."),
        ("user", "I'm particularly interested in machine learning and AI"),
        ("assistant", "Fascinating! ML and AI are exciting fields."),
        ("user", "I prefer detailed technical explanations"),
        ("assistant", "Noted! I'll provide comprehensive technical details."),
        ("user", "Can you tell me about neural networks?"),
        ("assistant", "Neural networks are computational models inspired by biological neural networks..."),
        ("user", "How do backpropagation work?"),
        ("assistant", "Backpropagation is a supervised learning algorithm that trains neural networks by calculating gradients..."),
        ("user", "What about deep learning frameworks?"),
        ("assistant", "Popular deep learning frameworks include TensorFlow, PyTorch, and JAX..."),
    ]
    
    # Process conversation and show memory updates
    for i, (role, content) in enumerate(conversation, 1):
        print(f"\nTurn {i//2 + 1}: {role}")
        print(f"  Message: {content[:60]}...")
        
        memory_agent.add_message(role, content)
        
        if role == "assistant":
            proactive_agent.increment_interaction()
            turn_num = i // 2
            
            # Show memory summarization
            if turn_num % 5 == 0:
                print(f"  [Memory Agent] Triggered summarization at turn {turn_num}")
                print(f"  [M_long] Summaries: {len(memory_agent.long_term_memory.summaries)}")
            
            # Show proactive trigger
            if proactive_agent.should_trigger_proactive_chat():
                print(f"  [Proactive Agent] Triggered at turn {turn_num}")
    
    # Show M_long state
    print("\n" + "="*70)
    print(" LONG-TERM MEMORY (M_long) STATE")
    print("="*70)
    long_term = memory_agent.get_long_term_memory()
    print(f"Conversation summaries: {len(long_term.summaries)}")
    print(f"Key facts extracted: {long_term.key_facts[:3] if long_term.key_facts else 'None yet'}")
    print(f"User insights: {long_term.user_insights}")
    
    # Show personality evolution
    print("\n" + "="*70)
    print(" PERSONALITY PROFILE (P_params) EVOLUTION")
    print("="*70)
    
    # Initial personality
    initial_profile = PersonalityProfile()
    print("\nInitial Personality:")
    print(f"  Tone: {initial_profile.tone}")
    print(f"  Formality: {initial_profile.formality}")
    print(f"  Interests: {initial_profile.interests}")
    print(f"  Communication style: {initial_profile.communication_style}")
    
    # Updated personality based on M_long
    updated_profile = proactive_agent.update_personality_profile(
        initial_profile,
        long_term
    )
    
    print("\nUpdated Personality (after analyzing M_long):")
    print(f"  Tone: {updated_profile.tone}")
    print(f"  Formality: {updated_profile.formality}")
    print(f"  Interests: {updated_profile.interests}")
    print(f"  Communication style: {updated_profile.communication_style}")
    print(f"  User preferences: {updated_profile.user_preferences}")
    print(f"  Expertise areas: {updated_profile.expertise_areas}")
    
    # Show transparent output format
    print("\n" + "="*70)
    print(" TRANSPARENT OUTPUT FORMAT EXAMPLE")
    print("="*70)
    
    # Simulate the three-part response
    factual_part = """Retrieved from Knowledge Base ($KB_{RAG}$):
- Python is a high-level programming language known for readability
- Neural networks are computational models inspired by biological neurons
- Backpropagation is the primary algorithm for training neural networks"""
    
    personality_part = updated_profile.to_prompt()
    
    proactive_context = proactive_agent.generate_proactive_context(
        long_term,
        updated_profile
    )
    proactive_part = proactive_context.suggested_prompt if proactive_context else "No proactive engagement at this turn."
    
    print("\n[Part 1: Factual Context from KB_RAG]")
    print(factual_part)
    
    print("\n[Part 2: Personality Context from P_params]")
    print(personality_part)
    
    print("\n[Part 3: Proactive Engagement]")
    print(proactive_part)
    
    print("\n" + "="*70)
    print(" KEY FEATURES DEMONSTRATED")
    print("="*70)
    print("✓ Memory Agent: Automatic summarization every 5 turns → M_long")
    print("✓ Personality Agent: Dynamic P_params updates based on M_long")
    print("✓ Proactive Agent: Deterministic triggers every 10 turns")
    print("✓ Transparent Output: Three distinct parts (Factual#Personality#Proactive)")
    print("✓ Personality Evolution: System adapts based on user interactions")
    print("="*70 + "\n")


if __name__ == "__main__":
    demonstrate_transparent_output()
