# NutriLive

Realtime nutrition tracking app with a React frontend and Python backend.

## Backend quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
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
pytest -q

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
- `GET /v1/milestone/context-retirement`

## Milestone

`context` can be deleted when `/v1/milestone/context-retirement` returns:

- `"standalone_ui": true`
- `"live_session_api": true`
- `"meal_logging_api": true`
- `"nutrition_api": true`
- `"ready": true`
