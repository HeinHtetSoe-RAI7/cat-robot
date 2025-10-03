// vosk-processor.js

// Silence detection settings - must match the main script for consistency
const SILENCE_THRESHOLD = 0.003;
const RMS_HISTORY_SIZE = 5;
const SILENCE_DURATION = 2000; // ms (must be managed using counters or time, not duration directly)

// We'll use a frame counter to manage the silence duration
let rmsHistory = [];
let silenceFrames = 0;
const sampleRate = 16000; // Must match AudioContext settings
const frameSize = 128; // Standard Worklet frame size (or 4096 if you specified it)
const silenceFrameLimit = Math.ceil(
  (SILENCE_DURATION / 1000) * (sampleRate / frameSize)
);

class VoskProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    // Initialize silence tracking variables on the Worklet thread
    this.rmsHistory = [];
    this.silenceFrames = 0;
  }

  // Utility function to convert 32-bit float to 16-bit PCM
  floatTo16BitPCM(float32Array) {
    const buffer = new ArrayBuffer(float32Array.length * 2);
    const view = new DataView(buffer);
    let offset = 0;
    for (let i = 0; i < float32Array.length; i++, offset += 2) {
      let s = Math.max(-1, Math.min(1, float32Array[i]));
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    }
    return buffer;
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0];
    const channel = input[0];

    if (channel) {
      // 1. Audio Data Conversion and Post
      const int16Data = this.floatTo16BitPCM(channel);
      // Post PCM data to main thread (type: 'pcm')
      this.port.postMessage({ type: "pcm", data: int16Data }, [int16Data]);

      // 2. Silence Detection
      let sum = 0;
      for (let i = 0; i < channel.length; i++) sum += channel[i] ** 2;
      let rms = Math.sqrt(sum / channel.length);

      this.rmsHistory.push(rms);
      if (this.rmsHistory.length > RMS_HISTORY_SIZE) this.rmsHistory.shift();
      let avgRMS =
        this.rmsHistory.reduce((a, b) => a + b, 0) / this.rmsHistory.length;

      if (avgRMS > SILENCE_THRESHOLD) {
        this.silenceFrames = 0; // Sound detected, reset counter
      } else {
        this.silenceFrames++; // Increment silence frame counter
        if (this.silenceFrames > 300) {
          // A safe number of frames for 2 seconds at 128 buffer size
          // Post silence event to main thread (type: 'silence')
          this.port.postMessage({ type: "silence" });
          return false; // Stop processing audio on this thread
        }
      }
    }

    return true;
  }
}

registerProcessor("vosk-processor", VoskProcessor);
