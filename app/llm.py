"""OpenAI / Anthropic chat with optional streaming."""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx

from .config import SYSTEM_PROMPT, Settings


class LLMError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


async def stream_chat(
    settings: Settings,
    messages: list[dict[str, str]],
) -> AsyncIterator[str]:
    provider = settings.llm_provider.lower().strip()
    if provider == "anthropic":
        async for chunk in _stream_anthropic(settings, messages):
            yield chunk
    else:
        async for chunk in _stream_openai(settings, messages):
            yield chunk


async def _stream_openai(
    settings: Settings,
    messages: list[dict[str, str]],
) -> AsyncIterator[str]:
    if not settings.openai_api_key.strip():
        raise LLMError(
            "OPENAI_API_KEY missing. Copy .env.example to .env and add your key.",
            status=401,
        )
    payload: dict[str, Any] = {
        "model": settings.openai_model,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, *messages],
        "stream": True,
        "temperature": 0.7,
    }
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST",
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
        ) as resp:
            if resp.status_code >= 400:
                body = await resp.aread()
                raise LLMError(
                    f"OpenAI error {resp.status_code}: {body.decode(errors='replace')[:400]}",
                    status=resp.status_code,
                )
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:].strip()
                if data == "[DONE]":
                    break
                try:
                    import json

                    obj = json.loads(data)
                    delta = obj["choices"][0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        yield content
                except Exception:
                    continue


async def _stream_anthropic(
    settings: Settings,
    messages: list[dict[str, str]],
) -> AsyncIterator[str]:
    if not settings.anthropic_api_key.strip():
        raise LLMError(
            "ANTHROPIC_API_KEY missing. Copy .env.example to .env and add your key.",
            status=401,
        )
    # Anthropic wants system separate; merge consecutive same-role if needed
    anth_messages = []
    for m in messages:
        role = m["role"]
        if role not in ("user", "assistant"):
            continue
        if anth_messages and anth_messages[-1]["role"] == role:
            anth_messages[-1]["content"] += "\n" + m["content"]
        else:
            anth_messages.append({"role": role, "content": m["content"]})
    if not anth_messages or anth_messages[0]["role"] != "user":
        anth_messages.insert(0, {"role": "user", "content": "Hello."})

    payload = {
        "model": settings.anthropic_model,
        "max_tokens": 2048,
        "system": SYSTEM_PROMPT,
        "messages": anth_messages,
        "stream": True,
        "temperature": 0.7,
    }
    headers = {
        "x-api-key": settings.anthropic_api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST",
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
        ) as resp:
            if resp.status_code >= 400:
                body = await resp.aread()
                raise LLMError(
                    f"Anthropic error {resp.status_code}: {body.decode(errors='replace')[:400]}",
                    status=resp.status_code,
                )
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:].strip()
                if not data:
                    continue
                try:
                    import json

                    obj = json.loads(data)
                    if obj.get("type") == "content_block_delta":
                        delta = obj.get("delta", {})
                        if delta.get("type") == "text_delta":
                            text = delta.get("text")
                            if text:
                                yield text
                except Exception:
                    continue
