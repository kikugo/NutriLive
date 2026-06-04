# NutriLive — Project Status

> Single source of truth. Supersedes `HANDOFF_NUTRILIVE.md` (Jun 2) and
> `IMPROVEMENT_PLAN.md` (May 14), which disagreed with each other and with the
> code. Every claim below was verified against the codebase on 2026-06-04.

---

## TL;DR

A voice-first nutrition logging app. The **infrastructure is real and tested**
(Gemini Live voice bridge, FastAPI backend, React frontend, CI). Meals and
sessions **persist to SQLite** and are **scoped per user** behind Firebase ID
token auth. The remaining product gap: macro numbers are estimates rather than
looked up from a nutrition database.

- Backend: `app/` — FastAPI. **33 tests passing.**
- Frontend: `frontend/` — React + Vite + TypeScript.
- Both status docs were local/untracked. This file is too unless staged.

---

## Environment / How to Run

Backend uses **uv** on **Python 3.12** (3.14 lacks working wheels for the deps —
do not use it).

```bash
uv venv --python 3.12 --seed          # create .venv
uv pip install -e ".[dev]"            # runtime + dev deps (pytest, httpx)
.venv/bin/python -m pytest -q         # 31 passing
uvicorn app.main:app --reload         # backend on :8000
```

```bash
cd frontend && npm ci && npm run dev  # frontend on :3000
```

Env vars (local `.env`, gitignored): `GEMINI_API_KEY`, `GEMINI_MODEL`,
`APP_ENV`, `UPSTREAM_MODE` (`mock` | `gemini`), `CORS_ORIGINS`,
`DATABASE_PATH` (SQLite file, defaults to `nutrilive.db`),
`AUTH_MODE` (`disabled` | `firebase`), `FIREBASE_PROJECT_ID` (required when
`AUTH_MODE=firebase`).
Frontend Firebase config expected at `frontend/firebase-config.json` (gitignored;
example in `frontend/firebase-config.example.json`).

---

## Architecture (verified)

```
app/
  main.py                 FastAPI app, routes, request-id middleware, WS handler
  config.py               settings (pydantic-settings)
  schemas.py
  contracts/              meal_log, nutrition pydantic models
  services/
    upstream.py           UpstreamClient (mock) + GeminiUpstreamClient (real Live)
    live_bridge.py        maps client/upstream events <-> websocket frames
    meal_store.py         SQLite-backed, scoped by user_id
    session_store.py      SQLite-backed, scoped by user_id
    nutrition.py          pure macro math (totals, progress vs goals)
    milestone.py
  auth.py                 get_current_user dependency (Firebase ID token verify)
  db.py                   SQLite connection helper + schema
  web/                    legacy minimal HTML/JS UI (superseded by frontend/)

frontend/                 React + Vite + TS — canonical user-facing app
  src/App.tsx, firebase.ts, types.ts, lib/utils.ts
```

---

## What Works ✅ (verified against code)

- **Gemini Live voice bridge** — real `client.aio.live.connect` session in
  `app/services/upstream.py`: audio in/out, input+output transcription, and a
  `prepare_meal_log` tool-call that passes the model's args straight through.
- **Mock mode** for tests/CI (`UPSTREAM_MODE=mock`) — no network needed.
- **WebSocket flow** `WS /v1/live/ws/{session_id}` with the event families
  documented below; frontend maps these into live voice state.
- **REST endpoints** all present in `app/main.py` (see below).
- **Persistence**: meals and sessions in SQLite, scoped per `user_id`, survive
  restart.
- **Auth**: `app/auth.py` verifies Firebase ID tokens against Google's public
  keys (`AUTH_MODE=firebase`). `AUTH_MODE=disabled` runs as a dev user for local
  dev and tests. Meal/session routes require auth and isolate data by user.
- **Frontend**: live voice modal, transcript updates, audio playback queue,
  meal-confirm modal with edit-before-save, dashboard empty/error states.
- **Security/ops**: `frontend/.npmrc` (save-exact), CI (`.github/workflows/ci.yml`),
  dependabot (`.github/dependabot.yml`). The 5 pruned frontend deps are gone.
- **Tests**: 10 files, 33 tests, all green.

### Endpoints
(`A` = requires auth in `firebase` mode and is scoped to the caller's user)
- `GET /health`, `GET /`
- `POST /v1/live/session` `A`, `WS /v1/live/ws/{session_id}`
- `GET /v1/live/session/{id}` `A`, `GET /v1/live/sessions` `A`,
  `GET /v1/live/stats` `A`, `POST /v1/live/cleanup` `A`,
  `POST /v1/live/expire-idle` `A`
- `POST /v1/nutrition/daily-stats`, `POST /v1/nutrition/progress` (stateless math)
- `POST /v1/meals` `A`, `GET /v1/meals` `A`
- `GET /v1/milestone/context-retirement`

### WebSocket events
- Inbound to backend: `start`, `audio_chunk`, `text`, `stop`, `close`, `ping`
- Outbound to client: `ready`, `server_ack`, `user_transcript`,
  `model_transcript`, `model_audio_chunk`, `tool_call`, `done`, `error`, `pong`

---

## What Is NOT Done ⚠️ (the real gaps)

### 1. Macro numbers are not real
- **mock mode**: hardcoded `calories=450, protein=30, ...`
  (`app/services/live_bridge.py:77`).
- **gemini mode**: whatever the LLM estimates, passed through unverified.
- There is **no external nutrition API** (no USDA / Nutritionix). `httpx` is a
  dev/test dep only.
- **Decision pending** (see "Open Decision" below). The architecture moved to
  Gemini-does-the-parsing, so a full Nutritionix integration may be unnecessary;
  the open question is purely about *accuracy*.

### 2. Tech debt
- WebSocket payloads validated *after* receive, not via a strict schema first.
- LiveBridge error handling is generic — upstream failures can look like parse
  errors.
- No rate limiting (`slowapi` or middleware).
- Frontend Vite build warns on a >500 kB chunk (no code-splitting yet).
- No frontend e2e/smoke tests for the voice + meal flow.

---

## Open Decision: do we even need a nutrition API?

A nutrition API does two jobs: (1) parse NL → food+quantity, (2) look up verified
macros. Gemini Live now does (1) for free and *estimates* (2). So the only thing
a nutrition API adds today is **macro accuracy**.

| Option | Parsing | Accuracy | Cost | Effort |
|---|---|---|---|---|
| Gemini-only (current) | ✅ | ⚠️ estimate | $0 | done |
| + USDA FoodData Central | reuse Gemini | ✅ verified | free | medium |
| + Nutritionix | ✅ | ✅ verified | $99/mo | medium |
| Drop the idea (v1) | ✅ | ⚠️ accept estimates | $0 | none |

Recommendation: if accuracy matters, add **USDA as a verification layer** (Gemini
parses the food, USDA supplies real macros) — free and reuses Gemini's strength.
This is now the top open product gap.

---

## Recommended Order

1. ~~**Persistence**~~ — done. Meals and sessions are SQLite-backed
   (`app/db.py`, path via `DATABASE_PATH`); route signatures unchanged.
2. ~~**Auth + per-user isolation**~~ — done. Firebase ID token verification in
   `app/auth.py`; meal/session data scoped by `user_id`. To turn it on, set
   `AUTH_MODE=firebase` and `FIREBASE_PROJECT_ID`. Next step when needed: WS-path
   auth (currently the session id is the capability) and a persisted user record.
3. **Nutrition accuracy** — resolve the decision above (likely USDA layer).
   Now the top open gap.
4. **Polish** — WS schema validation, rate limiting, chunk-splitting, e2e tests.

---

## Conventions

- Natural commit messages (no `fix(...)` prefixes); distinct features committed
  separately; `main` is the working branch.
- Sensitive config stays local and gitignored (`.env`, `firebase-config.json`).
