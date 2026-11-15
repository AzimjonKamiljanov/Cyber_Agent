/**
 * Cyber Agent PWA Client
 * Vanilla JS voice controller with AudioWorklet streaming and 24 kHz playback.
 */

const STATE_TRANSLATIONS = {
  Idle: "Kutilmoqda",
  Listening: "Tinglanmoqda...",
  Thinking: "O'ylanmoqda...",
  Speaking: "Gapirmoqda...",
  Stopped: "To'xtatildi",
};

let ws = null;
let audioCtx = null;
let micStream = null;
let workletNode = null;
let isPttActive = false;
let isStopped = false;

// Playback queue for 24 kHz audio chunks
let playbackQueue = [];
let isPlaying = false;
let currentSourceNode = null;

const statusBadge = document.getElementById("status-badge");
const tokenInput = document.getElementById("pairing-token");
const saveTokenBtn = document.getElementById("save-token-btn");
const pttBtn = document.getElementById("ptt-btn");
const stopBtn = document.getElementById("stop-btn");
const resumeBtn = document.getElementById("resume-btn");
const transcriptList = document.getElementById("transcript-list");
const clearTranscriptBtn = document.getElementById("clear-transcript-btn");

const diagEcho = document.getElementById("diag-echo");
const diagNoise = document.getElementById("diag-noise");
const diagAgc = document.getElementById("diag-agc");
const diagRate = document.getElementById("diag-rate");

// Load stored token
const storedToken = localStorage.getItem("cyber_pairing_token") || "";
tokenInput.value = storedToken;

function updateStatus(state) {
  statusBadge.className = `badge badge-${state.toLowerCase()}`;
  statusBadge.textContent = STATE_TRANSLATIONS[state] || state;

  if (state === "Stopped") {
    isStopped = true;
    pttBtn.disabled = true;
    stopBtn.style.display = "none";
    resumeBtn.style.display = "block";
  } else {
    isStopped = false;
    pttBtn.disabled = !ws || ws.readyState !== WebSocket.OPEN;
    stopBtn.style.display = "block";
    resumeBtn.style.display = "none";
  }
}

function appendTranscript(role, text, isFinal = false) {
  let existing = transcriptList.querySelector(`.transcript-msg.${role}.interim`);
  if (!existing || isFinal) {
    if (existing) existing.remove();
    const div = document.createElement("div");
    div.className = `transcript-msg ${role} ${isFinal ? "final" : "interim"}`;
    const prefix = role === "user" ? "Siz" : "Cyber Agent";
    div.textContent = `${prefix}: ${text}`;
    transcriptList.appendChild(div);
  } else {
    const prefix = role === "user" ? "Siz" : "Cyber Agent";
    existing.textContent = `${prefix}: ${text}`;
  }
  transcriptList.scrollTop = transcriptList.scrollHeight;
}

saveTokenBtn.addEventListener("click", () => {
  const token = tokenInput.value.trim();
  localStorage.setItem("cyber_pairing_token", token);
  connectWebSocket();
});

clearTranscriptBtn.addEventListener("click", () => {
  transcriptList.innerHTML = '<div class="transcript-msg system">Suhbat tarixi tozalandi.</div>';
});

async function initMicrophone() {
  if (micStream) return;

  const constraints = {
    audio: {
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
      channelCount: 1,
    },
  };

  try {
    micStream = await navigator.mediaDevices.getUserMedia(constraints);
    const audioTrack = micStream.getAudioTracks()[0];
    const settings = audioTrack.getSettings ? audioTrack.getSettings() : {};

    diagEcho.textContent = settings.echoCancellation !== undefined ? String(settings.echoCancellation) : "Ha (So'ralgan)";
    diagNoise.textContent = settings.noiseSuppression !== undefined ? String(settings.noiseSuppression) : "Ha (So'ralgan)";
    diagAgc.textContent = settings.autoGainControl !== undefined ? String(settings.autoGainControl) : "Ha (So'ralgan)";
    diagRate.textContent = settings.sampleRate ? `${settings.sampleRate} Hz` : "48000 Hz";

    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    await audioCtx.audioWorklet.addModule("/audio-processor.js");

    const micSource = audioCtx.createMediaStreamSource(micStream);
    workletNode = new AudioWorkletNode(audioCtx, "audio-capture-processor");

    workletNode.port.onmessage = (event) => {
      if (isPttActive && ws && ws.readyState === WebSocket.OPEN && !isStopped) {
        ws.send(event.data); // Binary 16 kHz PCM16
      }
    };

    micSource.connect(workletNode);
  } catch (err) {
    appendTranscript("system", `Mikrofon ruxsati berilmadi: ${err.message}`);
  }
}

function flushAudioPlayback() {
  playbackQueue = [];
  isPlaying = false;
  if (currentSourceNode) {
    try {
      currentSourceNode.stop();
      currentSourceNode.disconnect();
    } catch (_) {}
    currentSourceNode = null;
  }
}

async function playNextChunk() {
  if (playbackQueue.length === 0 || isStopped) {
    isPlaying = false;
    return;
  }

  isPlaying = true;
  const chunk = playbackQueue.shift();

  if (!audioCtx) {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  }
  if (audioCtx.state === "suspended") {
    await audioCtx.resume();
  }

  // Convert PCM16 (Int16Array) to Float32Array at 24000 Hz
  const int16 = new Int16Array(chunk);
  const float32 = new Float32Array(int16.length);
  for (let i = 0; i < int16.length; i++) {
    float32[i] = int16[i] / 32768.0;
  }

  const audioBuffer = audioCtx.createBuffer(1, float32.length, 24000);
  audioBuffer.getChannelData(0).set(float32);

  const source = audioCtx.createBufferSource();
  source.buffer = audioBuffer;
  source.connect(audioCtx.destination);
  currentSourceNode = source;

  source.onended = () => {
    currentSourceNode = null;
    playNextChunk();
  };

  source.start();
}

function connectWebSocket() {
  if (ws) {
    ws.close();
  }

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const token = localStorage.getItem("cyber_pairing_token") || "";
  const wsUrl = `${protocol}//${window.location.host}/ws/voice?token=${encodeURIComponent(token)}`;

  ws = new WebSocket(wsUrl);
  ws.binaryType = "arraybuffer";

  ws.onopen = () => {
    updateStatus("Idle");
    appendTranscript("system", "Shlyuzga ulandi.");
    initMicrophone();
  };

  ws.onmessage = (event) => {
    if (typeof event.data === "string") {
      const msg = JSON.parse(event.data);
      if (msg.type === "transcript_in") {
        appendTranscript("user", msg.text, msg.is_final);
      } else if (msg.type === "transcript_out") {
        appendTranscript("agent", msg.text, msg.is_final);
      } else if (msg.type === "status") {
        updateStatus(msg.state);
      } else if (msg.type === "error") {
        appendTranscript("system", `Xatolik [${msg.code}]: ${msg.message}`);
      }
    } else if (event.data instanceof ArrayBuffer && !isStopped) {
      playbackQueue.push(event.data);
      if (!isPlaying) {
        playNextChunk();
      }
    }
  };

  ws.onclose = (event) => {
    updateStatus("Idle");
    pttBtn.disabled = true;
    appendTranscript("system", `Aloqa uzildi (kod: ${event.code}). Tokenni tekshiring.`);
  };

  ws.onerror = () => {
    appendTranscript("system", "WebSocket xatosi.");
  };
}

// Push-to-Talk Event Handlers
function startPtt() {
  if (pttBtn.disabled || isStopped) return;
  isPttActive = true;
  pttBtn.classList.add("active");

  // Immediate barge-in: flush local playback
  flushAudioPlayback();

  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "ptt_start" }));
  }
}

function endPtt() {
  if (!isPttActive) return;
  isPttActive = false;
  pttBtn.classList.remove("active");

  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "ptt_end" }));
  }
}

pttBtn.addEventListener("pointerdown", (e) => {
  e.preventDefault();
  startPtt();
});

pttBtn.addEventListener("pointerup", (e) => {
  e.preventDefault();
  endPtt();
});

pttBtn.addEventListener("pointercancel", (e) => {
  e.preventDefault();
  endPtt();
});

// Keyboard Spacebar PTT support
window.addEventListener("keydown", (e) => {
  if (e.code === "Space" && !e.repeat && document.activeElement !== tokenInput) {
    e.preventDefault();
    startPtt();
  }
});

window.addEventListener("keyup", (e) => {
  if (e.code === "Space" && document.activeElement !== tokenInput) {
    e.preventDefault();
    endPtt();
  }
});

// Emergency STOP
stopBtn.addEventListener("click", () => {
  flushAudioPlayback();
  isStopped = true;
  updateStatus("Stopped");
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "stop" }));
  }
});

resumeBtn.addEventListener("click", () => {
  isStopped = false;
  updateStatus("Idle");
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "resume" }));
  }
});

// Service Worker Registration
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").catch((err) => {
    console.debug("ServiceWorker registration skipped or failed:", err);
  });
}

// Auto-connect on page load
connectWebSocket();
