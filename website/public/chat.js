const messagesDiv = document.getElementById("messages");
const inputField = document.getElementById("input");
const sendButton = document.getElementById("sendButton");
const micButton = document.getElementById("micButton");

let wsVosk, mediaStream, audioContext, workletNode;
let finalTranscript = "";
let recording = false; // Single source of truth for recording state

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
    try {
      await startRecording();
    } catch (e) {
      // If startRecording fails (e.g., mic access denied), reset the button state
      stopRecording(false);
      console.error("Start recording failed:", e);
    }
  } else {
    // Manually stopped by user
    stopRecording(true);
  }
};

// startRecording
async function startRecording() {
  // Ensure we stop if the process is already running or being called again accidentally
  if (wsVosk || workletNode) stopRecording(false);

  mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
  audioContext = new AudioContext({ sampleRate: 16000 });
  const source = audioContext.createMediaStreamSource(mediaStream);

  // 1. Load AudioWorklet module
  await audioContext.audioWorklet.addModule("vosk-processor.js");

  // 2. Create AudioWorklet node
  workletNode = new AudioWorkletNode(audioContext, "vosk-processor");

  // 3. Vosk WebSocket
  wsVosk = new WebSocket("ws://localhost:2700");
  wsVosk.binaryType = "arraybuffer";

  wsVosk.onopen = () => {
    console.log("Vosk WS Connected");
  };

  wsVosk.onclose = () => {
    // If the server closes, clean up resources (but don't auto-send the transcript)
    if (recording) stopRecording(false);
  };

  wsVosk.onerror = (error) => {
    console.error("Vosk WS Error:", error);
    if (recording) stopRecording(false);
  };

  // 4. Handle messages from the Worklet thread
  workletNode.port.onmessage = (event) => {
    const { type, data } = event.data;

    if (type === "pcm") {
      // Audio data ready to send to Vosk
      if (wsVosk && wsVosk.readyState === WebSocket.OPEN) wsVosk.send(data);
    } else if (type === "silence") {
      // Silence detected by Worklet - Auto-stop
      stopRecording(true);
    }
  };

  // 5. Vosk Reply Handler (unchanged)
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

  // 6. Connect Nodes
  source.connect(workletNode);
  workletNode.connect(audioContext.destination);
}

/**
 * Stops recording and cleans up resources.
 * @param {boolean} [shouldSend=true] - Whether to automatically send the final transcript to Gemini.
 */
function stopRecording(shouldSend = true) {
  if (!recording) return;

  // 1. Update State (Single Source of Truth)
  recording = false;
  micButton.textContent = "🎤 Start";

  // 2. Clean up Web Audio resources and null out references
  if (workletNode) {
    workletNode.disconnect();
    workletNode = null;
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

  // 6. Reset transcript buffer
  finalTranscript = "";
}
