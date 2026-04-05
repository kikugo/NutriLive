from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.config import get_settings
from app.schemas import AudioChunkEvent, SessionCreateResponse, TextEvent
from app.services.live_bridge import live_bridge
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


@app.websocket("/v1/live/ws/{session_id}")
async def live_session_ws(websocket: WebSocket, session_id: str) -> None:
    session = session_store.get(session_id)
    if not session:
        await websocket.accept()
        await websocket.send_json({"type": "error", "message": "Session not found"})
        await websocket.close(code=1008)
        return

    await websocket.accept()
    session_store.set_status(session_id, "active")
    await websocket.send_json({"type": "ready", "session_id": session_id, "protocol_version": "v1"})

    try:
        while True:
            payload = await websocket.receive_json()
            event_type = payload.get("type")

            if event_type == "start":
                await live_bridge.handle_start(websocket)
            elif event_type == "audio_chunk":
                try:
                    validated_payload = AudioChunkEvent.model_validate(payload).model_dump()
                except ValidationError:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": "Invalid audio_chunk payload",
                        }
                    )
                    continue
                await live_bridge.handle_audio_chunk(websocket, validated_payload)
            elif event_type == "text":
                try:
                    validated_payload = TextEvent.model_validate(payload).model_dump()
                except ValidationError:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": "Invalid text payload",
                        }
                    )
                    continue
                await live_bridge.handle_text(websocket, validated_payload)
            elif event_type == "stop":
                await live_bridge.handle_stop(websocket)
                break
            elif event_type == "close":
                break
            else:
                await websocket.send_json(
                    {"type": "error", "message": f"Unsupported event type: {event_type}"}
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
