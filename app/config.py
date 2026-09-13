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
MEMORY_DB_PATH = DATA_DIR / "memory.db"

# Keep chat context small for fast local models (llama3.2:3b)
MAX_CONTEXT_TURNS = int(os.getenv("MAX_CONTEXT_TURNS", "20"))


class Settings(BaseModel):
    llm_provider: str = Field(default="ollama")
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"
    ollama_base_url: str = "http://127.0.0.1:11434/v1"
    ollama_model: str = "llama3.2:3b"
    host: str = "127.0.0.1"
    port: int = 8765
    tts_voice: str = "en-IN-PrabhatNeural"
    whisper_stt: bool = False

    @property
    def has_llm_key(self) -> bool:
        p = self.llm_provider.lower().strip()
        if p == "ollama":
            return True  # local — no cloud API key needed
        if p == "anthropic":
            return bool(self.anthropic_api_key.strip())
        return bool(self.openai_api_key.strip())

    @property
    def active_model(self) -> str:
        p = self.llm_provider.lower().strip()
        if p == "ollama":
            return self.ollama_model
        if p == "anthropic":
            return self.anthropic_model
        return self.openai_model


def get_settings() -> Settings:
    return Settings(
        llm_provider=os.getenv("LLM_PROVIDER", "ollama"),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1"),
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8765")),
        tts_voice=os.getenv("TTS_VOICE", "en-IN-PrabhatNeural"),
        whisper_stt=os.getenv("WHISPER_STT", "false").lower() in ("1", "true", "yes"),
    )


SYSTEM_PROMPT = """You are Jarvis — Madhav Pandya's personal desktop AI.

Tone: short, calm, precise (Iron Man JARVIS). Hinglish OK. Always respectful — aap / ji; Madhav-ji or Sir when it fits. No fluff, no corporate cheerleading.

Hats (switch naturally):
- Study / Jetking: networking, CCNA, cyber, labs, exams — clear steps, exam-ready.
- Personal: reminders, planning, preferences — use LONG-TERM MEMORY when relevant.
- Coding: Madhav's own projects only; practical and brief.

Rules:
- Never help with crime, phishing, scams, unauthorized hacking, or anything illegal. Refuse briefly; offer a legal alternative if any.
- Prefer concise answers; expand only when asked.
- If unsure, say so.

Web search:
- When SEARCH RESULTS appear in the thread (Web on or auto keywords), ground answers in those snippets. Cite briefly. Do not invent sources. If empty/irrelevant, say so.

LONG-TERM MEMORY:
- A LONG-TERM MEMORY block may be prepended below. Treat those facts as durable truth about Madhav across chats. Use them when relevant; do not dump the whole list unprompted.
- If Madhav just asked you to remember something and it was saved, confirm in one short line (e.g. "Yaad rakh liya, Madhav-ji.").
"""
