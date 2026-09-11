"""edge-tts helpers."""
from __future__ import annotations

import io
from typing import Optional

import edge_tts


async def synthesize(text: str, voice: str) -> bytes:
    communicate = edge_tts.Communicate(text, voice)
    buf = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])
    return buf.getvalue()


async def list_voices(locale_filter: Optional[str] = None) -> list[dict]:
    voices = await edge_tts.list_voices()
    if locale_filter:
        lf = locale_filter.lower()
        voices = [v for v in voices if lf in v.get("Locale", "").lower()]
    return [
        {
            "short_name": v["ShortName"],
            "gender": v.get("Gender"),
            "locale": v.get("Locale"),
            "friendly": v.get("FriendlyName"),
        }
        for v in voices
    ]
