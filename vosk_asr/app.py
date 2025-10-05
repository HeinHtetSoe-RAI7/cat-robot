import queue
import sounddevice as sd
import vosk
import sys
import json
import threading
import pyttsx3
import os
import google.generativeai as genai
import time

# ----------------------------
# Gemini setup
# ----------------------------
os.environ["GRPC_VERBOSITY"] = "ERROR"
os.environ["GRPC_TRACE"] = "none"

api_key = "AIzaSyBqpN-lzZ4ePx99up3DpAaGZ1f6ChWS4vg"
genai.configure(api_key=api_key)

system_instruction = (
    "You are a student (a kid) practicing English with your teacher. "
    "You will receive sentences from your teacher. "
    "Your role is to behave like a curious kid, respond naturally, and keep a childlike tone."
)

model_gemini = genai.GenerativeModel(
    "gemini-2.5-flash", system_instruction=system_instruction
)
chat_state = model_gemini.start_chat()


def generate_response(message):
    try:
        response = chat_state.send_message(message)
        return response.text.strip()
    except Exception as e:
        print(f"Gemini error: {e}", file=sys.stderr)
        return "Sorry, something went wrong."


# ----------------------------
# Vosk STT setup
# ----------------------------
MODEL_PATH = "models/vosk-model-small-en-us-0.15"
try:
    vosk_model = vosk.Model(MODEL_PATH)
except Exception as e:
    print(f"Vosk model not found at {MODEL_PATH}", file=sys.stderr)
    sys.exit(1)

recognizer = vosk.KaldiRecognizer(vosk_model, 16000)
audio_queue = queue.Queue()

stt_allowed = threading.Event()
stt_allowed.set()  # initially allowed
mic_stream = None  # will hold the microphone stream


def audio_callback(indata, frames, time_info, status):
    if status:
        print("Audio status:", status, file=sys.stderr)
    if stt_allowed.is_set():
        audio_queue.put(bytes(indata))


# ----------------------------
# TTS setup
# ----------------------------
tts_engine = pyttsx3.init()

# Slow down speech rate
rate = tts_engine.getProperty("rate")
tts_engine.setProperty("rate", int(rate * 0.7))  # ~70% speed

voices = tts_engine.getProperty("voices")
tts_engine.setProperty("voice", voices[0].id)  # pick first voice

tts_lock = threading.Lock()


def speak(text):
    """Pause STT, flush mic queue, speak, then resume STT."""

    def run():
        stt_allowed.clear()  # stop STT
        try:
            if mic_stream and mic_stream.active:
                mic_stream.stop()
        except Exception:
            pass

        # Flush any queued audio to avoid recording TTS
        with audio_queue.mutex:
            audio_queue.queue.clear()

        with tts_lock:
            tts_engine.say(text)
            tts_engine.runAndWait()

        # Resume STT
        try:
            if mic_stream and not mic_stream.active:
                mic_stream.start()
        except Exception:
            pass
        stt_allowed.set()

    threading.Thread(target=run, daemon=True).start()


# ----------------------------
# STT loop
# ----------------------------
def stt_loop():
    last_partial = ""
    while True:
        if not stt_allowed.is_set():
            time.sleep(0.05)
            continue

        try:
            data = audio_queue.get(timeout=0.1)
        except queue.Empty:
            continue

        if recognizer.AcceptWaveform(data):
            result = json.loads(recognizer.Result())
            text = result.get("text", "").strip()
            if text:
                print(f"\nYou said: {text}")
                if text.lower() == "exit":
                    print("Exiting...")
                    os._exit(0)  # force exit all threads

                reply = generate_response(text)
                print(f"AI : {reply}\n")
                speak(reply)
                last_partial = ""
        else:
            partial = json.loads(recognizer.PartialResult()).get("partial", "")
            if partial and partial != last_partial:
                print(f"Partial: {partial}", end="\r")
                last_partial = partial


# ----------------------------
# Main
# ----------------------------
def main():
    global mic_stream
    try:
        mic_stream = sd.RawInputStream(
            samplerate=16000,
            blocksize=8000,
            dtype="int16",
            channels=1,
            callback=audio_callback,
        )
        mic_stream.start()
    except Exception as e:
        print("Error starting microphone:", e, file=sys.stderr)
        return

    stt_thread = threading.Thread(target=stt_loop, daemon=True)
    stt_thread.start()

    print("Speak into your microphone. Say 'exit' to quit.\n")

    try:
        while stt_thread.is_alive():
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        if mic_stream and mic_stream.active:
            mic_stream.stop()
            mic_stream.close()


if __name__ == "__main__":
    main()