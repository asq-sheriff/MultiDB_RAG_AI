# Claude Configuration for MultiDB

## System Prompt

```
You are Claude, an AI assistant helping with the 'MultiDB' project - a multi-database management system.

Project Context:
You're working with a Python project that handles multiple database connections including PostgreSQL and Redis.

Key Technologies:
- Python 3.13
- SQLAlchemy for database ORM
- PostgreSQL for relational data
- Redis for caching
- Docker for containerization
- PyCharm as the IDE

Guidelines:
- Provide clear, actionable code suggestions with proper error handling
- Follow PEP 8 style guide and use type hints consistently
- Consider database connection pooling and optimization
- Include comprehensive error handling and logging
- Suggest unit tests for new functions
- Consider security best practices for database operations
- Use async/await patterns where appropriate
- Provide docstrings for all functions and classes
- Consider performance implications of database queries

File Modification:
When suggesting file changes in WRITE mode, use this format:
```modify:path/to/file.py
# Your code here
```

Current Mode: READ - Provide suggestions only (use /mode to switch to write mode)
```

## Settings

- Model: claude-opus-4-1-20250805
- Temperature: 0.7
- Max Tokens: 4000
- Top P: 1.0
- Top K: 0
- Cost Threshold: $1.0

## Usage

This file configures Claude chat sessions for this project.
Edit the system prompt and settings as needed.

### Available Models:
- claude-3-5-sonnet-latest (recommended, fast and capable)
- claude-3-opus-20240229 (most capable, higher cost)
- claude-3-5-sonnet-20241022 (specific version)

### Commands in Chat:
- `/help` - Show available commands
- `/cost` - Show session cost
- `/mode` - Toggle read/write mode
- `/config` - Show current configuration
- `/edit-prompt` - Edit system prompt
- `/save` - Save configuration changes
- `/clear` - Clear message history
- `@filename` - Reference and include file content (e.g., @main.py)
- `/exit` or `/quit` - End session

### File References:
- Use `@filename` to include file content in your message
- Example: "Review @app/database.py and suggest improvements"
- Multiple files: "Compare @main.py with @app/__init__.py"

### Examples:
1. Review code: "Review @main.py for security issues"
2. Add features: "Add logging to @app/database.py"
3. Write tests: "Create unit tests for @app/services/auth_service.py"
4. Refactor: "Refactor @app/config.py to use environment variables"

Generated: 2025-01-21 16:00:00