"""Jarvis FastAPI backend + static HUD."""
from __future__ import annotations

import json
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import history, memory
from .config import ROOT, get_settings
from .llm import LLMError, build_system_prompt, stream_chat
from .tts import list_voices, synthesize
from .websearch import format_search_context, search_web, should_auto_search

STATIC = ROOT / "static"

app = FastAPI(title="Jarvis", version="1.1.0")


@app.on_event("startup")
async def _startup() -> None:
    await history.init_db()
    await memory.init_db()


class ChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    message: str = Field(..., min_length=1)
    stream: bool = True
    web_search: bool = False


class NewConvResponse(BaseModel):
    id: str
    title: str


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)
    voice: Optional[str] = None


class MemoryCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)
    key: Optional[str] = Field(None, max_length=120)


@app.get("/api/health")
async def health():
    s = get_settings()
    mem_count = await memory.count_memories()
    return {
        "ok": True,
        "provider": s.llm_provider,
        "model": s.active_model,
        "has_llm_key": s.has_llm_key,
        "tts_voice": s.tts_voice,
        "whisper_stt": s.whisper_stt,
        "web_search": True,
        "memory_count": mem_count,
    }


@app.get("/api/memory")
async def api_list_memory(limit: int = Query(50, ge=1, le=200)):
    items = await memory.list_memories(limit=limit)
    return {"count": await memory.count_memories(), "items": items}


@app.post("/api/memory")
async def api_add_memory(body: MemoryCreate):
    try:
        item = await memory.add_memory(
            body.content,
            key=body.key,
            source="ui",
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return item


@app.delete("/api/memory/{memory_id}")
async def api_delete_memory(memory_id: str):
    ok = await memory.delete_memory(memory_id)
    if not ok:
        raise HTTPException(404, "Memory not found")
    return {"deleted": True}


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


async def _maybe_search(text: str, web_search: bool) -> tuple[bool, str, list]:
    """Decide whether to search; return (do_search, query, results)."""
    do_search = bool(web_search) or should_auto_search(text)
    if not do_search:
        return False, text, []
    results = await search_web(text, max_results=5)
    return True, text, results


def _inject_search_context(
    llm_messages: list[dict[str, str]],
    query: str,
    results: list,
) -> list[dict[str, str]]:
    """Inject SEARCH RESULTS as a user context message before the last user turn."""
    context = format_search_context(results, query)
    injected = list(llm_messages)
    injected.append(
        {
            "role": "user",
            "content": (
                f"{context}\n\n"
                "Use the SEARCH RESULTS above to answer the user's latest question. "
                "Cite briefly when you rely on a result."
            ),
        }
    )
    return injected


async def _prepare_chat_context(text: str, web_search: bool, prior: list) -> tuple:
    """Load memories, auto-save if asked, build system prompt + llm messages."""
    saved_memory = None
    fact = memory.detect_remember_request(text)
    if fact:
        saved_memory = await memory.add_memory(fact, source="chat")

    recent = await memory.list_memories(limit=30)
    mem_block = memory.format_memory_block(recent)
    extra = [mem_block] if mem_block else []
    if saved_memory:
        extra.append(
            "NOTE: Madhav just asked you to remember something. "
            f'It was saved: "{saved_memory["content"]}". '
            "Confirm briefly in one short line, then continue if needed."
        )
    system = build_system_prompt(extra)

    llm_messages = [{"role": m["role"], "content": m["content"]} for m in prior]
    do_search, search_query, search_results = await _maybe_search(text, web_search)
    if do_search:
        llm_messages = _inject_search_context(llm_messages, search_query, search_results)

    return system, llm_messages, do_search, search_query, search_results, saved_memory


@app.post("/api/chat")
async def api_chat(body: ChatRequest):
    s = get_settings()
    if not s.has_llm_key:
        provider = s.llm_provider.lower().strip()
        if provider == "ollama":
            key_hint = "Start Ollama and set OLLAMA_MODEL in .env (no cloud key needed)."
        elif provider == "anthropic":
            key_hint = "ANTHROPIC_API_KEY is missing. Copy .env.example to .env and set your key."
        else:
            key_hint = "OPENAI_API_KEY is missing. Copy .env.example to .env and set your key."
        raise HTTPException(
            status_code=401,
            detail=f"{key_hint} Current LLM_PROVIDER={s.llm_provider}.",
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

    (
        system,
        llm_messages,
        do_search,
        search_query,
        search_results,
        saved_memory,
    ) = await _prepare_chat_context(text, body.web_search, prior)

    if not body.stream:
        chunks: list[str] = []
        try:
            async for c in stream_chat(s, llm_messages, system_prompt=system):
                chunks.append(c)
        except LLMError as e:
            raise HTTPException(e.status, str(e)) from e
        full = "".join(chunks)
        await history.add_message(conv_id, "assistant", full)
        return {
            "conversation_id": conv_id,
            "reply": full,
            "web_search": do_search,
            "search_count": len(search_results) if do_search else 0,
            "memory_saved": bool(saved_memory),
            "memory": saved_memory,
        }

    async def event_gen():
        meta = {"type": "meta", "conversation_id": conv_id}
        if saved_memory:
            meta["memory_saved"] = True
            meta["memory_id"] = saved_memory["id"]
        yield f"data: {json.dumps(meta)}\n\n"
        if do_search:
            yield f"data: {json.dumps({'type': 'search', 'query': search_query, 'count': len(search_results)})}\n\n"
        parts: list[str] = []
        try:
            async for token in stream_chat(s, llm_messages, system_prompt=system):
                parts.append(token)
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
            full = "".join(parts)
            await history.add_message(conv_id, "assistant", full)
            yield f"data: {json.dumps({'type': 'done', 'conversation_id': conv_id, 'memory_saved': bool(saved_memory)})}\n\n"
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
