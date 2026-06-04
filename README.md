# NutriLive

Voice-first nutrition logging. React frontend, FastAPI backend, Gemini Live for
the voice path.

## Backend quick start

Use Python 3.12 — the dependencies don't have working wheels on 3.14 yet.

```bash
uv venv --python 3.12 --seed
uv pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Set runtime mode in `.env`:

```bash
UPSTREAM_MODE=mock
# or
UPSTREAM_MODE=gemini
```

## Frontend quick start

```bash
cd frontend
npm ci
npm run dev
```

Frontend runs on `http://localhost:3000` and backend on `http://localhost:8000`.

## Verify and test

```bash
# backend tests
.venv/bin/python -m pytest -q

# frontend checks
cd frontend
npm run lint
npm run build
npm run audit:high
```

## API

- `GET /health`
- `GET /`
- `POST /v1/live/session`
- `GET /v1/live/session/{session_id}`
- `GET /v1/live/sessions`
- `GET /v1/live/stats`
- `POST /v1/live/cleanup`
- `POST /v1/live/expire-idle`
- `WS /v1/live/ws/{session_id}`
- `POST /v1/nutrition/daily-stats`
- `POST /v1/nutrition/progress`
- `POST /v1/meals`
- `GET /v1/meals`
- `GET /v1/milestone/context-retirement`

## Status

See `STATUS.md` for what's built versus what's still open. Short version: the
voice bridge and APIs work; meals and sessions persist to SQLite and are scoped
per user behind Firebase ID token auth (`AUTH_MODE=firebase`). The remaining gap
is macro accuracy — numbers are estimates rather than looked up from a nutrition
database. Local dev and tests run with `AUTH_MODE=disabled` (a fixed dev user).
