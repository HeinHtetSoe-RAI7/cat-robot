import sys
import queue
import json
import threading
import sounddevice as sd
from vosk import Model, KaldiRecognizer
import google.generativeai as genai
from gtts import gTTS
import io
import pygame
import time

# ----------------------------
# Gemini setup
# ----------------------------
api_key = "AIzaSyBqpN-lzZ4ePx99up3DpAaGZ1f6ChWS4vg"
genai.configure(api_key=api_key)

system_instruction = (
    "You are a student (a kid) practicing English with your teacher. "
    "You will receive spoken sentences from your teacher, but the input comes from Automatic Speech Recognition (ASR), "
    "so it may contain mistakes. "
    "Your role is to behave like a curious kid. "
    "If the teacher’s sentence looks correct and understandable, respond naturally as a student would. "
    "Always keep your tone childlike, curious, and respectful. "
    "Do not try to 'fix' the teacher’s English yourself. Just ask for clarification like a student would when they don’t understand. "
    "Your goal is to make the interaction feel like a real student learning English from a non-native teacher."
)

model_gemini = genai.GenerativeModel("gemini-2.5-flash", system_instruction=system_instruction)
chat_state = model_gemini.start_chat()  # persistent chat

def generate_response(message):
    try:
        response = chat_state.send_message(message)
        return response.text.strip()
    except Exception as e:
        print(f"Gemini error: {e}", file=sys.stderr)
        return "Sorry, something went wrong."

# ----------------------------
# Vosk setup
# ----------------------------
MODEL_PATH = "/home/myatooswe/ASR test/vosk-model-en-us-0.42-gigaspeech"
vosk_model = Model(MODEL_PATH)
recognizer = KaldiRecognizer(vosk_model, 16000)

audio_queue = queue.Queue()

# Event to pause STT while TTS is speaking
stt_allowed = threading.Event()
stt_allowed.set()

# ----------------------------
# gTTS + pygame TTS setup
# ----------------------------
pygame.mixer.init()

def speak_blocking(text):
    """Speak with gTTS + pygame (blocking)."""
    stt_allowed.clear()
    print(f"[TTS] {text}")

    try:
        # synthesize to memory
        mp3_fp = io.BytesIO()
        tts = gTTS(text=text, lang="en")
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)

        # play audio
        pygame.mixer.music.load(mp3_fp, "mp3")
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
    except Exception as e:
        print("TTS error:", e, file=sys.stderr)
    finally:
        stt_allowed.set()

def speak_async(text):
    threading.Thread(target=speak_blocking, args=(text,), daemon=True).start()

# ----------------------------
# Audio callback
# ----------------------------
def audio_callback(indata, frames, time_info, status):
    if status:
        print("AUDIO STATUS:", status, file=sys.stderr)
    if stt_allowed.is_set():
        try:
            audio_queue.put(bytes(indata))
        except Exception as e:
            print("audio_callback error:", e, file=sys.stderr)

# ----------------------------
# STT loop
# ----------------------------
def stt_loop():
    global recognizer
    while True:
        if not stt_allowed.is_set():
            time.sleep(0.05)
            continue

        try:
            data = audio_queue.get(timeout=0.1)
        except queue.Empty:
            continue

        try:
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text = result.get("text", "").strip()
                if text:
                    print(f"\nYou said: {text}")
                    if text.lower() == "exit":
                        print("Goodbye!")
                        break
                    reply = generate_response(text)
                    print(f"AI  : {reply}\n")
                    speak_async(reply)
            else:
                partial = json.loads(recognizer.PartialResult()).get("partial", "")
                if partial:
                    print(f"Partial: {partial}", end="\r")
        except Exception as e:
            print("STT loop error:", e, file=sys.stderr)
            recognizer = KaldiRecognizer(vosk_model, 16000)

# ----------------------------
# Main
# ----------------------------
def main():
    print("=== CLI English Chat with Gemini + Vosk + gTTS ===")
    print("Speak into your microphone. Say 'exit' to quit.\n")

    # Start STT thread
    stt_thread = threading.Thread(target=stt_loop, daemon=True)
    stt_thread.start()

    try:
        with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                               channels=1, callback=audio_callback):
            while stt_thread.is_alive():
                time.sleep(0.1)
    except KeyboardInterrupt:
        print("Interrupted by user, exiting...")

if __name__ == "__main__":
    main()
