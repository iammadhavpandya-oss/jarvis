"""OpenAI / Anthropic / Ollama chat with optional streaming."""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Optional

import httpx

from .config import MAX_CONTEXT_TURNS, SYSTEM_PROMPT, Settings


class LLMError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def trim_messages(
    messages: list[dict[str, str]],
    max_turns: int = MAX_CONTEXT_TURNS,
) -> list[dict[str, str]]:
    """Keep the last N user/assistant turns (~2 messages each) for small models."""
    if max_turns <= 0 or len(messages) <= max_turns * 2:
        return messages
    return messages[-(max_turns * 2) :]


def build_system_prompt(extra_blocks: Optional[list[str]] = None) -> str:
    parts = [SYSTEM_PROMPT.strip()]
    for block in extra_blocks or []:
        b = (block or "").strip()
        if b:
            parts.append(b)
    return "\n\n".join(parts)


async def stream_chat(
    settings: Settings,
    messages: list[dict[str, str]],
    *,
    system_prompt: Optional[str] = None,
) -> AsyncIterator[str]:
    system = system_prompt or SYSTEM_PROMPT
    messages = trim_messages(messages)
    provider = settings.llm_provider.lower().strip()
    if provider == "anthropic":
        async for chunk in _stream_anthropic(settings, messages, system=system):
            yield chunk
    elif provider == "ollama":
        async for chunk in _stream_ollama(settings, messages, system=system):
            yield chunk
    else:
        async for chunk in _stream_openai(settings, messages, system=system):
            yield chunk


async def _stream_openai_compatible(
    settings: Settings,
    messages: list[dict[str, str]],
    *,
    base_url: str,
    api_key: str,
    model: str,
    provider_label: str,
    system: str,
) -> AsyncIterator[str]:
    """Stream chat completions from an OpenAI-compatible endpoint."""
    url = base_url.rstrip("/") + "/chat/completions"
    payload: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "system", "content": system}, *messages],
        "stream": True,
        "temperature": 0.7,
    }
    headers = {
        "Authorization": f"Bearer {api_key or 'ollama'}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                url,
                headers=headers,
                json=payload,
            ) as resp:
                if resp.status_code >= 400:
                    body = await resp.aread()
                    raise LLMError(
                        f"{provider_label} error {resp.status_code}: "
                        f"{body.decode(errors='replace')[:400]}",
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
    except httpx.ConnectError as e:
        if provider_label.lower() == "ollama":
            raise LLMError(
                "Ollama is not running (connection refused). "
                "On Ramdoot Linux box Ollama is expected; PC install is optional. "
                "Install from https://ollama.com , start it, then run: "
                f"ollama pull {model}",
                status=503,
            ) from e
        raise LLMError(
            f"Could not connect to {provider_label} at {url}: {e}",
            status=503,
        ) from e
    except httpx.HTTPError as e:
        raise LLMError(
            f"{provider_label} request failed: {e}",
            status=502,
        ) from e


async def _stream_ollama(
    settings: Settings,
    messages: list[dict[str, str]],
    *,
    system: str,
) -> AsyncIterator[str]:
    async for chunk in _stream_openai_compatible(
        settings,
        messages,
        base_url=settings.ollama_base_url,
        api_key="ollama",
        model=settings.ollama_model,
        provider_label="Ollama",
        system=system,
    ):
        yield chunk


async def _stream_openai(
    settings: Settings,
    messages: list[dict[str, str]],
    *,
    system: str,
) -> AsyncIterator[str]:
    if not settings.openai_api_key.strip():
        raise LLMError(
            "OPENAI_API_KEY missing. Copy .env.example to .env and add your key.",
            status=401,
        )
    payload: dict[str, Any] = {
        "model": settings.openai_model,
        "messages": [{"role": "system", "content": system}, *messages],
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
    *,
    system: str,
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
        "system": system,
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
