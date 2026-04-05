# NutriLive

Python backend for real-time voice session orchestration.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

## API

- `GET /health`
- `POST /v1/live/session`
- `GET /v1/live/session/{session_id}`
- `WS /v1/live/ws/{session_id}`
