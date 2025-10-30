# Personality Update Feature

## Overview

The Personality Update feature automatically analyzes conversation patterns and suggests improvements to the AI agent's personality based on user interactions. This feature uses Celery background tasks to periodically check sessions and make intelligent recommendations.

## How It Works

### 1. Background Monitoring

A Celery Beat task (`check_personality_updates_task`) runs every 20 minutes to:
- Scan all active chat sessions with 20+ messages
- Analyze sessions that were active in the last 24 hours
- Skip sessions that were checked in the last 24 hours

### 2. Analysis Process

For eligible sessions, the system:
1. Retrieves the last 30 messages from the conversation
2. Examines the current personality prompt (if any)
3. Uses AI (OpenAI) to analyze:
   - User's communication style (formal/casual, detailed/concise)
   - Topics being discussed
   - Level of detail the user prefers
   - User satisfaction with current responses
   - Conversation topic consistency

### 3. Suggestion Generation

The analysis produces:
- `should_update`: Boolean indicating if an update is recommended
- `reason`: Explanation for the decision
- `suggested_personality`: New personality prompt (if update recommended)
- `confidence`: Confidence score (0.0 to 1.0)

### 4. User Notification

When a suggestion is available:
- A banner appears at the top of the chat interface
- Shows the reason, suggested personality, and confidence level
- User can choose to "Apply" or "Dismiss" the suggestion

## API Endpoints

### Check for Personality Suggestion
```
GET /api/sessions/{session_id}/personality-suggestion
```

Response:
```json
{
  "session_id": 1,
  "has_suggestion": true,
  "suggestion": {
    "should_update": true,
    "reason": "User prefers detailed technical explanations",
    "suggested_personality": "You are a knowledgeable assistant...",
    "confidence": 0.85
  }
}
```

### Apply Personality Update
```
POST /api/sessions/{session_id}/personality-update
```

Applies the suggested personality to the agent configuration.

### Dismiss Suggestion
```
POST /api/sessions/{session_id}/personality-dismiss
```

Dismisses the current suggestion without applying it.

## Configuration

### Celery Beat Schedule

In `settings.py`:
```python
CELERY_BEAT_SCHEDULE = {
    'check-personality-updates': {
        'task': 'agent.tasks.check_personality_updates_task',
        'schedule': 1200.0,  # Every 20 minutes
    },
}
```

### Minimum Messages

The feature only activates for sessions with at least 20 messages. This ensures sufficient conversation history for meaningful analysis.

### Check Frequency

- Personality checks run every 20 minutes (Celery Beat schedule)
- Each session is checked at most once per 24 hours
- Frontend polls for suggestions every 5 minutes

## Usage

### For Users

1. **Chat normally** - The system monitors in the background
2. **Review suggestions** - When a banner appears, read the explanation
3. **Apply or Dismiss** - Choose whether to update the personality
4. **Continue chatting** - The new personality takes effect immediately

### For Developers

#### Testing the Feature

```python
from agent.core import decide_personality_update
from agent.models import ChatSession, AgentConfiguration

# Get a session
session = ChatSession.objects.get(id=1)
agent_config = session.agent_configuration

# Check for personality update
decision = decide_personality_update(
    session, 
    agent_config, 
    api_key="your-key",
    base_url="https://api.openai.com/v1"
)

print(decision)
```

#### Running Celery Tasks Manually

```bash
# From the app directory
celery -A app call agent.tasks.check_personality_updates_task
```

## Database Schema

The feature uses the existing `ChatSession.current_state` JSONField to store:

```json
{
  "last_personality_check": "2025-10-30T05:00:00Z",
  "personality_update_suggestion": {
    "should_update": true,
    "reason": "...",
    "suggested_personality": "...",
    "confidence": 0.85
  }
}
```

## Fallback Behavior

### Without API Key

If no OpenAI API key is configured:
- Simple heuristic: suggest update every 50 messages
- Default suggestion: "You are a helpful and friendly assistant."
- Confidence: 0.5

### On Error

If analysis fails:
- Returns `should_update: false`
- Logs error details
- Session check timestamp is still updated

## Security & Privacy

- Personality suggestions are session-specific
- No personal data is permanently stored in suggestions
- Suggestions can be dismissed without affecting functionality
- API keys are never exposed to the frontend

## Performance Considerations

- Celery tasks run asynchronously, not blocking the main application
- Only active sessions (activity in last 24 hours) are checked
- Maximum of 30 messages analyzed per session
- Rate limiting: one check per session per 24 hours

## Monitoring

To monitor the personality update tasks:

```bash
# View Celery logs
celery -A app worker --loglevel=info

# View task execution
celery -A app events
```

Check Django logs for:
- `"Checking personality update for session {id}"`
- `"Personality update check for session {id}: should_update={bool}"`
- Any error messages from the analysis process
