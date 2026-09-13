# J.A.R.V.I.S — desktop assistant (v1.1)

Dark Iron-Man / HUD chat UI with **voice in** (browser mic), **voice out** (edge-tts), **free web search** (DuckDuckGo / ddgs), **long-term memory** (SQLite), multi-turn streaming chat, and local chat history.

Stack: **Python 3.11+ · FastAPI · static HTML/CSS/JS · edge-tts · Web Speech API · Ollama (local LLM)**

Repo: https://github.com/iammadhavpandya-oss/jarvis

> **Primary runtime:** Ramdoot Linux box at `/workspace/jarvis` (Ollama + uvicorn already there).  
> **Windows PC:** you can run the UI/server there too, but **Ollama on the PC is optional** — Madhav does not need to install Ollama on Windows if the box is serving.

---

## Quick start (Ramdoot Linux box — recommended)

```bash
cd /workspace/jarvis
source .venv/bin/activate   # or: .venv/bin/pip install -r requirements.txt
# Ollama should already be running with llama3.2:3b
uvicorn app.main:app --host 127.0.0.1 --port 8765
```

Open http://127.0.0.1:8765

`.env` defaults:
```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434/v1
OLLAMA_MODEL=llama3.2:3b
HOST=127.0.0.1
PORT=8765
TTS_VOICE=en-IN-PrabhatNeural
MAX_CONTEXT_TURNS=20
```

---

## Quick start (Windows PC — optional)

Assume project path: `C:\Users\Admin\jarvis`.

### 1. Install Python
- Python 3.11+ from https://www.python.org/downloads/ — tick **Add to PATH**
- `py -3 --version`

### 2. Ollama on PC — **optional**
Only needed if you want a **local** LLM on Windows. Otherwise use a cloud provider in `.env`, or keep using the Ramdoot box.

If you do install: https://ollama.com then `ollama pull llama3.2:3b`

### 3. Get code
```bat
cd C:\Users\Admin
git clone https://github.com/iammadhavpandya-oss/jarvis.git
cd jarvis
```

### 4. Create `.env`
```bat
copy .env.example .env
notepad .env
```

**Ollama (if installed on PC):**
```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434/v1
OLLAMA_MODEL=llama3.2:3b
```

**Or OpenAI / Anthropic** (paid cloud — no local Ollama):
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

### 5. Run
Double-click **`start.bat`** or:
```bat
cd C:\Users\Admin\jarvis
start.bat
```

---

## Long-term memory

Jarvis stores durable facts in `data/memory.db` and injects the latest ~30 into every chat as a **LONG-TERM MEMORY** block.

### Chat phrases (auto-save)
Say any of these, then the fact:
- `yaad rakh …` / `yaad rakho …`
- `remember …` / `remember this …`
- `save this …`
- `memory mein daal …`

Example: *“yaad rakh mera Jetking campus Vasai hai”* → saved; Jarvis confirms briefly.

### UI
- Sidebar **🧠 Memory** button shows the count
- Open panel → list / add (optional key) / delete
- Also: `GET|POST /api/memory`, `DELETE /api/memory/{id}`

Memories persist across chats and restarts (same `data/` folder).

---

## Features (v1.1)
| Feature | How |
|--------|-----|
| HUD chat UI | Cyan/amber glass theme |
| Streaming chat | SSE from FastAPI |
| **Ollama (free local)** | OpenAI-compatible `/v1` — default `llama3.2:3b`, last **20 turns** trimmed |
| OpenAI / Anthropic | Optional paid via `.env` |
| Chat history | SQLite `data/chat_history.db` |
| **Long-term memory** | SQLite `data/memory.db` — phrases + UI panel |
| TTS | `edge-tts` → `/api/tts` |
| STT | Browser Web Speech API |
| Mute / Web toggles | LocalStorage |
| **Web search (free)** | DuckDuckGo via `ddgs` — 🌐 Web or auto keywords |

Health: `GET /api/health` includes `memory_count`.

---

## Project layout
```
jarvis/
  app/
    main.py       # FastAPI routes
    config.py     # env + Jarvis system prompt
    llm.py        # Ollama / OpenAI / Anthropic streaming
    history.py    # SQLite conversations
    memory.py     # SQLite long-term memory
    tts.py        # edge-tts
    websearch.py  # free DuckDuckGo search (ddgs)
  static/
    index.html
    css/style.css
    js/app.js
  data/           # chat_history.db + memory.db (runtime)
  .env.example
  requirements.txt
  start.bat
  README.md
```

---

## Persona
Respectful **aap / ji**; short Jarvis tone; Jetking/study vs personal hats; uses LONG-TERM MEMORY and web search when available. No help with crime, phishing, or unauthorized hacking.

---

## Troubleshooting
| Problem | Fix |
|--------|-----|
| `Ollama is not running` | On Ramdoot: ensure `ollama serve`. On PC: install optional, or switch to openai/anthropic in `.env` |
| Model slow | Keep `llama3.2:3b`; context already trimmed to 20 turns |
| Port in use | Change `PORT` in `.env` |
| Mic | Chrome/Edge + allow mic for the page |
| TTS silent | Unmute 🔊; edge-tts needs internet |
| Web search empty | Needs internet; retry / rephrase |
| Memory not sticking | Check `data/memory.db` exists; sidebar count should rise |

---

Made for Madhav. Systems online.
