(() => {
  const $ = (sel) => document.querySelector(sel);

  const els = {
    messages: $("#messages"),
    input: $("#input"),
    send: $("#btn-send"),
    newChat: $("#btn-new"),
    convList: $("#conv-list"),
    mute: $("#btn-mute"),
    voice: $("#btn-voice"),
    status: $("#status-pill"),
    model: $("#model-label"),
    title: $("#chat-title"),
    listening: $("#listening-banner"),
    toast: $("#toast"),
  };

  const state = {
    conversationId: null,
    streaming: false,
    ttsMuted: localStorage.getItem("jarvis_tts_muted") === "1",
    recognition: null,
    listening: false,
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
    d.innerHTML = `<h2>Systems online</h2><p>Madhav-ji, aap command dijiye.<br/>Mic ya type — Jarvis ready hai.</p>`;
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
      return h;
    } catch (e) {
      els.status.textContent = "Offline";
      els.status.className = "pill err";
      return null;
    }
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
          } else if (payload.type === "token") {
            full += payload.content;
            bodyEl.textContent = full;
            els.messages.scrollTop = els.messages.scrollHeight;
          } else if (payload.type === "error") {
            assistantEl.remove();
            appendMsg("assistant", payload.message, { error: true });
            toast(payload.message);
            full = "";
          } else if (payload.type === "done") {
            if (payload.conversation_id) state.conversationId = payload.conversation_id;
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

  // Boot
  setMuteUI();
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
