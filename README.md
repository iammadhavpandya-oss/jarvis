# J.A.R.V.I.S — Windows desktop assistant (v1)

Dark Iron-Man / HUD chat UI with **voice in** (browser mic), **voice out** (edge-tts), multi-turn streaming chat, and local SQLite history.

Stack: **Python 3.11+ · FastAPI · static HTML/CSS/JS · edge-tts · Web Speech API**

Repo: https://github.com/iammadhavpandya-oss/jarvis

---

## Quick start (Madhav — Windows)

Assume project path: `C:\Users\Admin\jarvis` (clone or copy here).

### 1. Install Python
- Download **Python 3.11+** from https://www.python.org/downloads/
- Installer mein **"Add python.exe to PATH"** tick karo
- Verify in Command Prompt:
  ```bat
  py -3 --version
  ```

### 2. Get code
```bat
cd C:\Users\Admin
git clone https://github.com/iammadhavpandya-oss/jarvis.git
cd jarvis
```
(Or unzip / copy the folder to `C:\Users\Admin\jarvis`.)

### 3. Create `.env`
```bat
copy .env.example .env
notepad .env
```

Set **one** provider:

**OpenAI**
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

**Anthropic**
```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-20250514
```

Optional TTS voice (examples):
```env
TTS_VOICE=en-IN-PrabhatNeural
# or en-US-GuyNeural / hi-IN-MadhurNeural / en-IN-NeerjaNeural
```

> Kabhi bhi real keys git mein mat daalo. `.env` is local-only.

### 4. Run (easiest)
Double-click **`start.bat`**

Ya Command Prompt se:
```bat
cd C:\Users\Admin\jarvis
start.bat
```

Script will:
1. Create `.venv` if needed  
2. `pip install -r requirements.txt`  
3. Open http://127.0.0.1:8765  
4. Start the API server  

Manual alternative:
```bat
cd C:\Users\Admin\jarvis
py -3 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8765
```
Then open Chrome/Edge: http://127.0.0.1:8765

### 5. Test mic + TTS
1. Sidebar pe status **LLM ready** (green) hona chahiye — warna `.env` key check karo  
2. Type a message → Jarvis streams reply  
3. **🔊 TTS** button se voice on/off (mute toggle)  
4. **🎙️ Mic** — Chrome/Edge allow microphone; speak (Web Speech API, free, no download)  
5. Agar API key missing ho → UI mein clear red error / toast dikhega  

**Mic note:** Web Speech API best on **Chrome or Edge**. Firefox may not support it well — typing always works.

---

## Features (v1)
| Feature | How |
|--------|-----|
| HUD chat UI | Cyan/amber glass theme |
| Streaming chat | SSE from FastAPI |
| OpenAI / Anthropic | Via `.env` |
| History | SQLite in `data/chat_history.db` |
| TTS | `edge-tts` → `/api/tts` |
| STT | Browser Web Speech API |
| Mute | LocalStorage toggle |

Optional later: Whisper STT if you set `WHISPER_STT=true` and wire OpenAI Whisper — see `.env.example` (frontend still uses Web Speech by default).

---

## Project layout
```
jarvis/
  app/
    main.py       # FastAPI routes
    config.py     # env + Jarvis system prompt
    llm.py        # OpenAI / Anthropic streaming
    history.py    # SQLite conversations
    tts.py        # edge-tts
  static/
    index.html
    css/style.css
    js/app.js
  data/           # created at runtime (SQLite)
  .env.example
  requirements.txt
  start.bat
  integrations.md
  README.md
```

---

## Persona
Jarvis is dry, competent, short; Hinglish OK; respectful **aap / ji**. No help with crime, phishing, or unauthorized hacking.

---

## Troubleshooting
| Problem | Fix |
|--------|-----|
| `API key missing` in UI | Edit `.env`, restart `start.bat` |
| Port in use | Change `PORT=8766` in `.env` and open that URL |
| Mic not working | Use Chrome/Edge; allow mic permission for `http://127.0.0.1:8765` |
| TTS silent | Unmute 🔊; check internet (edge-tts uses Microsoft voices online) |
| `pip` / venv errors | Reinstall Python with PATH; run CMD as normal user from `C:\Users\Admin\jarvis` |

---

## Push to GitHub
```bat
cd C:\Users\Admin\jarvis
git init
git add .
git commit -m "v1: Jarvis HUD assistant"
git branch -M main
git remote add origin https://github.com/iammadhavpandya-oss/jarvis.git
git push -u origin main
```
Ensure `.gitignore` excludes `.env`, `.venv/`, and `data/*.db`.

---

Made for Madhav. Systems online.
