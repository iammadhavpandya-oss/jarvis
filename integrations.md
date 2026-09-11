# Jarvis integrations (stub)

Future hooks — **not implemented in v1**. Track ideas here before coding.

## WhatsApp
- Goal: send/receive messages via WhatsApp Business Cloud API or a local bridge.
- Needs: phone number ID, access token, webhook URL (public HTTPS).
- Suggested module: `app/integrations/whatsapp.py`
- Safety: never auto-forward secrets; confirm before outbound blasts.

## Grok (xAI)
- Goal: optional `LLM_PROVIDER=grok` using xAI Chat Completions API.
- Env: `XAI_API_KEY`, `XAI_MODEL=grok-2-latest` (names may change).
- Suggested: extend `app/llm.py` with `_stream_grok` similar to OpenAI-compatible path.

## Other ideas
- Calendar / Outlook read-only briefings
- Local file search (user-scoped folders only)
- System tray + pywebview native window instead of browser
- Hotkey push-to-talk (global) via `keyboard` / Windows hooks

When adding an integration: document env vars in `.env.example`, add a toggle in `/api/health`, and keep secrets out of git.
