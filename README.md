# Proactive AI

## Prerequisites
- Python 3.12 or higher
- pip (Python package manager)
- Virtual environment (recommended)
- UV installed for project management
- OpenAI API key (optional, for AI features)

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

4. Configure environment variables:
   ```bash
   # Copy the example environment file
   cp .env.example app/.env
   
   # Edit app/.env and add your OpenAI API key
   # OPENAI_API_KEY=your_api_key_here
   # OPENAI_BASE_URL=https://api.openai.com/v1
   # OPENAI_MODEL=gpt-3.5-turbo
   ```

5. Apply migrations:
   ```bash
   cd app
   uv run manage.py migrate
   ```

6. Run the development server:
   ```bash
   uv run manage.py runserver
   ```

## Configuration

### Environment Variables

The application uses environment variables for OpenAI API configuration. Create a `.env` file in the `app/` directory with the following settings:

- `OPENAI_API_KEY`: Your OpenAI API key (required for AI responses)
- `OPENAI_BASE_URL`: The OpenAI API base URL (default: https://api.openai.com/v1)
- `OPENAI_MODEL`: The model to use (default: gpt-3.5-turbo)

Example:
```
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-3.5-turbo
```

### Agent Personality

You can customize the AI agent's personality through the web interface:

1. Click the ⚙️ settings button in the chat interface
2. Enter a personality prompt (e.g., "You are a helpful and friendly assistant who explains things clearly.")
3. Click "Save Personality"

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
