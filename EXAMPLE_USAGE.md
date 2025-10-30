# Example: Using the Personality Update Feature

This example demonstrates how the personality update feature works in practice.

## Setup

1. Start Redis:
```bash
redis-server
```

2. Start Django development server:
```bash
cd app
python manage.py runserver
```

3. Start Celery worker:
```bash
cd app
celery -A app worker --loglevel=info
```

4. Start Celery beat (for periodic tasks):
```bash
cd app
celery -A app beat --loglevel=info
```

## Example Session

### Step 1: Create a Chat Session

Open your browser and navigate to `http://127.0.0.1:8000/`

Click the "+" button to create a new chat session.

### Step 2: Have a Conversation (20+ messages)

Example conversation about Python programming:

**User:** "Can you help me learn Python?"
**AI:** "Of course! Python is a great language to learn..."

**User:** "How do I create a list?"
**AI:** "You can create a list using square brackets..."

**User:** "What about dictionaries?"
**AI:** "Dictionaries are created with curly braces..."

Continue the conversation for at least 20 messages (10 exchanges).

### Step 3: Wait for Analysis

After 20+ messages, the Celery beat task will:
1. Detect your session has sufficient messages
2. Analyze the conversation patterns
3. Generate a personality suggestion if appropriate

This happens automatically in the background every 20 minutes.

### Step 4: Review the Suggestion

If a personality update is suggested, you'll see a banner at the top of the chat:

```
💡 Personality Update Suggestion                    Confidence: 85%

User prefers detailed technical explanations with code examples

Suggested personality: "You are a knowledgeable Python programming 
assistant who provides detailed technical explanations with practical 
code examples and best practices."

[Apply]  [Dismiss]
```

### Step 5: Apply or Dismiss

- Click **Apply** to update the agent's personality
- Click **Dismiss** to ignore the suggestion

## Manual Testing via API

You can also test the feature programmatically:

### 1. Check for Suggestions

```bash
curl http://127.0.0.1:8000/api/sessions/1/personality-suggestion
```

Response:
```json
{
  "session_id": 1,
  "has_suggestion": true,
  "suggestion": {
    "should_update": true,
    "reason": "User prefers detailed technical explanations",
    "suggested_personality": "You are a knowledgeable Python...",
    "confidence": 0.85
  }
}
```

### 2. Apply a Suggestion

```bash
curl -X POST http://127.0.0.1:8000/api/sessions/1/personality-update \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN"
```

### 3. Dismiss a Suggestion

```bash
curl -X POST http://127.0.0.1:8000/api/sessions/1/personality-dismiss \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN"
```

## Manual Trigger (Development)

For testing, you can manually trigger the personality check:

```python
# In Django shell: python manage.py shell
from agent.models import ChatSession
from agent.core import decide_personality_update
from django.conf import settings

# Get your session
session = ChatSession.objects.get(id=1)
agent_config = session.agent_configuration

# Run the analysis
decision = decide_personality_update(
    session,
    agent_config,
    api_key=settings.OPENAI_API_KEY,
    base_url=settings.OPENAI_BASE_URL
)

print(decision)
```

## Expected Behavior

### With OpenAI API Key

The system will:
- Analyze the last 30 messages
- Examine conversation patterns
- Generate a contextual personality suggestion
- Provide confidence score based on analysis

### Without OpenAI API Key

The system will:
- Use simple heuristics (suggest at 50 message intervals)
- Provide a generic helpful assistant personality
- Set confidence to 0.5

## Monitoring

Watch the Celery logs to see the tasks running:

```
[2025-10-30 05:00:00,000: INFO] Running Celery task: check_personality_updates
[2025-10-30 05:00:01,234: INFO] Checking personality update for session 1
[2025-10-30 05:00:02,567: INFO] Personality update check for session 1: should_update=True, confidence=0.85
```

## Tips

1. **Message Count**: Ensure you have at least 20 messages before expecting suggestions
2. **Activity**: The session must have been active in the last 24 hours
3. **Frequency**: Each session is checked at most once per 24 hours
4. **API Key**: For best results, configure a valid OpenAI API key

## Troubleshooting

**No suggestion appearing?**
- Check message count (must be 20+)
- Verify Celery beat is running
- Check if session was already checked in last 24 hours
- Look at Celery logs for any errors

**Suggestion not applying?**
- Verify CSRF token is valid
- Check Django logs for errors
- Ensure the session exists

**Generic suggestions only?**
- Verify OpenAI API key is configured
- Check OPENAI_API_KEY in app/.env file
- Look for API errors in logs
