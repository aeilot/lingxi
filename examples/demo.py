"""
Example usage of the Proactive RAG Chatbot
"""

import os
from proactive_ai import ProactiveRAGChatbot
from proactive_ai.utils import load_config, validate_config


def main():
    """Main example function"""
    
    # Load configuration
    config = load_config()
    
    if not validate_config(config):
        print("Please set OPENAI_API_KEY in your .env file")
        return
    
    # Initialize the chatbot
    print("Initializing Proactive RAG Chatbot...")
    chatbot = ProactiveRAGChatbot(
        api_key=config["api_key"],
        embedding_model=config["embedding_model"],
        llm_model=config["llm_model"],
        max_short_term_messages=config["max_short_term_messages"],
        long_term_threshold=config["long_term_memory_threshold"],
        personality_update_threshold=config["personality_update_threshold"],
        proactive_trigger_probability=config["proactive_trigger_probability"]
    )
    
    # Add some knowledge to the RAG system
    print("\nAdding knowledge to the system...")
    knowledge_base = [
        "Python is a high-level programming language known for its simplicity and readability.",
        "Machine learning is a subset of artificial intelligence that enables systems to learn from data.",
        "Natural Language Processing (NLP) is a field of AI focused on interaction between computers and human language.",
        "Haystack is a framework for building NLP applications with a focus on question answering and semantic search.",
        "RAG (Retrieval-Augmented Generation) combines information retrieval with text generation for better responses."
    ]
    chatbot.add_knowledge(knowledge_base)
    
    # Interactive chat loop
    print("\n" + "="*60)
    print("Proactive RAG Chatbot - Interactive Demo")
    print("="*60)
    print("\nType 'quit' to exit")
    print("Type 'memory' to see memory summary")
    print("Type 'personality' to see current personality profile")
    print("Type 'proactive' to get a proactive message")
    print("\n" + "="*60 + "\n")
    
    while True:
        # Get user input
        user_input = input("You: ").strip()
        
        if not user_input:
            continue
        
        if user_input.lower() == 'quit':
            print("\nGoodbye!")
            break
        
        if user_input.lower() == 'memory':
            # Show memory summary
            summary = chatbot.get_memory_summary()
            print("\n--- Memory Summary ---")
            print(f"Short-term messages: {summary['short_term_messages']}")
            print(f"Long-term summaries: {summary['long_term_summaries']}")
            print(f"Conversation count: {summary['conversation_count']}")
            print(f"Key facts: {summary['key_facts']}")
            print(f"User insights: {summary['user_insights']}")
            print("----------------------\n")
            continue
        
        if user_input.lower() == 'personality':
            # Show personality profile
            profile = chatbot.get_personality_profile()
            print("\n--- Personality Profile ---")
            print(f"Tone: {profile.tone}")
            print(f"Formality: {profile.formality}")
            print(f"Communication style: {profile.communication_style}")
            print(f"Interests: {profile.interests}")
            print(f"Expertise areas: {profile.expertise_areas}")
            print(f"User preferences: {profile.user_preferences}")
            print("---------------------------\n")
            continue
        
        if user_input.lower() == 'proactive':
            # Get proactive message
            proactive_msg = chatbot.get_proactive_message()
            if proactive_msg:
                print(f"\nProactive: {proactive_msg}\n")
            else:
                print("\nNo proactive message triggered at this time.\n")
            continue
        
        # Process user message
        result = chatbot.chat(user_input)
        
        # Display response
        print(f"\nAssistant: {result['response']}\n")
        
        # Show proactive context if available
        if result['proactive_context'] and result['proactive_context'].suggested_prompt:
            print(f"[Proactive prompt available: {result['proactive_context'].suggested_prompt}]")
            print(f"[Reason: {result['proactive_context'].reason}]\n")


if __name__ == "__main__":
    main()
