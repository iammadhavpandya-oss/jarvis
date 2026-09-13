"""Free online web search via DuckDuckGo (ddgs) — no paid API keys."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


async def search_web(query: str, max_results: int = 5) -> list[dict[str, str]]:
    """Search the web and return [{title, href, body}, ...].

    Uses the free ``ddgs`` package (DuckDuckGo). Runs the sync client in a
    thread so the FastAPI event loop is not blocked.
    """
    q = (query or "").strip()
    if not q:
        return []
    n = max(1, min(int(max_results or 5), 10))

    def _run() -> list[dict[str, str]]:
        try:
            from ddgs import DDGS
        except ImportError:  # pragma: no cover — older package name
            from duckduckgo_search import DDGS  # type: ignore

        out: list[dict[str, str]] = []
        try:
            raw: list[dict[str, Any]] = list(DDGS().text(q, max_results=n))
        except Exception as e:
            logger.warning("web search failed for %r: %s", q, e)
            return []
        for r in raw:
            out.append(
                {
                    "title": str(r.get("title") or "").strip(),
                    "href": str(r.get("href") or r.get("link") or "").strip(),
                    "body": str(r.get("body") or r.get("snippet") or "").strip(),
                }
            )
        return out

    return await asyncio.to_thread(_run)


def format_search_context(results: list[dict[str, str]], query: str) -> str:
    """Build a SEARCH RESULTS block to inject into the LLM message list."""
    if not results:
        return (
            f"SEARCH RESULTS for query: {query}\n"
            "(No results returned. Answer from general knowledge and say "
            "you could not fetch live web results.)"
        )
    lines = [f"SEARCH RESULTS for query: {query}", ""]
    for i, r in enumerate(results, 1):
        lines.append(f"[{i}] {r.get('title') or '(no title)'}")
        if r.get("href"):
            lines.append(f"    URL: {r['href']}")
        if r.get("body"):
            lines.append(f"    {r['body']}")
        lines.append("")
    return "\n".join(lines).rstrip()


# Keywords that auto-enable web search even if the UI toggle is off.
_SEARCH_KEYWORDS = (
    "search",
    "google",
    "latest",
    "news",
    "today",
    "current",
    "search karo",
    "online",
)


def should_auto_search(message: str) -> bool:
    """True if the user message looks like it wants live/web info."""
    lower = (message or "").lower()
    return any(k in lower for k in _SEARCH_KEYWORDS)
