from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from uuid import uuid4

from app.config import get_settings
from app.contracts.nutrition import Meal
from app.schemas import AudioChunkEvent, SessionCreateResponse, TextEvent
from app.services.live_bridge import LiveBridge
from app.services.nutrition import calculate_daily_stats
from app.services.session_store import session_store

settings = get_settings()

app = FastAPI(title="NutriLive Backend", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


async def send_ws_error(websocket: WebSocket, code: str, message: str) -> None:
    await websocket.send_json({"type": "error", "code": code, "message": message})


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "env": settings.app_env}


@app.post("/v1/live/session", response_model=SessionCreateResponse)
def create_live_session() -> SessionCreateResponse:
    session = session_store.create()
    return SessionCreateResponse(session_id=session.session_id)


@app.get("/v1/live/session/{session_id}")
def get_live_session(session_id: str) -> dict:
    session = session_store.get(session_id)
    if not session:
        return {"found": False}
    return {
        "found": True,
        "session_id": session.session_id,
        "status": session.status,
        "created_at": session.created_at.isoformat(),
    }


@app.get("/v1/live/stats")
def get_live_stats() -> dict:
    return session_store.stats()


@app.get("/v1/live/sessions")
def list_live_sessions(status: str | None = None) -> dict:
    sessions = session_store.list_sessions(status=status)
    return {
        "count": len(sessions),
        "sessions": [
            {
                "session_id": session.session_id,
                "status": session.status,
                "created_at": session.created_at.isoformat(),
            }
            for session in sessions
        ],
    }


@app.post("/v1/live/cleanup")
def cleanup_live_sessions(max_age_minutes: int = 60) -> dict:
    removed = session_store.cleanup_older_than(max_age_minutes=max_age_minutes)
    return {"removed": removed, "max_age_minutes": max_age_minutes}


@app.post("/v1/nutrition/daily-stats")
def get_daily_stats(meals: list[Meal]) -> dict:
    stats = calculate_daily_stats(meals)
    return stats.model_dump()


@app.websocket("/v1/live/ws/{session_id}")
async def live_session_ws(websocket: WebSocket, session_id: str) -> None:
    session = session_store.get(session_id)
    if not session:
        await websocket.accept()
        await send_ws_error(websocket, "SESSION_NOT_FOUND", "Session not found")
        await websocket.close(code=1008)
        return

    await websocket.accept()
    session_store.set_status(session_id, "active")
    try:
        live_bridge = LiveBridge()
    except RuntimeError as exc:
        await send_ws_error(websocket, "UPSTREAM_INIT_FAILED", str(exc))
        session_store.set_status(session_id, "closed")
        await websocket.close(code=1011)
        return

    await websocket.send_json({"type": "ready", "session_id": session_id, "protocol_version": "v1"})

    try:
        while True:
            payload = await websocket.receive_json()
            event_type = payload.get("type")

            if event_type == "start":
                try:
                    await live_bridge.handle_start(websocket)
                except RuntimeError as exc:
                    await send_ws_error(websocket, "UPSTREAM_ERROR", str(exc))
            elif event_type == "audio_chunk":
                try:
                    validated_payload = AudioChunkEvent.model_validate(payload).model_dump()
                except ValidationError:
                    await send_ws_error(websocket, "INVALID_AUDIO_CHUNK", "Invalid audio_chunk payload")
                    continue
                try:
                    await live_bridge.handle_audio_chunk(websocket, validated_payload)
                except RuntimeError as exc:
                    await send_ws_error(websocket, "UPSTREAM_ERROR", str(exc))
            elif event_type == "text":
                try:
                    validated_payload = TextEvent.model_validate(payload).model_dump()
                except ValidationError:
                    await send_ws_error(websocket, "INVALID_TEXT", "Invalid text payload")
                    continue
                try:
                    await live_bridge.handle_text(websocket, validated_payload)
                except RuntimeError as exc:
                    await send_ws_error(websocket, "UPSTREAM_ERROR", str(exc))
            elif event_type == "stop":
                try:
                    await live_bridge.handle_stop(websocket)
                except RuntimeError as exc:
                    await send_ws_error(websocket, "UPSTREAM_ERROR", str(exc))
                break
            elif event_type == "close":
                break
            elif event_type == "ping":
                await websocket.send_json({"type": "pong"})
            else:
                await send_ws_error(
                    websocket, "UNSUPPORTED_EVENT_TYPE", f"Unsupported event type: {event_type}"
                )
    except WebSocketDisconnect:
        pass
    finally:
        session_store.set_status(session_id, "closed")
        if websocket.client_state.name != "DISCONNECTED":
            await websocket.close()


@app.exception_handler(Exception)
async def unhandled_exception_handler(_, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"error": str(exc)})
