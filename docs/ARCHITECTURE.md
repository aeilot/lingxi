# Architecture Documentation

## System Overview

The Proactive AI chatbot is built on a multi-agent architecture with three specialized agents working together to provide an intelligent, adaptive conversational experience.

## Agent Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    ProactiveRAGChatbot                          │
│                   (Main Orchestrator)                           │
└────────┬──────────────────┬──────────────────┬──────────────────┘
         │                  │                  │
         ▼                  ▼                  ▼
┌────────────────┐  ┌──────────────┐  ┌─────────────────┐
│ Conversation   │  │   Memory     │  │   Proactive     │
│    Agent       │  │   Agent      │  │    Agent        │
└────────────────┘  └──────────────┘  └─────────────────┘
```

## Component Details

### 1. Conversation Agent

**Purpose**: Generate contextually-aware responses using RAG (Retrieval-Augmented Generation)

**Key Components**:
- **Haystack Pipeline**: Orchestrates the RAG workflow
- **Document Store**: In-memory BM25-indexed knowledge base
- **Retriever**: Fetches relevant documents for context
- **Prompt Builder**: Constructs prompts with personality and context
- **LLM Generator**: OpenAI GPT for response generation

**Data Flow**:
```
User Query → Retriever → Documents → Prompt Builder → LLM → Response
                ↑                          ↑
           Knowledge Base        Personality Profile (P_params)
```

**Key Features**:
- Integrates personality profile into every response
- Retrieves relevant knowledge from document store
- Maintains conversation history context
- Supports dynamic personality updates

### 2. Memory Agent

**Purpose**: Manage conversation memory across short-term and long-term storage

**Memory Structure**:

```
┌─────────────────────────────────────────────────────────┐
│                    Memory Agent                         │
├─────────────────────┬───────────────────────────────────┤
│  Short-Term Memory  │     Long-Term Memory (M_long)     │
├─────────────────────┼───────────────────────────────────┤
│ Recent messages     │ • Conversation summaries          │
│ (Sliding window)    │ • Key facts extracted             │
│                     │ • User insights                   │
│ Max: 10 messages    │ • Topic tracking                  │
│                     │ • Conversation count              │
└─────────────────────┴───────────────────────────────────┘
```

**Key Features**:
- **Short-term memory**: Fixed-size sliding window of recent messages
- **Long-term memory**: Persistent storage of:
  - Conversation summaries
  - Key facts about user
  - User insights (preferences, interests, identity)
  - Extracted topics
- **Automatic summarization**: Triggered when message threshold reached
- **Information extraction**: Extracts facts and insights from conversations

**Summarization Process**:
1. Collect messages from short-term memory
2. Extract topics using keyword analysis
3. Identify key facts (user statements about themselves)
4. Extract user insights (preferences, interests)
5. Create conversation summary
6. Store in long-term memory

### 3. Proactive Agent

**Purpose**: Dynamically adapt personality and initiate proactive conversations

**Key Responsibilities**:

1. **Personality Profile Updates (P_params)**:
   - Monitors interaction count
   - Analyzes long-term memory (M_long)
   - Updates personality parameters based on user patterns
   - Adjusts communication style, interests, preferences

2. **Proactive Engagement**:
   - Triggers information-gathering conversations
   - Initiates follow-ups on previous topics
   - Prompts for user preferences
   - Engages users to collect more data

**Personality Profile (P_params)**:
```python
{
    "tone": str,                    # friendly, professional, etc.
    "formality": str,               # casual, formal
    "interests": List[str],         # User interests
    "communication_style": str,     # conversational, technical
    "expertise_areas": List[str],   # Areas to emphasize
    "user_preferences": Dict        # Specific preferences
}
```

**Update Triggers**:
- Interaction count threshold reached
- New user insights detected in M_long
- Significant change in conversation patterns

**Proactive Context Types**:
- `information_gathering`: Collect user data
- `personality_update`: Update P_params
- `follow_up`: Continue previous conversations

## Data Models

### Message
```python
{
    "role": str,            # "user" or "assistant"
    "content": str,         # Message content
    "timestamp": datetime   # When message was sent
}
```

### PersonalityProfile (P_params)
```python
{
    "tone": str,
    "formality": str,
    "interests": List[str],
    "communication_style": str,
    "expertise_areas": List[str],
    "user_preferences": Dict[str, str]
}
```

### ShortTermMemory
```python
{
    "messages": List[Message],
    "max_size": int
}
```

### LongTermMemory (M_long)
```python
{
    "summaries": List[str],
    "key_facts": List[str],
    "user_insights": Dict[str, str],
    "conversation_count": int
}
```

## System Flow

### Standard Conversation Flow

```
1. User sends message
   ↓
2. Memory Agent stores message in short-term memory
   ↓
3. Proactive Agent checks if personality update needed
   ↓
4. If needed, update P_params based on M_long
   ↓
5. Conversation Agent retrieves relevant documents
   ↓
6. Conversation Agent generates response with:
   - Retrieved knowledge
   - Personality context
   - Conversation history
   ↓
7. Memory Agent stores response
   ↓
8. Proactive Agent increments interaction count
   ↓
9. Proactive Agent generates proactive context (probabilistic)
   ↓
10. Return response + optional proactive prompt
```

### Memory Summarization Flow

```
1. Message count reaches threshold (e.g., 50 messages)
   ↓
2. Memory Agent collects short-term messages
   ↓
3. Extract topics, facts, and insights
   ↓
4. Create conversation summary
   ↓
5. Store in Long-Term Memory (M_long)
   ↓
6. Reset message counter
```

### Personality Update Flow

```
1. Interaction count reaches threshold (e.g., 20 interactions)
   ↓
2. Proactive Agent retrieves M_long
   ↓
3. Analyze user insights for preferences
   ↓
4. Extract new interests from facts
   ↓
5. Adjust communication style based on patterns
   ↓
6. Update P_params
   ↓
7. Apply to Conversation Agent
```

## Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_short_term_messages` | 10 | Short-term memory size |
| `long_term_threshold` | 50 | Messages before summarization |
| `personality_update_threshold` | 20 | Interactions before P_params update |
| `proactive_trigger_probability` | 0.3 | Probability of proactive chat |
| `embedding_model` | all-MiniLM-L6-v2 | Sentence transformer model |
| `llm_model` | gpt-3.5-turbo | OpenAI model |

## Design Principles

1. **Modularity**: Each agent is independent and can be modified separately
2. **Adaptability**: System learns and adapts to user preferences over time
3. **Proactivity**: System takes initiative to gather information and engage
4. **Memory Hierarchy**: Two-tier memory system balances recency and persistence
5. **Personality-Driven**: All responses filtered through personality profile
6. **RAG-Enhanced**: Responses grounded in retrievable knowledge

## Extension Points

The architecture supports several extension points:

1. **Custom Memory Extractors**: Add domain-specific fact extraction
2. **Advanced Summarization**: Use LLM-based summarization instead of keyword-based
3. **Multiple Document Stores**: Support different knowledge bases per topic
4. **Personality Learning**: ML-based personality adaptation
5. **Proactive Strategies**: Custom proactive engagement strategies
6. **Multi-modal Support**: Extend to handle images, voice, etc.
