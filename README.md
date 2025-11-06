# Lingxi - Multi-Agent Group Chat AI

A Django-based AI chat application featuring multiple AI agents with distinct personalities, enabling engaging group conversations.

## Features

### 🤖 Multi-Agent Group Chat
- **Three Unique AI Agents**: Alice (friendly 😊), Bob (professional 🧠), and Charlie (creative 🎨)
- **Group Conversations**: 1-2 agents respond to each message, creating dynamic discussions
- **Distinct Personalities**: Each agent has a unique communication style and personality
- **Visual Identity**: Color-coded messages with emoji avatars for easy agent identification

### 🎨 Rich Chat Experience
- Modern, responsive UI with Apple-inspired design
- Session management with conversation history
- Real-time message delivery
- Read receipts and unread message indicators
- Export conversation data

### 🔧 Agent Management
- Add, edit, and configure AI agents
- Customize agent personalities, emojis, and colors
- Activate/deactivate agents per session
- Admin interface for agent management

### 📊 Advanced Features
- Automatic conversation summarization (every 10 messages)
- Proactive messaging based on inactivity
- Personality adaptation suggestions (every 20 messages)
- Background task processing with Celery
- Session state management

See [MULTI_AGENT.md](MULTI_AGENT.md) for detailed documentation on the multi-agent feature.

## Prerequisites
- Python 3.12 or higher (Python 3.13+ recommended)
- pip (Python package manager)
- Virtual environment (recommended)
- UV installed for project management
- OpenAI API key (optional, for AI features)
- Redis server (required for Celery background tasks)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/aeilot/lingxi.git
   cd lingxi
   ```

2. Set up a virtual environment:
   ```bash
   uv venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   uv sync
   ```

4. Install and start Redis (required for Celery):
   ```bash
   # On macOS
   brew install redis
   brew services start redis
   
   # On Ubuntu/Debian
   sudo apt-get install redis-server
   sudo systemctl start redis
   
   # On Windows (using WSL or Docker)
   # Use Docker: docker run -d -p 6379:6379 redis
   ```

5. Configure environment variables:
   ```bash
   # Copy the example environment file to the app directory
   cp .env.example app/.env
   
   # Edit app/.env and add your OpenAI API key
   # OPENAI_API_KEY=your_api_key_here
   # OPENAI_BASE_URL=https://api.openai.com/v1
   # OPENAI_MODEL=gpt-3.5-turbo
   # CELERY_BROKER_URL=redis://localhost:6379/0
   ```

6. Apply migrations:
   ```bash
   cd app
   uv run manage.py migrate
   ```

7. Run the development server and Celery workers:
   ```bash
   # Terminal 1: Run Django development server
   # From the app directory
   uv run manage.py runserver
   
   # Terminal 2: Run Celery worker
   # From the app directory
   celery -A app worker --loglevel=info
   
   # Terminal 3: Run Celery beat scheduler (for periodic tasks)
   # From the app directory
   celery -A app beat --loglevel=info
   ```

## Configuration

### Environment Variables

The application uses environment variables for OpenAI API and Celery configuration. Create a `.env` file in the `app/` directory with the following settings:

- `OPENAI_API_KEY`: Your OpenAI API key (required for AI responses)
- `OPENAI_BASE_URL`: The OpenAI API base URL (default: https://api.openai.com/v1)
- `OPENAI_MODEL`: The model to use (default: gpt-3.5-turbo)
- `SCHEDULER_CHECK_INTERVAL_MINUTES`: Interval in minutes for checking session inactivity (default: 5)
- `CELERY_BROKER_URL`: Redis broker URL for Celery (default: redis://localhost:6379/0)
- `CELERY_RESULT_BACKEND`: Redis result backend for Celery (default: redis://localhost:6379/0)

Example:
```
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-3.5-turbo
SCHEDULER_CHECK_INTERVAL_MINUTES=5
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### Celery Background Tasks

The application uses Celery for background task processing with two main periodic tasks:

1. **Session Inactivity Checker**: Runs every 5 minutes (configurable via `SCHEDULER_CHECK_INTERVAL_MINUTES`)
   - Checks all sessions for inactivity
   - Uses the DecisionModule to determine if proactive messages should be sent to inactive users
   
2. **Personality Update Checker**: Runs every 20 minutes
   - Analyzes conversation patterns in active sessions with 20+ messages
   - Suggests personality updates based on user interaction patterns
   - Stores suggestions in session state for user review

The tasks run automatically when you start the Celery worker and beat scheduler.

### Agent Personality

You can customize the AI agent's personality in two ways:

#### Manual Update:
1. Click the ⚙️ settings button in the chat interface
2. Enter a personality prompt (e.g., "You are a helpful and friendly assistant who explains things clearly.")
3. Click "Save Personality"

#### Automatic Suggestions:
After several rounds of conversation (20+ messages), the system will analyze the conversation and may suggest personality updates that better match your communication style. These suggestions will appear in the chat interface, and you can choose to apply or dismiss them.

The personality prompt is stored in the database and persists across sessions.

## Usage
- Access the application at `http://127.0.0.1:8000/` after starting the development server.
- Use UV for managing tasks and tracking project progress.

## Project Structure
```
proactive-ai/
├── app/
│   ├── db.sqlite3
│   ├── manage.py
│   └── app/
│       ├── __init__.py
│       ├── asgi.py
│       ├── settings.py
│       ├── urls.py
│       ├── wsgi.py
│       └── __pycache__/
├── pyproject.toml
└── README.md
```

## Contributing
Contributions are welcome! Please fork the repository and submit a pull request.

## License
This project is licensed under the MIT License. See the LICENSE file for details.
