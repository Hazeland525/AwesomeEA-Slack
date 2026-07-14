// ── Voice session: state machine · WebRTC · tool dispatch · UI helpers ───────
// Depends on: subtitle.js (appendSubtitle, onSubtitleDone, onSubtitleNewResponse,
//             clearSubtitle), tools.js (TOOLS)

// ── DOM refs ─────────────────────────────────────────────────────────────────
const userAvatar = document.getElementById("userAvatar");
const userTile = document.getElementById("userTile");
const bottomBar = document.getElementById("bottomBar");
const transcriptEl = document.getElementById("transcriptEl");
const micBtn = document.getElementById("micBtn");
const micIcon = document.getElementById("micIcon");

const callBtn = document.getElementById("callBtn");
const endBtn = document.getElementById("endBtn");
const controlsCol = document.getElementById("controlsCol");
const statusEl = document.getElementById("callStatus");
const btnLabel = document.getElementById("btnLabel");
const avatarWrap = document.getElementById("avatarWrap");
const audio = document.getElementById("remoteAudio");

// ── Toast ─────────────────────────────────────────────────────────────────────
const _toast = document.getElementById("actionToast");
const _toastIcon = document.getElementById("toastIcon");
const _toastText = document.getElementById("toastText");
const _toastUndo = document.getElementById("toastUndo");
let _toastTimer = null;

// Slack ID → { name, avatarUrl } populated by resolve_contact results
const _contactCache = {};

// action = { label, fn } for a custom right-side button (e.g. "Turn off")
function showToast(text, iconSpec, undoData, action) {
  clearTimeout(_toastTimer);
  _toast.classList.remove("toast-visible");
  void _toast.offsetWidth; // force reflow so re-animation fires
  _toastIcon.textContent = "";
  if (iconSpec && (iconSpec.startsWith("http") || iconSpec.startsWith("/"))) {
    const img = document.createElement("img");
    img.src = iconSpec;
    img.className = iconSpec.endsWith(".svg")
      ? "toast-icon-svg"
      : "toast-avatar";
    img.alt = "";
    _toastIcon.appendChild(img);
  } else {
    _toastIcon.textContent = iconSpec || "";
  }
  _toastText.textContent = text;
  _toastUndo.style.display = "none";
  _toastUndo.disabled = false;
  _toastUndo.onclick = null;

  if (action) {
    _toastUndo.textContent = action.label;
    _toastUndo.style.display = "inline";
    _toastUndo.onclick = () => {
      action.fn();
      clearTimeout(_toastTimer);
      _toast.classList.remove("toast-visible");
    };
  } else if (undoData) {
    _toastUndo.textContent = "Undo";
    _toastUndo.style.display = "inline";
    _toastUndo.onclick = async () => {
      clearTimeout(_toastTimer);
      _toastUndo.style.display = "none";
      _toastUndo.disabled = true;
      try {
        const r = await fetch("/undo-message", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(undoData),
        });
        const d = await r.json();
        _toastText.textContent = d.ok ? "Message deleted" : "Couldn't undo";
      } catch {
        _toastText.textContent = "Couldn't undo";
      }
      _toastTimer = setTimeout(
        () => _toast.classList.remove("toast-visible"),
        2000,
      );
    };
  }

  _toast.classList.add("toast-visible");
  _toastTimer = setTimeout(
    () => _toast.classList.remove("toast-visible"),
    undoData || action ? 6000 : 4000,
  );
}

// ── Mic mute ──────────────────────────────────────────────────────────────────
let micMuted = false;
let callAudioTrack = null;

micBtn.addEventListener("click", () => {
  micMuted = !micMuted;
  const enabled = !micMuted;
  if (callAudioTrack) callAudioTrack.enabled = enabled;
  if (typeof pc !== "undefined" && pc) {
    pc.getSenders().forEach((s) => {
      if (s.track?.kind === "audio") s.track.enabled = enabled;
    });
  }
  micIcon.src = micMuted ? "/static/mute.svg" : "/static/mic.svg";
});

// ── VAD — pulse user tile while speaking ─────────────────────────────────────
function startVAD(stream) {
  const ctx = new (window.AudioContext || window.webkitAudioContext)();
  const src = ctx.createMediaStreamSource(stream);
  const an = ctx.createAnalyser();
  an.fftSize = 256;
  an.smoothingTimeConstant = 0.65;
  src.connect(an);
  const buf = new Uint8Array(an.frequencyBinCount);
  let frames = 0;
  (function tick() {
    requestAnimationFrame(tick);
    an.getByteFrequencyData(buf);
    const avg = buf.reduce((s, v) => s + v, 0) / buf.length;
    if (avg > 10) {
      if (++frames > 5) userTile.classList.add("speaking");
    } else {
      frames = 0;
      userTile.classList.remove("speaking");
    }
  })();
}

// Intercept getUserMedia to capture the call's audio track for mute + VAD
const _gum = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
navigator.mediaDevices.getUserMedia = async function (c) {
  const stream = await _gum(c);
  if (c && c.audio && !c.video) {
    const tracks = stream.getAudioTracks();
    if (tracks.length) {
      callAudioTrack = tracks[0];
      startVAD(stream);
    }
  }
  return stream;
};

// ── Fetch intercept — show tool activity in transcriptEl ─────────────────────
const TOOL_LABELS = {
  search_workspace: "🔍 Searching…",
  ramp_up: "📥 Loading channel…",
  resolve_contact: "👤 Looking up contact…",
  post_message: "💬 Sending message…",
  set_reminder: "⏰ Setting reminder…",
  create_canvas: "📋 Creating canvas…",
  edit_canvas: "📋 Editing canvas…",
  list_canvases: "📋 Listing canvases…",
  read_canvas: "📋 Reading canvas…",
  delete_canvas: "🗑️ Deleting canvas…",
};
let _transcriptReset = null;
const _fetch = window.fetch.bind(window);
window.fetch = function (url, opts) {
  if (typeof url === "string" && url === "/execute-tool" && opts?.body) {
    try {
      const { name } = JSON.parse(opts.body);
      transcriptEl.textContent = TOOL_LABELS[name] || `⚡ ${name}…`;
      clearTimeout(_transcriptReset);
      _transcriptReset = setTimeout(() => {
        transcriptEl.textContent = "—";
      }, 4000);
    } catch {}
  }
  return _fetch(url, opts);
};

// ── Background music ──────────────────────────────────────────────────────────
const bgMusic = document.getElementById("bgMusic");

function startBgMusic() {
  if (!bgMusic.src || bgMusic.networkState === bgMusic.NETWORK_NO_SOURCE)
    return;
  bgMusic.volume = 0.05;
  bgMusic.play().catch(() => {});
  showToast("Morning Vibe", "/static/music.svg", null, {
    label: "Turn off",
    fn: () => {
      bgMusic.muted = true;
    },
  });
}

function stopBgMusic() {
  bgMusic.pause();
  bgMusic.currentTime = 0;
}

// ── Session state ─────────────────────────────────────────────────────────────
let currentSessionId = null;
let pc = null;

let timerInterval = null;
let timerSeconds = 0;

function startTimer() {
  timerSeconds = 0;
  timerInterval = setInterval(() => {
    timerSeconds++;
    const m = Math.floor(timerSeconds / 60);
    const s = timerSeconds % 60;
    statusEl.textContent = `${m}:${String(s).padStart(2, "0")}`;
  }, 1000);
}

function stopTimer() {
  clearInterval(timerInterval);
  timerInterval = null;
}

function setState(state) {
  stopTimer();
  avatarWrap.classList.remove("pulsing");
  callBtn.style.display = "none";
  endBtn.style.display = "none";

  if (state === "idle") {
    callBtn.style.display = "flex";
    callBtn.disabled = false;
    statusEl.textContent = "Just you";
    btnLabel.textContent = "tap to call";
  } else if (state === "calling") {
    endBtn.style.display = "flex";
    statusEl.textContent = "Connecting…";
    btnLabel.textContent = "tap to end";
    avatarWrap.classList.add("pulsing");
  } else if (state === "connected") {
    endBtn.style.display = "flex";
    btnLabel.textContent = "tap to end";
    avatarWrap.classList.add("pulsing");
    startTimer();
  } else if (state === "ended") {
    statusEl.textContent = "Call ended";
    btnLabel.textContent = "";
    setTimeout(() => setState("idle"), 1800);
  } else if (state === "error") {
    callBtn.style.display = "flex";
    callBtn.disabled = false;
    btnLabel.textContent = "tap to retry";
  }

  const inCall = state === "calling" || state === "connected";
  controlsCol.style.display = inCall ? "flex" : "none";
  if (!inCall) clearSubtitle();
}

// ── WebRTC ────────────────────────────────────────────────────────────────────
async function startCall() {
  setState("calling");

  const tokenResp = await fetch("/token");
  if (!tokenResp.ok) {
    const errData = await tokenResp.json().catch(() => ({}));
    throw new Error(errData.error || `Request failed (${tokenResp.status})`);
  }
  const tokenData = await tokenResp.json();
  const EPHEMERAL_KEY = tokenData.value;
  currentSessionId = tokenData.session_id || null;

  pc = new RTCPeerConnection();

  pc.ontrack = (e) => {
    audio.srcObject = e.streams[0];
  };

  const localStream = await navigator.mediaDevices.getUserMedia({
    audio: true,
  });
  localStream.getTracks().forEach((track) => pc.addTrack(track, localStream));

  const dc = pc.createDataChannel("oai-events");

  dc.onopen = () => {
    setState("connected");
    startBgMusic();

    dc.send(
      JSON.stringify({
        type: "session.update",
        session: { type: "realtime", tools: TOOLS },
      }),
    );

    // Prompt agent to greet the user first (processes after session.update)
    dc.send(JSON.stringify({ type: "response.create" }));
  };

  dc.onmessage = async (e) => {
    let event;
    try {
      event = JSON.parse(e.data);
    } catch {
      return;
    }
    console.log("[voice] event:", event.type, event);

    if (event.type === "response.created") {
      onSubtitleNewResponse();
      return;
    }
    if (event.type === "response.output_audio_transcript.delta") {
      appendSubtitle(event.delta || "");
      return;
    }
    if (event.type === "response.output_audio_transcript.done") {
      onSubtitleDone();
      return;
    }

    if (event.type !== "response.output_item.done") return;
    const item = event.item;

    // Audio message items (not function calls) — skip tool handling
    if (item && item.type === "message" && item.role === "assistant") return;

    if (!item || item.type !== "function_call") return;

    const { name, call_id, arguments: argsStr } = item;
    let args;
    try {
      args = JSON.parse(argsStr);
    } catch {
      args = {};
    }

    let output;
    try {
      const execResp = await fetch("/execute-tool", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          arguments: args,
          session_id: currentSessionId,
        }),
      });
      const execData = await execResp.json();
      output = JSON.stringify(execData.result ?? { error: execData.error });

      // Action toasts + contact cache
      const res = execData.result;
      if (name === "post_message" && res?.ts) {
        const cached = _contactCache[args.target || ""] || {};
        const dest = res.channel_name || cached.name || null;
        showToast(
          "Message sent" + (dest ? " to " + dest : ""),
          cached.avatarUrl || "💬",
          { channel: res.channel, ts: res.ts },
        );
      } else if (name === "set_reminder") {
        showToast("Reminder set", "⏰");
      } else if (name === "create_canvas") {
        const dest = res?.channel_name || null;
        showToast("Canvas created" + (dest ? " in " + dest : ""), "📋");
      } else if (name === "edit_canvas") {
        showToast("Canvas updated", "📋");
      } else if (name === "delete_canvas") {
        showToast("Canvas deleted", "🗑️");
      } else if (name === "save_memory") {
        showToast("Memory updated", "🧠");
      }

      if (name === "resolve_contact" && execData.result) {
        const rc = execData.result;
        if (rc.match?.id)
          _contactCache[rc.match.id] = {
            name: rc.match.name,
            avatarUrl: rc.match.avatar_url || "",
          };
        (rc.candidates || []).forEach((c) => {
          if (c.id)
            _contactCache[c.id] = {
              name: c.name,
              avatarUrl: c.avatar_url || "",
            };
        });
      }
    } catch (err) {
      output = JSON.stringify({ error: String(err) });
      console.error("[voice] tool call failed:", err);
    }

    dc.send(
      JSON.stringify({
        type: "conversation.item.create",
        item: { type: "function_call_output", call_id, output },
      }),
    );
    dc.send(JSON.stringify({ type: "response.create" }));
  };

  const offer = await pc.createOffer();
  await pc.setLocalDescription(offer);

  const sdpResp = await fetch("https://api.openai.com/v1/realtime/calls", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${EPHEMERAL_KEY}`,
      "Content-Type": "application/sdp",
    },
    body: offer.sdp,
  });
  if (!sdpResp.ok) {
    const err = await sdpResp.text();
    throw new Error(`SDP exchange failed (${sdpResp.status}): ${err}`);
  }

  await pc.setRemoteDescription({ type: "answer", sdp: await sdpResp.text() });
}

function stopCall() {
  if (currentSessionId) {
    fetch("/end-session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: currentSessionId }),
    })
      .then((r) => r.json())
      .then((d) => {
        if (d.memory_updated) showToast("Memory updated", "🧠");
      })
      .catch((err) => console.error("[voice] end-session failed:", err));
    currentSessionId = null;
  }
  if (pc) {
    pc.getSenders().forEach((s) => s.track?.stop());
    pc.close();
    pc = null;
  }
  audio.srcObject = null;
  stopBgMusic();
  setState("ended");
}

// ── Button handlers ───────────────────────────────────────────────────────────
callBtn.addEventListener("click", () => {
  startCall().catch((err) => {
    console.error("[voice] error:", err);
    statusEl.textContent = err.message;
    setState("error");
  });
});

endBtn.addEventListener("click", stopCall);

// ── Init ──────────────────────────────────────────────────────────────────────
startCall().catch((err) => {
  console.error("[voice] auto-start error:", err);
  statusEl.textContent = err.message;
  setState("error");
});

fetch("/config")
  .then((r) => r.json())
  .then((d) => {
    const el = document.getElementById("workspaceCtx");
    if (el && d.workspace) el.textContent = `Connected to ${d.workspace}`;
    if (d.avatar_url) userAvatar.src = d.avatar_url;
  })
  .catch(() => {});
