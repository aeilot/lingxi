"""
Basic tests for the Proactive AI chatbot (without requiring API key)
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from proactive_ai.models import (
    Message, PersonalityProfile, ShortTermMemory, 
    LongTermMemory, ProactiveContext
)
from proactive_ai.agents import MemoryAgent, ProactiveAgent


def test_personality_profile():
    """Test PersonalityProfile model"""
    print("Testing PersonalityProfile...")
    profile = PersonalityProfile(
        tone="friendly",
        formality="casual",
        interests=["programming", "ai"],
        communication_style="conversational"
    )
    
    prompt = profile.to_prompt()
    assert "friendly" in prompt
    assert "casual" in prompt
    assert "programming" in prompt
    print("✓ PersonalityProfile works correctly")


def test_short_term_memory():
    """Test ShortTermMemory"""
    print("\nTesting ShortTermMemory...")
    memory = ShortTermMemory(max_size=3)
    
    memory.add_message("user", "Hello")
    memory.add_message("assistant", "Hi there!")
    memory.add_message("user", "How are you?")
    memory.add_message("assistant", "I'm good, thanks!")
    
    # Should only keep last 3 messages
    assert len(memory.messages) == 3
    assert memory.messages[0].content == "Hi there!"
    print("✓ ShortTermMemory works correctly")


def test_long_term_memory():
    """Test LongTermMemory"""
    print("\nTesting LongTermMemory...")
    memory = LongTermMemory()
    
    memory.add_summary("User discussed Python programming")
    memory.add_key_fact("User is a Python developer")
    memory.add_user_insight("interests", "programming, AI")
    
    assert len(memory.summaries) == 1
    assert len(memory.key_facts) == 1
    assert "interests" in memory.user_insights
    
    context = memory.get_context()
    assert "Python developer" in context
    print("✓ LongTermMemory works correctly")


def test_memory_agent():
    """Test MemoryAgent"""
    print("\nTesting MemoryAgent...")
    agent = MemoryAgent(max_short_term_messages=5, long_term_threshold=10)
    
    # Add some messages
    for i in range(15):
        agent.add_message("user", f"Message {i}")
        agent.add_message("assistant", f"Response {i}")
    
    # Should have triggered long-term summarization
    assert len(agent.long_term_memory.summaries) > 0
    print("✓ MemoryAgent works correctly")


def test_proactive_agent():
    """Test ProactiveAgent"""
    print("\nTesting ProactiveAgent...")
    agent = ProactiveAgent(
        personality_update_threshold=5,
        proactive_trigger_probability=1.0  # Always trigger for testing
    )
    
    # Test interaction counting
    for i in range(10):
        agent.increment_interaction()
    
    assert agent.interaction_count == 10
    assert agent.should_update_personality()
    
    # Test personality update
    profile = PersonalityProfile()
    memory = LongTermMemory()
    memory.add_user_insight("interests", "I am interested in programming and AI")
    
    updated_profile = agent.update_personality_profile(profile, memory)
    assert updated_profile is not None
    
    # Test proactive context generation
    context = agent.generate_proactive_context(memory, profile)
    assert context is not None
    assert context.suggested_prompt is not None
    print("✓ ProactiveAgent works correctly")


def test_message_model():
    """Test Message model"""
    print("\nTesting Message model...")
    msg = Message(role="user", content="Hello, world!")
    assert msg.role == "user"
    assert msg.content == "Hello, world!"
    assert msg.timestamp is not None
    print("✓ Message model works correctly")


def test_proactive_context():
    """Test ProactiveContext model"""
    print("\nTesting ProactiveContext...")
    context = ProactiveContext(
        trigger_type="information_gathering",
        reason="Need more user data",
        suggested_prompt="Tell me about yourself"
    )
    assert context.trigger_type == "information_gathering"
    assert context.suggested_prompt == "Tell me about yourself"
    print("✓ ProactiveContext works correctly")


def main():
    """Run all tests"""
    print("="*60)
    print("Running Basic Functionality Tests")
    print("="*60)
    
    try:
        test_message_model()
        test_personality_profile()
        test_short_term_memory()
        test_long_term_memory()
        test_memory_agent()
        test_proactive_agent()
        test_proactive_context()
        
        print("\n" + "="*60)
        print("✓ All tests passed!")
        print("="*60)
        return 0
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
