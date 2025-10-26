# Proactive AI

## Prerequisites
- Python 3.13 or higher
- pip (Python package manager)
- Virtual environment (recommended)
- UV installed for project management

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

3. Apply migrations:
   ```bash
   uv run manage.py migrate
   ```

4. Run the development server:
   ```bash
   uv run manage.py runserver
   ```

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
