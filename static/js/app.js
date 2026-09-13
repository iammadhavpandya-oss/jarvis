(() => {
  const $ = (sel) => document.querySelector(sel);

  const els = {
    messages: $("#messages"),
    input: $("#input"),
    send: $("#btn-send"),
    newChat: $("#btn-new"),
    convList: $("#conv-list"),
    web: $("#btn-web"),
    mute: $("#btn-mute"),
    voice: $("#btn-voice"),
    status: $("#status-pill"),
    model: $("#model-label"),
    title: $("#chat-title"),
    listening: $("#listening-banner"),
    searching: $("#searching-banner"),
    toast: $("#toast"),
    memoryBtn: $("#btn-memory"),
    memoryCount: $("#memory-count"),
    memoryPanel: $("#memory-panel"),
    memoryClose: $("#btn-memory-close"),
    memoryList: $("#memory-list"),
    memoryKey: $("#memory-key"),
    memoryContent: $("#memory-content"),
    memoryAdd: $("#btn-memory-add"),
  };

  const state = {
    conversationId: null,
    streaming: false,
    ttsMuted: localStorage.getItem("jarvis_tts_muted") === "1",
    webSearch: localStorage.getItem("jarvis_web_search") === "1",
    recognition: null,
    listening: false,
    memoryCount: 0,
  };

  function toast(msg, ms = 4500) {
    els.toast.textContent = msg;
    els.toast.classList.remove("hidden");
    clearTimeout(toast._t);
    toast._t = setTimeout(() => els.toast.classList.add("hidden"), ms);
  }

  function setMuteUI() {
    els.mute.textContent = state.ttsMuted ? "🔇 TTS muted" : "🔊 TTS";
    els.mute.classList.toggle("muted-on", state.ttsMuted);
  }

  function setWebUI() {
    els.web.textContent = state.webSearch ? "🌐 Web on" : "🌐 Web";
    els.web.classList.toggle("web-on", state.webSearch);
    els.web.title = state.webSearch
      ? "Web search ON (DuckDuckGo, free)"
      : "Web search OFF — still auto-runs for search/latest/news keywords";
  }

  function setMemoryCount(n) {
    state.memoryCount = Number(n) || 0;
    if (els.memoryCount) els.memoryCount.textContent = String(state.memoryCount);
  }

  function setSearching(on, detail) {
    if (!els.searching) return;
    if (on) {
      els.searching.textContent = detail
        ? `Searching… ${detail}`
        : "Searching the web…";
      els.searching.classList.remove("hidden");
    } else {
      els.searching.classList.add("hidden");
    }
  }

  function autoGrow() {
    els.input.style.height = "auto";
    els.input.style.height = Math.min(els.input.scrollHeight, 160) + "px";
  }

  function clearMessages() {
    els.messages.innerHTML = "";
  }

  function showEmpty() {
    clearMessages();
    const d = document.createElement("div");
    d.className = "empty";
    d.innerHTML = `<h2>Systems online</h2><p>Madhav-ji, aap command dijiye.<br/>Mic ya type — Jarvis ready hai. Memory ke liye “yaad rakh …”.</p>`;
    els.messages.appendChild(d);
  }

  function appendMsg(role, content, { streaming = false, error = false } = {}) {
    const empty = els.messages.querySelector(".empty");
    if (empty) empty.remove();

    const div = document.createElement("div");
    div.className = `msg ${error ? "error" : role}`;
    const roleLabel = error ? "System" : role === "user" ? "Madhav" : "Jarvis";
    div.innerHTML = `<div class="role">${roleLabel}</div><div class="body ${streaming ? "cursor-blink" : ""}"></div>`;
    div.querySelector(".body").textContent = content;
    els.messages.appendChild(div);
    els.messages.scrollTop = els.messages.scrollHeight;
    return div;
  }

  async function refreshHealth() {
    try {
      const r = await fetch("/api/health");
      const h = await r.json();
      if (h.has_llm_key) {
        els.status.textContent = "LLM ready";
        els.status.className = "pill ok";
      } else {
        els.status.textContent = "API key missing";
        els.status.className = "pill err";
      }
      els.model.textContent = `${h.provider} · ${h.model}`;
      if (typeof h.memory_count === "number") setMemoryCount(h.memory_count);
      return h;
    } catch (e) {
      els.status.textContent = "Offline";
      els.status.className = "pill err";
      return null;
    }
  }

  async function loadMemories() {
    const r = await fetch("/api/memory?limit=50");
    const data = await r.json();
    setMemoryCount(data.count ?? (data.items || []).length);
    els.memoryList.innerHTML = "";
    const items = data.items || [];
    if (!items.length) {
      const empty = document.createElement("div");
      empty.className = "memory-empty";
      empty.textContent = "No memories yet. Add one above or say “yaad rakh …” in chat.";
      els.memoryList.appendChild(empty);
      return;
    }
    for (const m of items) {
      const row = document.createElement("div");
      row.className = "memory-item";
      row.innerHTML = `<div class="body"></div><button type="button" class="del" title="Delete">✕</button>`;
      const body = row.querySelector(".body");
      if (m.key) {
        const k = document.createElement("div");
        k.className = "key";
        k.textContent = m.key;
        body.appendChild(k);
      }
      const c = document.createElement("div");
      c.className = "content";
      c.textContent = m.content;
      body.appendChild(c);
      row.querySelector(".del").addEventListener("click", async () => {
        await fetch(`/api/memory/${m.id}`, { method: "DELETE" });
        await loadMemories();
        toast("Memory deleted");
      });
      els.memoryList.appendChild(row);
    }
  }

  function openMemoryPanel() {
    els.memoryPanel.classList.remove("hidden");
    loadMemories();
    els.memoryContent.focus();
  }

  function closeMemoryPanel() {
    els.memoryPanel.classList.add("hidden");
  }

  async function addMemoryFromUI() {
    const content = (els.memoryContent.value || "").trim();
    const key = (els.memoryKey.value || "").trim();
    if (!content) {
      toast("Write a fact to remember first.");
      return;
    }
    const r = await fetch("/api/memory", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(key ? { content, key } : { content }),
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      toast(err.detail || `Failed (${r.status})`);
      return;
    }
    els.memoryContent.value = "";
    els.memoryKey.value = "";
    await loadMemories();
    toast("Memory saved");
  }

  async function loadConversations() {
    const r = await fetch("/api/conversations");
    const list = await r.json();
    els.convList.innerHTML = "";
    for (const c of list) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "conv-item" + (c.id === state.conversationId ? " active" : "");
      btn.innerHTML = `<span class="t"></span><span class="del" title="Delete">✕</span>`;
      btn.querySelector(".t").textContent = c.title || "Chat";
      btn.addEventListener("click", (e) => {
        if (e.target.classList.contains("del")) {
          e.stopPropagation();
          deleteConv(c.id);
          return;
        }
        openConversation(c.id, c.title);
      });
      els.convList.appendChild(btn);
    }
  }

  async function deleteConv(id) {
    await fetch(`/api/conversations/${id}`, { method: "DELETE" });
    if (state.conversationId === id) {
      state.conversationId = null;
      els.title.textContent = "Systems online";
      showEmpty();
    }
    await loadConversations();
  }

  async function openConversation(id, title) {
    state.conversationId = id;
    els.title.textContent = title || "Conversation";
    clearMessages();
    const r = await fetch(`/api/conversations/${id}/messages`);
    const msgs = await r.json();
    if (!msgs.length) showEmpty();
    else for (const m of msgs) appendMsg(m.role, m.content);
    await loadConversations();
  }

  async function newChat() {
    const r = await fetch("/api/conversations", { method: "POST" });
    const c = await r.json();
    state.conversationId = c.id;
    els.title.textContent = c.title;
    showEmpty();
    await loadConversations();
  }

  async function speak(text) {
    if (state.ttsMuted || !text.trim()) return;
    try {
      const r = await fetch("/api/tts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: text.slice(0, 1500) }),
      });
      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        console.warn("TTS error", err);
        return;
      }
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.onended = () => URL.revokeObjectURL(url);
      await audio.play();
    } catch (e) {
      console.warn("TTS play failed", e);
    }
  }

  async function sendMessage(raw) {
    const text = (raw ?? els.input.value).trim();
    if (!text || state.streaming) return;

    state.streaming = true;
    els.send.disabled = true;
    els.input.value = "";
    autoGrow();
    appendMsg("user", text);

    const assistantEl = appendMsg("assistant", "", { streaming: true });
    const bodyEl = assistantEl.querySelector(".body");
    let full = "";

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          conversation_id: state.conversationId,
          message: text,
          stream: true,
          web_search: !!state.webSearch,
        }),
      });

      if (!res.ok) {
        let detail = `HTTP ${res.status}`;
        try {
          const j = await res.json();
          detail = j.detail || detail;
        } catch (_) {}
        assistantEl.remove();
        appendMsg("assistant", detail, { error: true });
        toast(detail);
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() || "";
        for (const part of parts) {
          const line = part.trim();
          if (!line.startsWith("data: ")) continue;
          let payload;
          try {
            payload = JSON.parse(line.slice(6));
          } catch {
            continue;
          }
          if (payload.type === "meta" && payload.conversation_id) {
            state.conversationId = payload.conversation_id;
            if (payload.memory_saved) {
              toast("Memory saved");
              refreshHealth();
            }
          } else if (payload.type === "search") {
            const q = payload.query || text;
            const n = payload.count ?? 0;
            setSearching(true, n ? `${n} results for “${q.slice(0, 48)}”` : `“${q.slice(0, 48)}”`);
          } else if (payload.type === "token") {
            setSearching(false);
            full += payload.content;
            bodyEl.textContent = full;
            els.messages.scrollTop = els.messages.scrollHeight;
          } else if (payload.type === "error") {
            setSearching(false);
            assistantEl.remove();
            appendMsg("assistant", payload.message, { error: true });
            toast(payload.message);
            full = "";
          } else if (payload.type === "done") {
            setSearching(false);
            if (payload.conversation_id) state.conversationId = payload.conversation_id;
            if (payload.memory_saved) refreshHealth();
          }
        }
      }

      bodyEl.classList.remove("cursor-blink");
      if (full) {
        await speak(full);
        await loadConversations();
        const active = els.convList.querySelector(".conv-item.active .t");
        if (active) els.title.textContent = active.textContent;
      }
    } catch (e) {
      assistantEl.remove();
      const msg = `Connection error: ${e.message || e}`;
      appendMsg("assistant", msg, { error: true });
      toast(msg);
    } finally {
      setSearching(false);
      state.streaming = false;
      els.send.disabled = false;
      els.input.focus();
    }
  }

  function setupSpeech() {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      els.voice.title = "Web Speech API not supported — use Chrome/Edge";
      els.voice.addEventListener("click", () =>
        toast("Mic needs Chrome or Edge (Web Speech API). Type kar ke bhi chalega.")
      );
      return;
    }
    const rec = new SR();
    rec.lang = "en-IN";
    rec.interimResults = true;
    rec.continuous = false;
    state.recognition = rec;

    rec.onstart = () => {
      state.listening = true;
      els.voice.classList.add("listening");
      els.listening.classList.remove("hidden");
    };
    rec.onend = () => {
      state.listening = false;
      els.voice.classList.remove("listening");
      els.listening.classList.add("hidden");
    };
    rec.onerror = (ev) => {
      state.listening = false;
      els.voice.classList.remove("listening");
      els.listening.classList.add("hidden");
      if (ev.error !== "aborted" && ev.error !== "no-speech") {
        toast(`Mic error: ${ev.error}`);
      }
    };
    rec.onresult = (ev) => {
      let finalText = "";
      let interim = "";
      for (let i = ev.resultIndex; i < ev.results.length; i++) {
        const t = ev.results[i][0].transcript;
        if (ev.results[i].isFinal) finalText += t;
        else interim += t;
      }
      if (interim) els.input.value = interim;
      if (finalText.trim()) {
        els.input.value = finalText.trim();
        sendMessage(finalText.trim());
      }
      autoGrow();
    };

    const toggle = () => {
      if (state.listening) {
        rec.stop();
        return;
      }
      try {
        rec.start();
      } catch (e) {
        toast("Could not start mic — allow microphone permission.");
      }
    };
    els.voice.addEventListener("click", toggle);
  }

  // Events
  els.send.addEventListener("click", () => sendMessage());
  els.input.addEventListener("input", autoGrow);
  els.input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
  els.newChat.addEventListener("click", () => newChat());
  els.mute.addEventListener("click", () => {
    state.ttsMuted = !state.ttsMuted;
    localStorage.setItem("jarvis_tts_muted", state.ttsMuted ? "1" : "0");
    setMuteUI();
  });
  els.web.addEventListener("click", () => {
    state.webSearch = !state.webSearch;
    localStorage.setItem("jarvis_web_search", state.webSearch ? "1" : "0");
    setWebUI();
  });
  els.memoryBtn.addEventListener("click", () => openMemoryPanel());
  els.memoryClose.addEventListener("click", () => closeMemoryPanel());
  els.memoryAdd.addEventListener("click", () => addMemoryFromUI());
  els.memoryPanel.addEventListener("click", (e) => {
    if (e.target === els.memoryPanel) closeMemoryPanel();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !els.memoryPanel.classList.contains("hidden")) {
      closeMemoryPanel();
    }
  });

  // Boot
  setMuteUI();
  setWebUI();
  showEmpty();
  setupSpeech();
  (async () => {
    const h = await refreshHealth();
    await loadConversations();
    if (h && !h.has_llm_key) {
      toast(
        "API key missing. Copy .env.example → .env and set OPENAI_API_KEY or ANTHROPIC_API_KEY, then restart."
      );
    }
    els.input.focus();
  })();
})();
