# NutriLive — Project Status

> Single source of truth. Supersedes `HANDOFF_NUTRILIVE.md` (Jun 2) and
> `IMPROVEMENT_PLAN.md` (May 14), which disagreed with each other and with the
> code. Every claim below was verified against the codebase on 2026-06-04.

---

## TL;DR

A voice-first nutrition logging app. The **infrastructure is real and tested**
(Gemini Live voice bridge, FastAPI backend, React frontend, CI). Meals and
sessions **persist to SQLite** and are **scoped per user** behind Firebase ID
token auth. Macros can be **verified against USDA FoodData Central** instead of
trusting the LLM estimate (opt-in via `NUTRITION_LOOKUP_MODE=usda`).

- Backend: `app/` — FastAPI. **41 tests passing.**
- Frontend: `frontend/` — React + Vite + TypeScript.
- Both status docs were local/untracked. This file is too unless staged.

---

## Environment / How to Run

Backend uses **uv** on **Python 3.12** (3.14 lacks working wheels for the deps —
do not use it).

```bash
uv venv --python 3.12 --seed          # create .venv
uv pip install -e ".[dev]"            # runtime + dev deps (pytest, httpx)
.venv/bin/python -m pytest -q         # 39 passing
uvicorn app.main:app --reload         # backend on :8000
```

```bash
cd frontend && npm ci && npm run dev  # frontend on :3000
```

Env vars (local `.env`, gitignored): `GEMINI_API_KEY`, `GEMINI_MODEL`,
`APP_ENV`, `UPSTREAM_MODE` (`mock` | `gemini`), `CORS_ORIGINS`,
`DATABASE_PATH` (SQLite file, defaults to `nutrilive.db`),
`AUTH_MODE` (`disabled` | `firebase`), `FIREBASE_PROJECT_ID` (required when
`AUTH_MODE=firebase`), `NUTRITION_LOOKUP_MODE` (`off` | `usda`), `USDA_API_KEY`
(required when `NUTRITION_LOOKUP_MODE=usda`).
Frontend Firebase config expected at `frontend/firebase-config.json` (gitignored;
example in `frontend/firebase-config.example.json`).

---

## Architecture (verified)

```
app/
  main.py                 FastAPI app, routes, request-id middleware, WS handler
  config.py               settings (pydantic-settings)
  schemas.py
  contracts/              nutrition pydantic models
  services/
    upstream.py           UpstreamClient (mock) + GeminiUpstreamClient (real Live)
    live_bridge.py        maps client/upstream events <-> websocket frames
    session_store.py      SQLite-backed, scoped by user_id
    nutrition.py          pure macro math (totals, progress vs goals)
    nutrition_lookup.py   USDA FoodData Central lookup (off | usda)
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
  `prepare_meal_log` tool-call (now also asks the model for an estimated portion
  in grams).
- **Macro verification** — `app/services/nutrition_lookup.py`. With
  `NUTRITION_LOOKUP_MODE=usda`, the bridge replaces the model's estimated macros
  with USDA per-gram values scaled to the portion, tagged `source="usda"`. With
  no key, no portion, or no match it keeps the estimate (`source="estimate"`).
- **Mock mode** for tests/CI (`UPSTREAM_MODE=mock`) — no network needed.
- **WebSocket flow** `WS /v1/live/ws/{session_id}` with the event families
  documented below; frontend maps these into live voice state.
- **REST endpoints** all present in `app/main.py` (see below).
- **Meal storage**: meals live in **Firestore** (`users/{uid}/meals`), written by
  the frontend with real-time sync. Macros are USDA-verified in-flight (in the
  live bridge) before the frontend saves them.
- **Session persistence**: sessions in SQLite, scoped per `user_id`, survive
  restart.
- **Auth**: `app/auth.py` verifies Firebase ID tokens against Google's public
  keys (`AUTH_MODE=firebase`). `AUTH_MODE=disabled` runs as a dev user for local
  dev and tests. Session routes require auth and isolate data by user.
- **Frontend**: live voice modal, transcript updates, audio playback queue,
  meal-confirm modal with edit-before-save and a USDA-verified/estimated badge,
  dashboard empty/error states.
- **Security/ops**: `frontend/.npmrc` (save-exact), CI (`.github/workflows/ci.yml`),
  dependabot (`.github/dependabot.yml`). The 5 pruned frontend deps are gone.
- **Tests**: 9 files, 39 tests, all green.

### Endpoints
(`A` = requires auth in `firebase` mode and is scoped to the caller's user)
- `GET /health`, `GET /`
- `POST /v1/live/session` `A`, `WS /v1/live/ws/{session_id}`
- `GET /v1/live/session/{id}` `A`, `GET /v1/live/sessions` `A`,
  `GET /v1/live/stats` `A`, `POST /v1/live/cleanup` `A`,
  `POST /v1/live/expire-idle` `A`
- `POST /v1/nutrition/daily-stats`, `POST /v1/nutrition/progress` (stateless math)
- `GET /v1/milestone/context-retirement`
- Meals are not a backend endpoint — the frontend reads/writes Firestore directly.

### WebSocket events
- Inbound to backend: `start`, `audio_chunk`, `text`, `stop`, `close`, `ping`
- Outbound to client: `ready`, `server_ack`, `user_transcript`,
  `model_transcript`, `model_audio_chunk`, `tool_call`, `done`, `error`, `pong`

---

## What Is NOT Done ⚠️ (the real gaps)

### 1. Macro accuracy depends on opt-in USDA + a portion estimate
- The USDA verification layer exists but is **off by default** — until
  `NUTRITION_LOOKUP_MODE=usda` (+ `USDA_API_KEY`) is set, macros are still the
  LLM estimate, tagged `source="estimate"`.
- Even with USDA on, accuracy hinges on **Gemini estimating the portion (grams)**
  and on the **search returning the right food**. We take the top match only;
  there's no disambiguation, brand/restaurant data, or multi-ingredient split.
- **mock mode** still emits placeholder macros (`calories=450, grams=350`) — it's
  for tests/local, not real numbers.

### 2. Tech debt
- WebSocket payloads validated *after* receive, not via a strict schema first.
- LiveBridge error handling is generic — upstream failures can look like parse
  errors.
- No rate limiting (`slowapi` or middleware).
- Frontend Vite build warns on a >500 kB chunk (no code-splitting yet).
- No frontend e2e/smoke tests for the voice + meal flow.
- `app/web/` legacy UI and the `/v1/milestone/context-retirement` endpoint are
  vestigial (the `app/web/app.js` still calls the now-removed `/v1/meals`). Safe
  to delete in a follow-up.
- Meals only live in Firestore — the backend can't read meal history server-side
  (needed later for coach mode / weekly trends) until `firebase-admin` is added.

---

## Recommended Order

1. ~~**Persistence**~~ — done. Sessions are SQLite-backed (`app/db.py`, path via
   `DATABASE_PATH`). Meals live in Firestore (see below).
2. ~~**Auth + per-user isolation**~~ — done. Firebase ID token verification in
   `app/auth.py`; session data scoped by `user_id`. To turn it on, set
   `AUTH_MODE=firebase` and `FIREBASE_PROJECT_ID`. Next step when needed: WS-path
   auth (currently the session id is the capability) and a persisted user record.
3. ~~**Nutrition accuracy**~~ — done (opt-in). USDA verification layer in
   `app/services/nutrition_lookup.py`; enable with `NUTRITION_LOOKUP_MODE=usda`.
   The confirm modal shows a "USDA verified" / "Estimated" badge. Possible
   follow-up: food disambiguation.
4. ~~**Reconcile meal storage**~~ — done. Firestore is the single source of truth
   for meals; the unused backend SQLite meal store and `/v1/meals` endpoints were
   removed.
5. **Polish** — WS schema validation, rate limiting, chunk-splitting, e2e tests,
   delete the vestigial `app/web/` UI + milestone endpoint.

---

## Conventions

- Natural commit messages (no `fix(...)` prefixes); distinct features committed
  separately; `main` is the working branch.
- Sensitive config stays local and gitignored (`.env`, `firebase-config.json`).
