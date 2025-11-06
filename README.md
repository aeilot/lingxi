# Lingxi - AI Chat Backend

A comprehensive backend API for building AI-powered chat applications with multi-user support, agent management, and intelligent conversation features.

## Features

- **RESTful API**: Complete backend API for frontend applications
- **JWT Authentication**: Secure token-based authentication for multi-user support
- **Multi-Agent Management**: Create and manage multiple AI agents with different personalities
- **Chat Sessions**: Organize conversations into sessions with full history
- **Automatic Summaries**: Session summaries generated every 10 messages
- **Adaptive Personality**: AI personality automatically adapts based on conversation patterns
- **Proactive Messaging**: Background tasks for intelligent proactive engagement
- **Split Messages**: Support for multi-message responses
- **Read Receipts**: Track message read status

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

### Backend API

The application provides a comprehensive REST API for frontend applications. See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for detailed API documentation.

**Main API Endpoints:**

- `POST /api/auth/login/` - User authentication
- `POST /api/auth/refresh/` - Refresh JWT token
- `GET /api/agents/` - List agents
- `POST /api/agents/` - Create a new agent
- `PUT /api/agents/{id}/personality/` - Update agent personality
- `POST /api/chat/` - Send a message and get AI response
- `GET /api/chat/history/` - Get chat history
- `GET /api/sessions/` - List chat sessions
- `POST /api/sessions/` - Create a new session

**Example Usage:**

See the example scripts:
- Python: `python example_api_usage.py`
- JavaScript: `node example_api_usage.js`

### Legacy Web UI

Access the legacy web interface at `http://127.0.0.1:8000/` after starting the development server.

### Creating Users

Before using the API, create a user account:

```bash
cd app
python manage.py createsuperuser
```

Or create a regular user via Django shell:

```bash
cd app
python manage.py shell
```

```python
from django.contrib.auth.models import User
User.objects.create_user('username', 'email@example.com', 'password')
```

## Project Structure
```
lingxi/
├── app/
│   ├── agent/
│   │   ├── models.py          # Data models (User, Agent, Session, Message)
│   │   ├── api_views.py       # REST API views
│   │   ├── api_urls.py        # API URL routing
│   │   ├── serializers.py     # DRF serializers
│   │   ├── views.py           # Legacy UI views
│   │   ├── core.py            # AI logic and decision making
│   │   ├── tasks.py           # Celery background tasks
│   │   └── tests.py           # Test suite
│   ├── app/
│   │   ├── settings.py        # Django settings
│   │   ├── urls.py            # Main URL routing
│   │   └── celery.py          # Celery configuration
│   ├── templates/             # HTML templates (legacy UI)
│   ├── static/                # Static files (legacy UI)
│   ├── manage.py              # Django management script
│   └── db.sqlite3             # SQLite database
├── API_DOCUMENTATION.md       # Comprehensive API docs
├── example_api_usage.py       # Python API example
├── example_api_usage.js       # JavaScript API example
├── pyproject.toml             # Project dependencies
└── README.md                  # This file
```

## API Architecture

The backend uses Django REST Framework with JWT authentication:

1. **Authentication Layer**: JWT tokens for secure API access
2. **Multi-User Support**: Each user can have multiple agents and sessions
3. **Agent Management**: CRUD operations for AI agent configurations
4. **Chat Engine**: Real-time chat with AI, session management, and history
5. **Background Tasks**: Celery tasks for proactive features and personality updates

## Technology Stack

- **Backend Framework**: Django 5.2+
- **API Framework**: Django REST Framework
- **Authentication**: JWT (Simple JWT)
- **Database**: SQLite (development) / PostgreSQL (production recommended)
- **AI Integration**: OpenAI API
- **Task Queue**: Celery with Redis
- **Testing**: Django TestCase with DRF APIClient


## Contributing
Contributions are welcome! Please fork the repository and submit a pull request.

## License
This project is licensed under the MIT License. See the LICENSE file for details.
