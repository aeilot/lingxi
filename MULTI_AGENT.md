# Multi-Agent Group Chat Feature

This document describes the multi-agent group chatting functionality in the Lingxi application.

## Overview

The app has been transformed from a single-agent chat to a multi-agent group chat, where users can interact with multiple AI agents, each with distinct personalities, styles, and visual identities.

## Features

### Multiple AI Agents

The application includes three default AI agents:

1. **Alice** (😊) - Friendly and enthusiastic
   - Color: Pink (#FF6B9D)
   - Personality: Warm, encouraging, uses emojis, explains things conversationally
   
2. **Bob** (🧠) - Professional and knowledgeable
   - Color: Blue (#4A90E2)
   - Personality: Formal, technical, detailed explanations, focuses on accuracy
   
3. **Charlie** (🎨) - Creative and playful
   - Color: Orange (#FFA500)
   - Personality: Innovative, uses metaphors and analogies, thinks outside the box

### How It Works

When a user sends a message:

1. The system randomly selects 1-2 active agents to respond
2. Each selected agent generates a response based on their unique personality
3. Responses are displayed with the agent's:
   - Name
   - Emoji avatar
   - Color-coded left border
4. All responses appear in the conversation thread, creating a group chat experience

### Visual Design

- **Agent Messages**: Each agent's message has a distinctive colored left border matching their theme color
- **Agent Header**: Shows the agent's emoji and name in their theme color
- **Message Layout**: Clean, modern design with rounded corners and subtle shadows

## Database Schema

### New Models

#### Agent Model
```python
class Agent(models.Model):
    name = CharField              # Agent's name (e.g., "Alice")
    personality_prompt = TextField  # Personality description
    avatar_emoji = CharField       # Emoji representation (e.g., "😊")
    color = CharField             # Theme color (e.g., "#FF6B9D")
    is_active = BooleanField      # Whether agent participates in chats
    created_at = DateTimeField
    updated_at = DateTimeField
```

### Updated Models

#### ChatInformation
- Added `agent` ForeignKey to track which agent sent the message

#### ChatSession
- Added `agents` ManyToManyField to track which agents are active in the session

## API Endpoints

### Agent Management

- `GET /api/agents/list` - List all active agents
- `GET /api/agents/<id>` - Get agent details
- `POST /api/agents/<id>/update` - Update agent properties
- `POST /api/sessions/<id>/agents` - Update agents for a session

### Message Handling

The existing `/handle_user_input` endpoint now returns multi-agent responses:

```json
{
  "session_id": 1,
  "user_message_id": 123,
  "messages": [
    {
      "id": 124,
      "message": "Hello! I'd be happy to help!",
      "agent_id": 1,
      "agent_name": "Alice",
      "agent_emoji": "😊",
      "agent_color": "#FF6B9D"
    },
    {
      "id": 125,
      "message": "Let me provide a detailed analysis...",
      "agent_id": 2,
      "agent_name": "Bob",
      "agent_emoji": "🧠",
      "agent_color": "#4A90E2"
    }
  ]
}
```

## Core Functions

### `generate_multi_agent_responses()`

Main function for generating multi-agent responses:

```python
def generate_multi_agent_responses(user_message, agent_config, session, 
                                   api_key=None, base_url=None, num_agents=None)
```

- Selects 1-2 random agents from the session's active agents
- Generates a response from each selected agent
- Returns list of `{agent, response}` dictionaries

### `generate_response()` with Agent Support

Updated to accept an optional `agent` parameter:

```python
def generate_response(user_message, agent_config, session, 
                     api_key=None, base_url=None, agent=None)
```

- Uses agent-specific personality prompt when provided
- Includes agent context in conversation history
- Maintains backward compatibility for single-agent mode

## Frontend Updates

### JavaScript (chat.js)

- `appendAgentMessage()`: New function to render agent messages with styling
- `loadSessionHistory()`: Updated to display agent information
- `sendMessage()`: Updated to handle multi-agent responses

### CSS (styles.css)

New classes:
- `.agent-message`: Base styling for agent messages
- `.agent-header`: Container for agent emoji and name
- `.agent-emoji`: Emoji display styling
- `.agent-name`: Agent name styling
- `.agent-message-text`: Message content styling

## Admin Interface

The Django admin interface includes:
- Agent management (create, edit, activate/deactivate)
- View which agent sent each message
- Configure session agents
- Monitor agent activity

## Configuration

### Creating Custom Agents

You can create new agents through:

1. **Django Admin**: Navigate to Agents → Add Agent
2. **API**: POST to `/api/agents/` (requires authentication)
3. **Database Migration**: Add agents in a data migration

### Agent Selection Algorithm

The current implementation randomly selects 1-2 agents to respond. This can be customized by modifying `generate_multi_agent_responses()` in `core.py`.

Future enhancements could include:
- User preference for specific agents
- Context-based agent selection
- Round-robin or weighted selection
- Allow user to specify which agents should respond

## Testing

Comprehensive test suite in `test_multi_agent.py`:
- Agent model creation
- Multi-agent response generation
- API endpoint functionality
- Session agent assignment
- Message rendering with agent info

Run tests:
```bash
cd app
python manage.py test agent.test_multi_agent
```

## Migration

The multi-agent feature was added through migrations:
- `0006_agent_chatinformation_agent_chatsession_agents.py` - Schema changes
- `0007_create_default_agents.py` - Creates Alice, Bob, and Charlie

## Backward Compatibility

The implementation maintains backward compatibility:
- Old messages without agent info display as "AI"
- API responses include both new multi-agent format and legacy fields
- Existing single-agent functionality still works

## Usage Example

```python
from agent.models import Agent, ChatSession
from agent.core import generate_multi_agent_responses

# Get active agents
alice = Agent.objects.get(name="Alice")
bob = Agent.objects.get(name="Bob")

# Create a session with specific agents
session = ChatSession.objects.create(agent_configuration=config)
session.agents.set([alice, bob])

# Generate responses
responses = generate_multi_agent_responses(
    "What's the best way to learn Python?",
    config,
    session,
    api_key=api_key
)

# Each response contains agent info and message
for resp in responses:
    agent = resp["agent"]
    message = resp["response"]
    print(f"{agent.name} ({agent.avatar_emoji}): {message}")
```

## Future Enhancements

Potential improvements:
1. User ability to @mention specific agents
2. Agent voting or consensus mechanisms
3. Agent roles (moderator, expert, devil's advocate)
4. Conversation branching with different agent groups
5. Agent memory and learning from interactions
6. Custom agent creation by users
7. Agent collaboration on complex tasks
8. Analytics on agent performance and user preferences
