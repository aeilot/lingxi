# Quick Start Guide

## Installation

1. **Clone the repository**:
```bash
git clone https://github.com/aeilot/proactive-ai.git
cd proactive-ai
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

Or install in development mode:
```bash
pip install -e .
```

3. **Set up environment**:
```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:
```
OPENAI_API_KEY=sk-your-actual-key-here
```

## Running the Demo (No API Key Required)

To see the multi-agent system in action without requiring an API key:

```bash
python examples/simple_demo.py
```

This demonstrates:
- Memory Agent functionality (short-term and long-term memory)
- Proactive Agent personality updates
- Proactive engagement triggers

## Running the Full Interactive Demo

To use the complete RAG chatbot with OpenAI:

```bash
python examples/demo.py
```

Available commands:
- Type normally to chat
- `memory` - View memory summary
- `personality` - View personality profile
- `proactive` - Get proactive message
- `quit` - Exit

## Basic Usage in Code

### Simple Example

```python
from proactive_ai import ProactiveRAGChatbot

# Initialize (requires OpenAI API key)
chatbot = ProactiveRAGChatbot(
    api_key="your_openai_api_key"
)

# Add knowledge to the system
chatbot.add_knowledge([
    "Python is a high-level programming language.",
    "Machine learning is a subset of AI."
])

# Chat
result = chatbot.chat("What is Python?")
print(result["response"])
```

### Using Environment Variables

```python
from proactive_ai import ProactiveRAGChatbot
from proactive_ai.utils import load_config, validate_config

# Load from .env file
config = load_config()

if validate_config(config):
    chatbot = ProactiveRAGChatbot(
        api_key=config["api_key"],
        llm_model=config["llm_model"]
    )
else:
    print("Please set OPENAI_API_KEY in .env")
```

## Running Tests

Run the basic functionality tests:

```bash
python tests/test_basic.py
```

Expected output:
```
============================================================
Running Basic Functionality Tests
============================================================
Testing Message model...
✓ Message model works correctly
...
✓ All tests passed!
============================================================
```

## Understanding the Architecture

The system consists of three agents:

1. **Conversation Agent**: Generates responses using Haystack RAG
   - Uses OpenAI GPT for generation
   - Retrieves relevant knowledge from document store
   - Applies personality context to responses

2. **Memory Agent**: Manages conversation memory
   - Short-term: Recent messages (default: 10 messages)
   - Long-term: Summaries, facts, insights (M_long)
   - Automatic summarization when threshold reached

3. **Proactive Agent**: Adapts and engages proactively
   - Updates personality profile (P_params) based on M_long
   - Triggers proactive conversations probabilistically
   - Gathers user preferences and interests

## Key Concepts

### Personality Profile (P_params)

The system adapts its personality based on user interactions:
- **Tone**: friendly, professional, etc.
- **Formality**: casual, formal
- **Interests**: Topics user cares about
- **Communication style**: conversational, technical
- **User preferences**: detail level, etc.

### Long-Term Memory (M_long)

Persistent memory that stores:
- Conversation summaries
- Key facts about the user
- User insights (preferences, interests, identity)
- Topic tracking

### Proactive Contexts

The system can initiate conversations for:
- Information gathering
- Personality updates
- Follow-ups on previous topics

## Configuration

Customize behavior through environment variables in `.env`:

```bash
# Model Configuration
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
LLM_MODEL=gpt-3.5-turbo

# Memory Configuration
MAX_SHORT_TERM_MESSAGES=10        # Short-term memory size
LONG_TERM_MEMORY_THRESHOLD=50     # Messages before summarization

# Proactive Agent Configuration
PERSONALITY_UPDATE_THRESHOLD=20   # Interactions before update
PROACTIVE_TRIGGER_PROBABILITY=0.3 # 30% chance of proactive chat
```

## Next Steps

- Read the [Architecture Documentation](docs/ARCHITECTURE.md) for detailed design
- Check the [API Documentation](docs/API.md) for complete API reference
- Explore `examples/demo.py` for more usage examples
- Customize the agents for your specific use case

## Troubleshooting

### Import Errors

If you get import errors, ensure dependencies are installed:
```bash
pip install -r requirements.txt
```

### API Key Issues

If you get API key errors:
1. Check that `.env` exists and contains `OPENAI_API_KEY`
2. Verify the API key is valid
3. Ensure you have credits in your OpenAI account

### Module Not Found

If Python can't find the module:
```bash
# Install in development mode
pip install -e .

# Or add to Python path
export PYTHONPATH="${PYTHONPATH}:/path/to/proactive-ai/src"
```

## Getting Help

- Check the [README](README.md) for overview
- Read the [Architecture docs](docs/ARCHITECTURE.md) for design details
- Review the [API docs](docs/API.md) for usage examples
- Open an issue on GitHub for bugs or questions
