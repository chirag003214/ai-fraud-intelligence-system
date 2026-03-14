# Contributing to Sentinel

## Development Setup

1. **Clone and install:**
```bash
git clone https://github.com/chirag003214/ai-fraud-intelligence-system
cd ai-fraud-intelligence-system/sentinel
pip install -e ".[dev]"
```

2. **Set up environment:**
```bash
cp .env.example .env
# Edit .env with your values
```

3. **Start dependencies:**
```bash
docker-compose up -d postgres redis
```

4. **Run the backend:**
```bash
uvicorn sentinel.src.api.main:app --reload --port 8000
```

5. **Run tests:**
```bash
make test
```

## Code Quality

Before submitting a PR:
```bash
make lint       # ruff check
make typecheck  # mypy strict mode
make test       # pytest with coverage
make format     # ruff auto-format
```

## PR Requirements

- All tests must pass
- Coverage must be ≥ 80%
- No ruff errors
- No mypy errors (strict mode)
- One logical change per commit
- Clear commit message describing the change

## Architecture Rules

1. **No business logic in route handlers.** Routes validate input, call a service, return a response.
2. **No FastAPI imports in services.** Services are pure Python, fully testable without HTTP.
3. **No synchronous database calls.** All DB operations must be async.
4. **No secrets in code.** All configuration via environment variables.
5. **Every function has type annotations and a docstring.**
