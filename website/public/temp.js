const messagesDiv = document.getElementById("messages");
const inputField = document.getElementById("input");
const sendButton = document.getElementById("sendButton");
const micButton = document.getElementById("micButton");

let wsVosk, mediaStream, processor, audioContext;
let finalTranscript = "";
let recording = false; // Single source of truth for recording state

// Silence detection settings
const SILENCE_THRESHOLD = 0.003;
const SILENCE_DURATION = 2000;
const RMS_HISTORY_SIZE = 5;

let rmsHistory = [];
let lastSoundTime = Date.now();

// Gemini WS
const wsGemini = new WebSocket("ws://localhost:8765");
let currentGeminiMessageElement = null;

wsGemini.onmessage = (event) => {
  const chunk = event.data;
  if (chunk === "[[END]]") {
    currentGeminiMessageElement = null;
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    return;
  }
  if (!currentGeminiMessageElement) {
    currentGeminiMessageElement = document.createElement("div");
    currentGeminiMessageElement.classList.add("message", "gemini-message");
    currentGeminiMessageElement.innerHTML =
      "<b>Gemini:</b> <span class='stream-text'></span>";
    messagesDiv.appendChild(currentGeminiMessageElement);
  }
  const streamText = currentGeminiMessageElement.querySelector(".stream-text");
  if (streamText) streamText.textContent += chunk;
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
};

// Text message send
const sendMessage = () => {
  const message = inputField.value.trim();
  if (message && wsGemini.readyState === WebSocket.OPEN) {
    let userDiv = document.createElement("div");
    userDiv.classList.add("message", "user-message");
    userDiv.innerHTML = "<b>You:</b> " + message;
    messagesDiv.appendChild(userDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;

    currentGeminiMessageElement = null;
    wsGemini.send(message);
    inputField.value = "";
  }
};
sendButton.onclick = sendMessage;
inputField.addEventListener("keypress", (e) => {
  if (e.key === "Enter") sendMessage();
});

// Mic button handler (Single Source of Truth)
micButton.onclick = async () => {
  // Ensure AudioContext is resumed/started on user interaction
  if (audioContext && audioContext.state === "suspended") {
    audioContext.resume();
  }

  if (!recording) {
    micButton.textContent = "⏹ Stop";
    recording = true;
    finalTranscript = "";
    rmsHistory = [];
    lastSoundTime = Date.now();
    try {
      await startRecording();
    } catch (e) {
      // If startRecording fails (e.g., mic access denied), reset the button state
      stopRecording(false);
      console.error("Start recording failed:", e);
    }
  } else {
    // Manually stopped by user
    stopRecording();
  }
};

async function startRecording() {
  // Ensure we stop if the process is already running or being called again accidentally
  if (wsVosk || processor) stopRecording(false);

  mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
  audioContext = new AudioContext({ sampleRate: 16000 });
  const source = audioContext.createMediaStreamSource(mediaStream);

  // NOTE: createScriptProcessor is deprecated. Use AudioWorklet in production.
  processor = audioContext.createScriptProcessor(4096, 1, 1);

  // Use 127.0.0.1 for reliable local WebSocket connection
  wsVosk = new WebSocket("ws://localhost:2700");
  wsVosk.binaryType = "arraybuffer";

  wsVosk.onopen = () => {
    console.log("Vosk WS Connected");
  };

  wsVosk.onclose = () => {
    // If the server closes, ensure local resources are cleaned up (but don't auto-send)
    if (recording) stopRecording(false);
  };

  wsVosk.onerror = (error) => {
    console.error("Vosk WS Error:", error);
    if (recording) stopRecording(false);
  };

  wsVosk.onmessage = (event) => {
    const result = JSON.parse(event.data);
    let transcriptDiv = document.getElementById("transcript-msg");

    if (!transcriptDiv) {
      transcriptDiv = document.createElement("div");
      transcriptDiv.id = "transcript-msg";
      transcriptDiv.classList.add("message", "transcript-message");
      transcriptDiv.innerHTML = "<b>Voice:</b> <span id='voice-text'></span>";
      messagesDiv.appendChild(transcriptDiv);
    }

    const voiceText = transcriptDiv.querySelector("#voice-text");

    if (result.partial) {
      voiceText.textContent = finalTranscript.trim() + " " + result.partial;
    } else if (result.text) {
      finalTranscript += " " + result.text;
      voiceText.textContent = finalTranscript.trim();
    }

    messagesDiv.scrollTop = messagesDiv.scrollHeight;
  };

  processor.onaudioprocess = (e) => {
    const inputData = e.inputBuffer.getChannelData(0);
    const int16Data = floatTo16BitPCM(inputData);

    if (wsVosk.readyState === WebSocket.OPEN) {
      wsVosk.send(int16Data);
    }

    // --- Silence detection logic ---
    let sum = 0;
    for (let i = 0; i < inputData.length; i++) sum += inputData[i] ** 2;
    let rms = Math.sqrt(sum / inputData.length);

    rmsHistory.push(rms);
    if (rmsHistory.length > RMS_HISTORY_SIZE) rmsHistory.shift();
    let avgRMS = rmsHistory.reduce((a, b) => a + b, 0) / rmsHistory.length;

    if (avgRMS > SILENCE_THRESHOLD) {
      lastSoundTime = Date.now();
    } else if (Date.now() - lastSoundTime > SILENCE_DURATION) {
      // Auto-stop on silence - Auto-send is the default behavior
      stopRecording(true);
    }
    // --- End Silence detection logic ---
  };

  source.connect(processor);
  processor.connect(audioContext.destination);
}

/**
 * Stops recording and cleans up resources.
 * @param {boolean} [shouldSend=true] - Whether to automatically send the final transcript to Gemini.
 */
function stopRecording(shouldSend = true) {
  if (!recording) return;

  // 1. Update State (Single Source of Truth)
  recording = false;
  micButton.textContent = "🎙️ Start";

  // 2. Clean up Web Audio resources and null out references
  if (processor) {
    processor.disconnect();
    processor = null;
  }
  if (audioContext) {
    audioContext.close();
    audioContext = null;
  }
  if (mediaStream) {
    mediaStream.getTracks().forEach((t) => t.stop());
    mediaStream = null;
  }

  // 3. Close WebSocket and null out reference
  if (wsVosk) {
    if (wsVosk.readyState === WebSocket.OPEN) wsVosk.close();
    wsVosk = null;
  }

  // 4. Auto-send final transcript to Gemini if requested
  const trimmedTranscript = finalTranscript.trim();
  if (
    shouldSend &&
    trimmedTranscript &&
    wsGemini.readyState === WebSocket.OPEN
  ) {
    inputField.value = trimmedTranscript;
    sendMessage();
  }

  // 5. Clean up the temporary transcript element
  const transcriptDiv = document.getElementById("transcript-msg");
  if (transcriptDiv) transcriptDiv.remove();

  // 6. Reset transcript and RMS data
  finalTranscript = "";
  rmsHistory = [];
  lastSoundTime = Date.now();
}

function floatTo16BitPCM(float32Array) {
  const buffer = new ArrayBuffer(float32Array.length * 2);
  const view = new DataView(buffer);
  let offset = 0;
  for (let i = 0; i < float32Array.length; i++, offset += 2) {
    let s = Math.max(-1, Math.min(1, float32Array[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return buffer;
}
