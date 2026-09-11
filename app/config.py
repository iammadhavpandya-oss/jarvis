"""Load settings from environment / .env."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "chat_history.db"


class Settings(BaseModel):
    llm_provider: str = Field(default="openai")
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"
    host: str = "127.0.0.1"
    port: int = 8765
    tts_voice: str = "en-IN-PrabhatNeural"
    whisper_stt: bool = False

    @property
    def has_llm_key(self) -> bool:
        p = self.llm_provider.lower().strip()
        if p == "anthropic":
            return bool(self.anthropic_api_key.strip())
        return bool(self.openai_api_key.strip())

    @property
    def active_model(self) -> str:
        if self.llm_provider.lower().strip() == "anthropic":
            return self.anthropic_model
        return self.openai_model


def get_settings() -> Settings:
    return Settings(
        llm_provider=os.getenv("LLM_PROVIDER", "openai"),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8765")),
        tts_voice=os.getenv("TTS_VOICE", "en-IN-PrabhatNeural"),
        whisper_stt=os.getenv("WHISPER_STT", "false").lower() in ("1", "true", "yes"),
    )


SYSTEM_PROMPT = """You are Jarvis — Madhav's personal desktop AI assistant.

Persona:
- Dry, competent, slightly witty. Short answers preferred; expand only when asked.
- Hinglish is fine when Madhav uses it. Be respectful: use aap / ji naturally.
- Sound like Iron Man's JARVIS: calm, precise, no fluff, no corporate cheerleading.
- Address Madhav as Sir / Madhav-ji when it fits; never condescending.

Rules:
- Never help with crime, phishing, scams, hacking unauthorized systems, or anything illegal.
- If asked for something harmful, refuse briefly and offer a legal alternative if any.
- You may discuss general tech, coding help for Madhav's own projects, productivity, and learning.
- Keep responses concise unless the topic needs depth.
- If you don't know something, say so clearly.
"""
