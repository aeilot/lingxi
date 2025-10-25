# Proactive AI - Multi-Agent Haystack RAG Chatbot

A sophisticated multi-agent chatbot system built with Haystack, featuring Retrieval-Augmented Generation (RAG), dynamic personality adaptation, and proactive user engagement.

## Overview

This project implements a multi-agent architecture consisting of three specialized agents:

1. **Conversation Agent**: Uses a Haystack RAG Pipeline for generating responses, integrating factual knowledge from a document store with personality context
2. **Memory Agent**: Manages conversation memory with Short-Term and Long-Term Memory ($M_{long}$), summarizing conversations and extracting key insights
3. **Proactive Agent**: Dynamically updates the Conversation Agent's Personality Profile ($P_{params}$) based on user interactions and triggers proactive chats to collect user data

## Features

- **RAG-based Responses**: Leverages Haystack's retrieval-augmented generation for factually grounded responses
- **Dynamic Personality**: Personality profile adapts based on user interactions and preferences
- **Memory Management**: Sophisticated short-term and long-term memory system
- **Proactive Engagement**: System initiates conversations to gather user preferences and provide better service
- **Configurable Parameters**: Extensive configuration options for all agents

## Architecture

### Conversation Agent
- Implements Haystack RAG pipeline with BM25 retrieval
- Integrates personality context into prompts
- Uses OpenAI GPT models for response generation
- Supports custom knowledge base additions

### Memory Agent
- **Short-Term Memory**: Maintains recent conversation history (configurable size)
- **Long-Term Memory ($M_{long}$)**: Stores conversation summaries, key facts, and user insights
- Automatic summarization when threshold is reached
- Extracts topics, preferences, and interests from conversations

### Proactive Agent
- **Personality Updates**: Dynamically modifies $P_{params}$ based on $M_{long}$
- **Proactive Triggers**: Probabilistic triggering of engagement prompts
- **Information Gathering**: Initiates conversations to learn more about users
- **Adaptive Communication**: Adjusts tone, formality, and style based on user patterns

## Installation

1. Clone the repository:
```bash
git clone https://github.com/aeilot/proactive-ai.git
cd proactive-ai
```

2. Install dependencies:
```bash
pip install -e .
```

Or install from requirements:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:
```
OPENAI_API_KEY=your_openai_api_key_here
```

## Usage

### Basic Example

```python
from proactive_ai import ProactiveRAGChatbot

# Initialize the chatbot
chatbot = ProactiveRAGChatbot(
    api_key="your_openai_api_key",
    llm_model="gpt-3.5-turbo"
)

# Add knowledge to the RAG system
knowledge_base = [
    "Python is a high-level programming language.",
    "Machine learning is a subset of AI.",
]
chatbot.add_knowledge(knowledge_base)

# Chat with the bot
result = chatbot.chat("What is Python?")
print(result["response"])

# Check for proactive messages
if result["proactive_context"]:
    print(result["proactive_context"].suggested_prompt)
```

### Interactive Demo

Run the included interactive demo:

```bash
python examples/demo.py
```

The demo provides commands to:
- Chat with the bot
- View memory summaries (`memory`)
- Check personality profile (`personality`)
- Get proactive messages (`proactive`)
- Exit (`quit`)

### Configuration

Configure the chatbot through environment variables or constructor parameters:

```python
chatbot = ProactiveRAGChatbot(
    api_key="your_key",
    embedding_model="sentence-transformers/all-MiniLM-L6-v2",
    llm_model="gpt-3.5-turbo",
    max_short_term_messages=10,          # Short-term memory size
    long_term_threshold=50,               # Messages before summarization
    personality_update_threshold=20,      # Interactions before personality update
    proactive_trigger_probability=0.3     # Probability of proactive chat
)
```

## Components

### Personality Profile ($P_{params}$)

The personality profile includes:
- `tone`: Communication tone (friendly, professional, etc.)
- `formality`: Level of formality (casual, formal)
- `interests`: User interests identified from conversations
- `communication_style`: Style of communication (conversational, technical)
- `expertise_areas`: Areas of expertise to emphasize
- `user_preferences`: Specific user preferences (detail level, etc.)

### Memory System

**Short-Term Memory**:
- Stores recent conversation messages
- Fixed size with automatic pruning
- Used for immediate conversation context

**Long-Term Memory ($M_{long}$)**:
- Conversation summaries
- Key facts extracted from conversations
- User insights (preferences, interests, identity)
- Topic tracking
- Conversation count

### Proactive Contexts

The system can trigger different types of proactive interactions:
- `information_gathering`: Collect user data and preferences
- `personality_update`: Update personality based on interactions
- `follow_up`: Follow up on previous conversations

## Development

### Project Structure

```
proactive-ai/
├── src/
│   └── proactive_ai/
│       ├── __init__.py
│       ├── chatbot.py              # Main orchestration
│       ├── agents/
│       │   ├── __init__.py
│       │   ├── conversation_agent.py
│       │   ├── memory_agent.py
│       │   └── proactive_agent.py
│       ├── models/
│       │   └── __init__.py         # Data models
│       └── utils/
│           └── __init__.py         # Utilities
├── examples/
│   └── demo.py                     # Interactive demo
├── requirements.txt
├── setup.py
├── .env.example
└── README.md
```

### Testing

To test the implementation, ensure you have an OpenAI API key set and run:

```bash
python examples/demo.py
```

## Requirements

- Python >= 3.8
- haystack-ai >= 2.0.0
- sentence-transformers >= 2.2.0
- transformers >= 4.30.0
- openai >= 1.0.0
- pydantic >= 2.0.0
- python-dotenv >= 1.0.0

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgments

- Built with [Haystack](https://haystack.deepset.ai/)
- Uses OpenAI GPT models for language generation
- Inspired by research in conversational AI and proactive agents