# NutriLive

Log meals by talking. You say what you ate, Gemini Live parses it into a food and a
portion, and the backend verifies the macros against USDA FoodData Central instead of
trusting the model's estimate.

## What's built

A React frontend and a FastAPI backend, connected over WebSocket for the voice path:
you talk, Gemini Live streams back a structured food and portion, and the backend
takes it from there.

- **Voice bridge.** The `/v1/live/ws/{session_id}` endpoint holds the Gemini Live
  session and streams parsed meals back to the frontend as they come in.
- **Persistence.** Sessions and their state live in SQLite, so a restart does not
  lose an in-progress log. Meals themselves are written to Firestore by the
  frontend.
- **Per-user isolation.** Requests are scoped to a user behind Firebase ID token
  auth, so one person's meals never bleed into another's.
- **Macro verification.** Instead of trusting whatever number the model estimates,
  the backend can look the food up against USDA FoodData Central and use the
  measured macros.

Two of these ship switched off. Set `NUTRITION_LOOKUP_MODE=usda` with a
`USDA_API_KEY` to verify macros against the database, and `AUTH_MODE=firebase` to
turn on per-user isolation. Without them you get the model's own estimate and a
single shared user, which is fine for a local run and wrong for anything else.

## Running it

### Backend quick start

Use Python 3.12: the dependencies don't have working wheels on 3.14 yet.

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

### Frontend quick start

```bash
cd frontend
npm ci
npm run dev
```

Frontend runs on `http://localhost:3000` and backend on `http://localhost:8000`.

### Verify and test

```bash
# backend tests
.venv/bin/python -m pytest -q

# frontend checks
cd frontend
npm run lint
npm run build
npm run audit:high
```

Backend suite: 43 tests, all passing.

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

Meals are stored in Firestore by the frontend (`users/{uid}/meals`), not via a
backend endpoint.

## Status

See `STATUS.md` for what's built versus what's still open. Short version: the
voice bridge and APIs work; meals live in Firestore while sessions persist to
SQLite scoped per user behind Firebase ID token auth (`AUTH_MODE=firebase`).
Macros can be verified against USDA FoodData Central (`NUTRITION_LOOKUP_MODE=usda`) instead of
trusting the model's estimate. Local dev and tests run with `AUTH_MODE=disabled`
(a fixed dev user) and lookup off.
