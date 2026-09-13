"""Long-term durable memory (SQLite) — facts across chats."""
from __future__ import annotations

import re
import time
import uuid
from typing import Any, Optional

import aiosqlite

from .config import MEMORY_DB_PATH

# Phrases that trigger auto-save from chat (Hinglish + English)
_REMEMBER_TRIGGERS = re.compile(
    r"(?is)"
    r"(?:"
    r"yaad\s*rakh(?:o|na|iye)?"
    r"|remember(?:\s+this|\s+that)?"
    r"|save\s+this"
    r"|memory\s+mein\s+daal(?:o|na|iye)?"
    r")"
    r"\s*[:\-–,]?\s*"
    r"(?:ki\s+|that\s+|this\s+)?"
    r"(.+)",
)


async def init_db() -> None:
    async with aiosqlite.connect(MEMORY_DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                key TEXT,
                content TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'chat',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
            """
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_updated ON memories(updated_at DESC)"
        )
        await db.commit()


async def count_memories() -> int:
    async with aiosqlite.connect(MEMORY_DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM memories")
        row = await cur.fetchone()
        return int(row[0]) if row else 0


async def list_memories(limit: int = 30) -> list[dict[str, Any]]:
    """Recent / top by updated_at."""
    async with aiosqlite.connect(MEMORY_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """
            SELECT id, key, content, source, created_at, updated_at
            FROM memories
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def add_memory(
    content: str,
    *,
    key: Optional[str] = None,
    source: str = "api",
) -> dict[str, Any]:
    content = (content or "").strip()
    if not content:
        raise ValueError("Memory content is empty")
    key_clean = (key or "").strip() or None
    mid = str(uuid.uuid4())
    now = time.time()

    async with aiosqlite.connect(MEMORY_DB_PATH) as db:
        # Upsert by key when key is provided
        if key_clean:
            cur = await db.execute(
                "SELECT id FROM memories WHERE key = ? LIMIT 1", (key_clean,)
            )
            existing = await cur.fetchone()
            if existing:
                mid = existing[0]
                await db.execute(
                    """
                    UPDATE memories
                    SET content = ?, source = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (content, source, now, mid),
                )
                await db.commit()
                return {
                    "id": mid,
                    "key": key_clean,
                    "content": content,
                    "source": source,
                    "created_at": now,
                    "updated_at": now,
                    "updated": True,
                }

        await db.execute(
            """
            INSERT INTO memories (id, key, content, source, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (mid, key_clean, content, source, now, now),
        )
        await db.commit()

    return {
        "id": mid,
        "key": key_clean,
        "content": content,
        "source": source,
        "created_at": now,
        "updated_at": now,
        "updated": False,
    }


async def delete_memory(memory_id: str) -> bool:
    async with aiosqlite.connect(MEMORY_DB_PATH) as db:
        cur = await db.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        await db.commit()
        return cur.rowcount > 0


def detect_remember_request(text: str) -> Optional[str]:
    """
    If the user asks to remember something, return the fact to store.
    Returns None when no remember trigger is present.
    """
    if not text or not text.strip():
        return None
    m = _REMEMBER_TRIGGERS.search(text.strip())
    if not m:
        return None
    fact = (m.group(1) or "").strip().strip("\"'“”‘’")
    # Drop trailing politeness fluff
    fact = re.sub(r"[.!\s]+$", "", fact).strip()
    if len(fact) < 2:
        return None
    return fact[:2000]


def format_memory_block(memories: list[dict[str, Any]]) -> str:
    """Build LONG-TERM MEMORY preamble for the system prompt."""
    if not memories:
        return ""
    lines: list[str] = []
    for m in memories:
        key = (m.get("key") or "").strip()
        content = (m.get("content") or "").strip()
        if not content:
            continue
        if key:
            lines.append(f"- [{key}] {content}")
        else:
            lines.append(f"- {content}")
    if not lines:
        return ""
    return "LONG-TERM MEMORY (durable facts about Madhav — use when relevant):\n" + "\n".join(
        lines
    )
