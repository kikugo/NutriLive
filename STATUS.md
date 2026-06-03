# NutriLive — Project Status

> Single source of truth. Supersedes `HANDOFF_NUTRILIVE.md` (Jun 2) and
> `IMPROVEMENT_PLAN.md` (May 14), which disagreed with each other and with the
> code. Every claim below was verified against the codebase on 2026-06-04.

---

## TL;DR

A voice-first nutrition logging app. The **infrastructure is real and tested**
(Gemini Live voice bridge, FastAPI backend, React frontend, CI). It is **not yet
a product**: logged data does not persist, there is no auth, and macro numbers
are estimates, not database-backed. The three product-critical gaps from the old
plan are all still open.

- Backend: `app/` — FastAPI. **31 tests passing.**
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
`APP_ENV`, `UPSTREAM_MODE` (`mock` | `gemini`), `CORS_ORIGINS`.
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
    meal_store.py         IN-MEMORY dict+Lock  (does not survive restart)
    session_store.py      IN-MEMORY dict+Lock  (does not survive restart)
    nutrition.py          pure macro math (totals, progress vs goals)
    milestone.py
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
- **Frontend**: live voice modal, transcript updates, audio playback queue,
  meal-confirm modal with edit-before-save, dashboard empty/error states.
- **Security/ops**: `frontend/.npmrc` (save-exact), CI (`.github/workflows/ci.yml`),
  dependabot (`.github/dependabot.yml`). The 5 pruned frontend deps are gone.
- **Tests**: 9 files, 31 tests, all green.

### Endpoints
- `GET /health`, `GET /`
- `POST /v1/live/session`, `WS /v1/live/ws/{session_id}`
- `GET /v1/live/session/{id}`, `GET /v1/live/sessions`, `GET /v1/live/stats`,
  `POST /v1/live/cleanup`, `POST /v1/live/expire-idle`
- `POST /v1/nutrition/daily-stats`, `POST /v1/nutrition/progress`
- `POST /v1/meals`, `GET /v1/meals`
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

### 2. No persistence — THE #1 blocker
- `meal_store.py` and `session_store.py` are in-memory `dict + Lock`.
- Everything a user logs is lost on restart. No DB.
- Wiring a nutrition API or auth onto this is premature until it's fixed.

### 3. No auth / per-user isolation
- No `get_current_user`, no JWT verification, no row-level security.
- Every meal/session route is open; data is global, not per-user.

### 4. Tech debt
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
But this is lower priority than persistence + auth.

---

## Recommended Order

1. **Persistence** — SQLite or Postgres-backed repos replacing the in-memory
   stores; keep route signatures stable. (Unblocks everything else.)
2. **Auth + per-user isolation** — pick one provider, add a `get_current_user`
   dependency to meal/session routes.
3. **Nutrition accuracy** — resolve the decision above (likely USDA layer).
4. **Polish** — WS schema validation, rate limiting, chunk-splitting, e2e tests.

---

## Conventions

- Natural commit messages (no `fix(...)` prefixes); distinct features committed
  separately; `main` is the working branch.
- Sensitive config stays local and gitignored (`.env`, `firebase-config.json`).
