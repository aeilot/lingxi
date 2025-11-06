# Lingxi Backend API Documentation

## Overview

Lingxi provides a comprehensive backend API for building AI-powered chat applications. The API supports:
- User authentication with JWT tokens
- Multi-user and multi-agent management
- Chat sessions with conversation history
- AI-powered responses with personality customization
- Automatic personality updates based on conversation patterns

## Base URL

```
http://localhost:8000/api/
```

## Authentication

The API uses JWT (JSON Web Tokens) for authentication. Most endpoints require authentication.

### Login

Get access and refresh tokens.

**Endpoint:** `POST /api/auth/login/`

**Request Body:**
```json
{
  "username": "your_username",
  "password": "your_password"
}
```

**Response:**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

### Refresh Token

Get a new access token using a refresh token.

**Endpoint:** `POST /api/auth/refresh/`

**Request Body:**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response:**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

### Using JWT Tokens

Include the access token in the Authorization header for authenticated requests:

```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

## Agents

Agents are AI configurations with specific models and personality prompts.

### List Agents

Get all agents for the authenticated user.

**Endpoint:** `GET /api/agents/`

**Authentication:** Required

**Response:**
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "default",
      "parameters": {
        "model": "gpt-3.5-turbo",
        "personality_prompt": "You are a helpful assistant"
      },
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:30:00Z",
      "timings": null
    },
    {
      "id": 2,
      "name": "coding-assistant",
      "parameters": {
        "model": "gpt-4",
        "personality_prompt": "You are an expert programming assistant"
      },
      "created_at": "2024-01-16T11:00:00Z",
      "updated_at": "2024-01-16T11:00:00Z",
      "timings": null
    }
  ]
}
```

### Create Agent

Create a new agent configuration.

**Endpoint:** `POST /api/agents/`

**Authentication:** Required

**Request Body:**
```json
{
  "name": "my-agent",
  "parameters": {
    "model": "gpt-4",
    "personality_prompt": "You are a helpful coding assistant"
  },
  "timings": {
    "inactivity_check_minutes": 5
  }
}
```

**Response:**
```json
{
  "id": 3,
  "name": "my-agent",
  "parameters": {
    "model": "gpt-4",
    "personality_prompt": "You are a helpful coding assistant"
  },
  "created_at": "2024-01-17T09:15:00Z",
  "updated_at": "2024-01-17T09:15:00Z",
  "timings": {
    "inactivity_check_minutes": 5
  }
}
```

### Get Agent

Get details of a specific agent.

**Endpoint:** `GET /api/agents/{id}/`

**Authentication:** Required

**Response:**
```json
{
  "id": 1,
  "name": "default",
  "parameters": {
    "model": "gpt-3.5-turbo",
    "personality_prompt": "You are a helpful assistant"
  },
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "timings": null
}
```

### Update Agent

Update an agent configuration.

**Endpoint:** `PUT /api/agents/{id}/` or `PATCH /api/agents/{id}/`

**Authentication:** Required

**Request Body (PUT - full update):**
```json
{
  "name": "updated-agent",
  "parameters": {
    "model": "gpt-4",
    "personality_prompt": "Updated personality"
  }
}
```

**Request Body (PATCH - partial update):**
```json
{
  "parameters": {
    "personality_prompt": "Updated personality only"
  }
}
```

### Update Agent Personality

Update only the personality prompt of an agent.

**Endpoint:** `PUT /api/agents/{id}/personality/` or `PATCH /api/agents/{id}/personality/`

**Authentication:** Required

**Request Body:**
```json
{
  "personality_prompt": "You are a friendly and knowledgeable assistant"
}
```

**Response:**
```json
{
  "success": true,
  "personality_prompt": "You are a friendly and knowledgeable assistant"
}
```

### Delete Agent

Delete an agent configuration.

**Endpoint:** `DELETE /api/agents/{id}/`

**Authentication:** Required

**Response:** `204 No Content`

## Chat

### Send Message

Send a message to an AI agent and receive a response.

**Endpoint:** `POST /api/chat/`

**Authentication:** Required

**Request Body:**
```json
{
  "message": "Hello, how are you?",
  "session_id": 1,  // optional - continue existing session
  "agent_id": 2     // optional - use specific agent (defaults to user's default agent)
}
```

**Response (single message):**
```json
{
  "session_id": 1,
  "user_message_id": 10,
  "response": "Hello! I'm doing well, thank you for asking. How can I help you today?",
  "ai_message_id": 11
}
```

**Response (split messages - when AI breaks response into multiple parts):**
```json
{
  "session_id": 1,
  "user_message_id": 10,
  "response": "Hello! I'm doing well.",
  "ai_message_id": 11,
  "messages": [
    {
      "id": 11,
      "message": "Hello! I'm doing well."
    },
    {
      "id": 12,
      "message": "Thank you for asking."
    },
    {
      "id": 13,
      "message": "How can I help you today?"
    }
  ]
}
```

**Response (with summary update - every 10 messages):**
```json
{
  "session_id": 1,
  "user_message_id": 20,
  "response": "That's a great question!",
  "ai_message_id": 21,
  "summary_updated": true,
  "summary": "Discussion about Python programming concepts"
}
```

**Response (with personality update - every 20 messages):**
```json
{
  "session_id": 1,
  "user_message_id": 40,
  "response": "Let me explain that in detail.",
  "ai_message_id": 41,
  "personality_updated": true,
  "personality_prompt": "You are a detailed technical assistant who provides in-depth explanations"
}
```

**Response (with personality suggestion - when confidence is below threshold):**
```json
{
  "session_id": 1,
  "user_message_id": 40,
  "response": "Let me help with that.",
  "ai_message_id": 41,
  "personality_suggestion_available": true
}
```

### Get Chat History

Get chat history for the authenticated user.

**Endpoint:** `GET /api/chat/history/`

**Authentication:** Required

**Query Parameters:**
- `session_id` (optional): Filter by specific session
- `limit` (optional): Limit number of sessions returned (default: 100)

**Response:**
```json
{
  "sessions": [
    {
      "id": 1,
      "agent_configuration": 2,
      "agent_name": "coding-assistant",
      "started_at": "2024-01-15T10:00:00Z",
      "summary": "Discussion about Python functions and decorators",
      "message_count": 15,
      "last_activity_at": "2024-01-15T11:30:00Z",
      "current_state": null,
      "messages": [
        {
          "id": 1,
          "chat_date": "2024-01-15T10:00:00Z",
          "message": "How do I use decorators in Python?",
          "is_user": true,
          "is_agent": false,
          "is_agent_growth": false,
          "is_read": true,
          "metadata": null,
          "critical": false,
          "critical_type": null
        },
        {
          "id": 2,
          "chat_date": "2024-01-15T10:00:05Z",
          "message": "Decorators in Python are...",
          "is_user": false,
          "is_agent": true,
          "is_agent_growth": false,
          "is_read": true,
          "metadata": null,
          "critical": false,
          "critical_type": null
        }
      ]
    }
  ]
}
```

## Sessions

### List Sessions

Get all chat sessions for the authenticated user.

**Endpoint:** `GET /api/sessions/`

**Authentication:** Required

**Response:**
```json
{
  "count": 5,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "agent_configuration": 1,
      "agent_name": "default",
      "started_at": "2024-01-15T10:00:00Z",
      "summary": "General conversation about technology",
      "message_count": 25,
      "last_activity_at": "2024-01-15T12:00:00Z",
      "current_state": null,
      "messages": []  // Empty unless using retrieve endpoint
    }
  ]
}
```

### Create Session

Create a new chat session.

**Endpoint:** `POST /api/sessions/`

**Authentication:** Required

**Request Body:**
```json
{
  "agent_configuration": 1
}
```

**Response:**
```json
{
  "id": 6,
  "agent_configuration": 1,
  "agent_name": "default",
  "started_at": "2024-01-17T10:00:00Z",
  "summary": null,
  "message_count": 0,
  "last_activity_at": null,
  "current_state": null,
  "messages": []
}
```

### Get Session

Get a specific session with full message history.

**Endpoint:** `GET /api/sessions/{id}/`

**Authentication:** Required

**Response:**
```json
{
  "id": 1,
  "agent_configuration": 1,
  "agent_name": "default",
  "started_at": "2024-01-15T10:00:00Z",
  "summary": "Discussion about AI and machine learning",
  "message_count": 12,
  "last_activity_at": "2024-01-15T11:00:00Z",
  "current_state": null,
  "messages": [
    {
      "id": 1,
      "chat_date": "2024-01-15T10:00:00Z",
      "message": "What is machine learning?",
      "is_user": true,
      "is_agent": false,
      "is_agent_growth": false,
      "is_read": true,
      "metadata": null,
      "critical": false,
      "critical_type": null
    }
  ]
}
```

### Delete Session

Delete a chat session.

**Endpoint:** `DELETE /api/sessions/{id}/`

**Authentication:** Required

**Response:** `204 No Content`

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request
```json
{
  "message": ["This field is required."]
}
```

### 401 Unauthorized
```json
{
  "detail": "Authentication credentials were not provided."
}
```

or

```json
{
  "detail": "Given token not valid for any token type",
  "code": "token_not_valid"
}
```

### 404 Not Found
```json
{
  "error": "Session not found"
}
```

or

```json
{
  "detail": "Not found."
}
```

## Rate Limiting

The API does not currently implement rate limiting, but it is recommended for production use.

## Pagination

List endpoints support pagination with the following parameters:
- `page`: Page number (default: 1)
- `page_size`: Results per page (default: 100, max: 100)

Paginated responses include:
```json
{
  "count": 150,
  "next": "http://localhost:8000/api/sessions/?page=2",
  "previous": null,
  "results": [...]
}
```

## Example Usage

### Python Example

```python
import requests

# Login
response = requests.post('http://localhost:8000/api/auth/login/', json={
    'username': 'myuser',
    'password': 'mypassword'
})
tokens = response.json()
access_token = tokens['access']

# Set up headers
headers = {
    'Authorization': f'Bearer {access_token}',
    'Content-Type': 'application/json'
}

# Create an agent
agent_response = requests.post('http://localhost:8000/api/agents/', 
    headers=headers,
    json={
        'name': 'my-assistant',
        'parameters': {
            'model': 'gpt-4',
            'personality_prompt': 'You are helpful'
        }
    }
)
agent = agent_response.json()

# Send a chat message
chat_response = requests.post('http://localhost:8000/api/chat/',
    headers=headers,
    json={
        'message': 'Hello!',
        'agent_id': agent['id']
    }
)
chat = chat_response.json()
print(f"AI Response: {chat['response']}")

# Get chat history
history_response = requests.get('http://localhost:8000/api/chat/history/',
    headers=headers
)
history = history_response.json()
print(f"Total sessions: {len(history['sessions'])}")
```

### JavaScript Example

```javascript
// Login
const loginResponse = await fetch('http://localhost:8000/api/auth/login/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    username: 'myuser',
    password: 'mypassword'
  })
});
const { access } = await loginResponse.json();

// Create an agent
const agentResponse = await fetch('http://localhost:8000/api/agents/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${access}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    name: 'my-assistant',
    parameters: {
      model: 'gpt-4',
      personality_prompt: 'You are helpful'
    }
  })
});
const agent = await agentResponse.json();

// Send a chat message
const chatResponse = await fetch('http://localhost:8000/api/chat/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${access}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    message: 'Hello!',
    agent_id: agent.id
  })
});
const chat = await chatResponse.json();
console.log('AI Response:', chat.response);

// Get chat history
const historyResponse = await fetch('http://localhost:8000/api/chat/history/', {
  headers: { 'Authorization': `Bearer ${access}` }
});
const { sessions } = await historyResponse.json();
console.log('Total sessions:', sessions.length);
```

## Notes

- JWT access tokens expire after 24 hours
- Refresh tokens expire after 7 days
- All timestamps are in ISO 8601 format (UTC)
- The API supports both single and split message responses from the AI
- Session summaries are automatically generated every 10 messages
- Personality updates are evaluated every 20 messages and auto-applied if confidence > 0.8
