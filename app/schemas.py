from typing import Literal

from pydantic import BaseModel, Field


class SessionCreateResponse(BaseModel):
    session_id: str = Field(..., description="Server-generated session id")
    protocol_version: str = "v1"


class AudioPayload(BaseModel):
    data: str
    mime_type: str = "audio/pcm;rate=16000"


class AudioChunkEvent(BaseModel):
    type: Literal["audio_chunk"]
    audio: AudioPayload


class TextEvent(BaseModel):
    type: Literal["text"]
    text: str


class PrepareMealLogArgs(BaseModel):
    name: str
    calories: int
    protein: int
    carbs: int
    fat: int
    fiber: int
    type: Literal["breakfast", "lunch", "dinner", "snack"]
