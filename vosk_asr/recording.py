import queue
import sounddevice as sd
import vosk
import sys
import json

MODEL_PATH = "models/vosk-model-small-en-us-0.15"  # put model in app folder

try:
    model = vosk.Model(MODEL_PATH)
except Exception as e:
    print(
        f"Vosk model not found at {MODEL_PATH}. Download from https://alphacephei.com/vosk/models",
        file=sys.stderr,
    )
    sys.exit(1)

recognizer = vosk.KaldiRecognizer(model, 16000)
audio_queue = queue.Queue()


def audio_callback(indata, frames, time_info, status):
    if status:
        print("Audio status:", status, file=sys.stderr)
    audio_queue.put(bytes(indata))


def main():
    # --- ADDED: Variable to cache the last partial result ---
    last_partial = ""

    try:
        stream = sd.RawInputStream(
            samplerate=16000,
            blocksize=8000,
            dtype="int16",
            channels=1,
            callback=audio_callback,
        )
        stream.start()
        print("Speak into your microphone. Press Ctrl+C to exit.\n")

        while True:
            try:
                data = audio_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if recognizer.AcceptWaveform(data):
                # Full result received
                result = json.loads(recognizer.Result())
                text = result.get("text", "").strip()
                if text:
                    # Clear the partial line before printing the final result
                    sys.stdout.write(" " * len(last_partial) + "\r")
                    print(f"Transcription: {text}")
                    last_partial = ""  # Reset the cache after a full result

            else:
                # Partial result received
                partial = json.loads(recognizer.PartialResult()).get("partial", "")

                # --- MODIFIED: Check if the partial result has changed ---
                if partial and partial != last_partial:
                    sys.stdout.write(f"Partial: {partial}" + "\r")
                    sys.stdout.flush()  # Ensure the update is immediately shown
                    last_partial = partial  # Cache the new partial result

    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        # Final cleanup for the stream
        if "stream" in locals() and stream.active:
            stream.stop()
            stream.close()


if __name__ == "__main__":
    main()
