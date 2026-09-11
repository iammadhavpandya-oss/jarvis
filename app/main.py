"""Jarvis FastAPI backend + static HUD."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import history
from .config import ROOT, get_settings
from .llm import LLMError, stream_chat
from .tts import list_voices, synthesize

STATIC = ROOT / "static"

app = FastAPI(title="Jarvis", version="1.0.0")


@app.on_event("startup")
async def _startup() -> None:
    await history.init_db()


class ChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    message: str = Field(..., min_length=1)
    stream: bool = True


class NewConvResponse(BaseModel):
    id: str
    title: str


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)
    voice: Optional[str] = None


@app.get("/api/health")
async def health():
    s = get_settings()
    return {
        "ok": True,
        "provider": s.llm_provider,
        "model": s.active_model,
        "has_llm_key": s.has_llm_key,
        "tts_voice": s.tts_voice,
        "whisper_stt": s.whisper_stt,
    }


@app.get("/api/conversations")
async def api_list_conversations():
    return await history.list_conversations()


@app.post("/api/conversations")
async def api_create_conversation():
    return await history.create_conversation()


@app.delete("/api/conversations/{conversation_id}")
async def api_delete_conversation(conversation_id: str):
    ok = await history.delete_conversation(conversation_id)
    if not ok:
        raise HTTPException(404, "Conversation not found")
    return {"deleted": True}


@app.get("/api/conversations/{conversation_id}/messages")
async def api_get_messages(conversation_id: str):
    return await history.get_messages(conversation_id)


@app.post("/api/chat")
async def api_chat(body: ChatRequest):
    s = get_settings()
    if not s.has_llm_key:
        provider = s.llm_provider.lower().strip()
        key_name = "ANTHROPIC_API_KEY" if provider == "anthropic" else "OPENAI_API_KEY"
        raise HTTPException(
            status_code=401,
            detail=(
                f"{key_name} is missing. "
                f"Create C:\\Users\\Admin\\jarvis\\.env from .env.example and set your key. "
                f"Current LLM_PROVIDER={s.llm_provider}."
            ),
        )

    text = body.message.strip()
    if not text:
        raise HTTPException(400, "Empty message")

    conv_id = body.conversation_id
    if not conv_id:
        conv = await history.create_conversation()
        conv_id = conv["id"]

    await history.add_message(conv_id, "user", text)
    prior = await history.get_messages(conv_id)
    llm_messages = [{"role": m["role"], "content": m["content"]} for m in prior]

    if not body.stream:
        # Non-streaming: collect full reply
        chunks: list[str] = []
        try:
            async for c in stream_chat(s, llm_messages):
                chunks.append(c)
        except LLMError as e:
            raise HTTPException(e.status, str(e)) from e
        full = "".join(chunks)
        await history.add_message(conv_id, "assistant", full)
        return {"conversation_id": conv_id, "reply": full}

    async def event_gen():
        yield f"data: {json.dumps({'type': 'meta', 'conversation_id': conv_id})}\n\n"
        parts: list[str] = []
        try:
            async for token in stream_chat(s, llm_messages):
                parts.append(token)
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
            full = "".join(parts)
            await history.add_message(conv_id, "assistant", full)
            yield f"data: {json.dumps({'type': 'done', 'conversation_id': conv_id})}\n\n"
        except LLMError as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'Unexpected: {e}'})}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/tts")
async def api_tts(body: TTSRequest):
    s = get_settings()
    voice = body.voice or s.tts_voice
    try:
        audio = await synthesize(body.text, voice)
    except Exception as e:
        raise HTTPException(500, f"TTS failed: {e}") from e
    return Response(content=audio, media_type="audio/mpeg")


@app.get("/api/tts/voices")
async def api_voices(locale: Optional[str] = Query(None)):
    try:
        return await list_voices(locale)
    except Exception as e:
        raise HTTPException(500, f"Could not list voices: {e}") from e


@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")


def run() -> None:
    import uvicorn

    s = get_settings()
    uvicorn.run(
        "app.main:app",
        host=s.host,
        port=s.port,
        reload=False,
    )


if __name__ == "__main__":
    run()
