# API Documentation

## ProactiveRAGChatbot

Main chatbot class that orchestrates all three agents.

### Constructor

```python
ProactiveRAGChatbot(
    api_key: str,
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    llm_model: str = "gpt-3.5-turbo",
    max_short_term_messages: int = 10,
    long_term_threshold: int = 50,
    personality_update_threshold: int = 20,
    proactive_trigger_probability: float = 0.3
)
```

**Parameters**:
- `api_key`: OpenAI API key (required)
- `embedding_model`: Model for document embeddings
- `llm_model`: OpenAI model name for generation
- `max_short_term_messages`: Maximum messages in short-term memory
- `long_term_threshold`: Message count before summarizing to long-term
- `personality_update_threshold`: Interactions before personality update
- `proactive_trigger_probability`: Probability (0-1) of proactive engagement

### Methods

#### chat(user_message: str) -> Dict[str, Any]

Process a user message and generate a response.

**Parameters**:
- `user_message`: User's input message

**Returns**:
```python
{
    "response": str,                    # Assistant's response
    "proactive_context": ProactiveContext,  # Optional proactive context
    "personality_updated": bool,        # Whether personality was updated
    "interaction_count": int           # Total interactions
}
```

**Example**:
```python
result = chatbot.chat("What is Python?")
print(result["response"])
```

#### add_knowledge(documents: List[str])

Add documents to the RAG knowledge base.

**Parameters**:
- `documents`: List of document strings to add

**Example**:
```python
chatbot.add_knowledge([
    "Python is a programming language.",
    "AI involves creating intelligent machines."
])
```

#### get_proactive_message() -> Optional[str]

Get a proactive message if one should be triggered.

**Returns**: Proactive message string or None

**Example**:
```python
message = chatbot.get_proactive_message()
if message:
    print(f"Proactive: {message}")
```

#### get_personality_profile() -> PersonalityProfile

Get the current personality profile.

**Returns**: PersonalityProfile object

**Example**:
```python
profile = chatbot.get_personality_profile()
print(f"Tone: {profile.tone}")
```

#### get_memory_summary() -> Dict[str, Any]

Get a summary of the memory state.

**Returns**:
```python
{
    "short_term_messages": int,
    "long_term_summaries": int,
    "key_facts": List[str],
    "user_insights": Dict[str, str],
    "conversation_count": int
}
```

#### force_personality_update()

Force an immediate personality profile update.

---

## ConversationAgent

Agent responsible for generating responses using Haystack RAG.

### Constructor

```python
ConversationAgent(
    api_key: str,
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    llm_model: str = "gpt-3.5-turbo"
)
```

### Methods

#### add_knowledge(documents: List[str])

Add documents to the knowledge base.

#### update_personality(personality_profile: PersonalityProfile)

Update the personality profile used for responses.

#### generate_response(query: str, history: List[Message], max_history: int = 5) -> str

Generate a response using the RAG pipeline.

#### chat(query: str, history: List[Message]) -> str

Simplified chat interface.

---

## MemoryAgent

Agent responsible for managing conversation memory.

### Constructor

```python
MemoryAgent(
    max_short_term_messages: int = 10,
    long_term_threshold: int = 50
)
```

### Methods

#### add_message(role: str, content: str)

Add a message to short-term memory.

**Parameters**:
- `role`: "user" or "assistant"
- `content`: Message content

#### get_short_term_memory() -> ShortTermMemory

Get short-term memory object.

#### get_long_term_memory() -> LongTermMemory

Get long-term memory (M_long) object.

#### get_context_for_conversation() -> str

Get memory context as a string for conversation.

#### force_summarize()

Force immediate summarization to long-term memory.

---

## ProactiveAgent

Agent responsible for personality updates and proactive engagement.

### Constructor

```python
ProactiveAgent(
    personality_update_threshold: int = 20,
    proactive_trigger_probability: float = 0.3
)
```

### Methods

#### should_update_personality() -> bool

Check if personality should be updated.

#### update_personality_profile(current_profile: PersonalityProfile, long_term_memory: LongTermMemory) -> PersonalityProfile

Update personality based on long-term memory.

**Returns**: Updated PersonalityProfile

#### should_trigger_proactive_chat() -> bool

Determine if proactive chat should be triggered.

#### generate_proactive_context(long_term_memory: LongTermMemory, personality_profile: PersonalityProfile) -> Optional[ProactiveContext]

Generate context for proactive interaction.

#### increment_interaction()

Increment the interaction counter.

---

## Data Models

### PersonalityProfile

Personality profile parameters (P_params).

**Fields**:
```python
tone: str = "friendly"
formality: str = "casual"
interests: List[str] = []
communication_style: str = "conversational"
expertise_areas: List[str] = []
user_preferences: Dict[str, str] = {}
```

**Methods**:
- `to_prompt() -> str`: Convert to prompt string

### Message

Individual conversation message.

**Fields**:
```python
role: str                    # "user" or "assistant"
content: str                 # Message content
timestamp: datetime          # When message was created
```

### ShortTermMemory

Short-term message storage.

**Fields**:
```python
messages: List[Message]
max_size: int
```

**Methods**:
- `add_message(role: str, content: str)`
- `get_recent_messages(n: Optional[int]) -> List[Message]`
- `clear()`

### LongTermMemory

Long-term memory storage (M_long).

**Fields**:
```python
summaries: List[str]
key_facts: List[str]
user_insights: Dict[str, str]
conversation_count: int
```

**Methods**:
- `add_summary(summary: str)`
- `add_key_fact(fact: str)`
- `add_user_insight(key: str, value: str)`
- `get_context() -> str`

### ProactiveContext

Context for proactive interactions.

**Fields**:
```python
trigger_type: str            # "personality_update", "information_gathering", "follow_up"
reason: str                  # Why this was triggered
suggested_prompt: Optional[str]  # Suggested prompt to user
```

---

## Utility Functions

### load_config() -> dict

Load configuration from environment variables.

**Returns**: Configuration dictionary

### validate_config(config: dict) -> bool

Validate configuration.

**Returns**: True if valid, False otherwise

---

## Usage Examples

### Basic Usage

```python
from proactive_ai import ProactiveRAGChatbot

chatbot = ProactiveRAGChatbot(api_key="your_key")
chatbot.add_knowledge(["Python is a programming language."])

result = chatbot.chat("What is Python?")
print(result["response"])
```

### With Configuration

```python
from proactive_ai import ProactiveRAGChatbot
from proactive_ai.utils import load_config, validate_config

config = load_config()
if validate_config(config):
    chatbot = ProactiveRAGChatbot(**config)
```

### Accessing Components

```python
# Get memory summary
summary = chatbot.get_memory_summary()
print(f"Conversations: {summary['conversation_count']}")

# Get personality
profile = chatbot.get_personality_profile()
print(f"Interests: {profile.interests}")

# Force updates
chatbot.force_personality_update()
```

### Using Individual Agents

```python
from proactive_ai.agents import ConversationAgent, MemoryAgent, ProactiveAgent
from proactive_ai.models import PersonalityProfile, LongTermMemory

# Create agents separately
conv_agent = ConversationAgent(api_key="your_key")
mem_agent = MemoryAgent()
pro_agent = ProactiveAgent()

# Use them independently
mem_agent.add_message("user", "Hello")
profile = PersonalityProfile(tone="professional")
conv_agent.update_personality(profile)
```
