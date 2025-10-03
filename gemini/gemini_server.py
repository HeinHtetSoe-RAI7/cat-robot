import asyncio
import websockets
import google.generativeai as genai
import os

# --- Gemini Setup ---
API_KEY = os.getenv("GEMINI_API_KEY") or "YOUR_API_KEY_HERE"
genai.configure(api_key=API_KEY)

system_instruction = (
    "You are a student (a kid) practicing English with your teacher. "
    "You will receive sentences from your teacher. "
    "Your role is to behave like a curious kid, respond naturally, and keep a childlike tone."
)

MODEL_NAME = "gemini-2.5-flash"  # make sure this model exists
model = genai.GenerativeModel(MODEL_NAME)


# --- WebSocket Handler ---
async def handle_client(websocket):
    async for message in websocket:
        try:
            # Streaming response (sync generator)
            response = model.generate_content(message, stream=True)

            # Send chunks as they arrive
            for chunk in response:
                if chunk.text:
                    await websocket.send(chunk.text)

            # Send END marker so client knows it's done
            await websocket.send("[[END]]")

        except Exception as e:
            await websocket.send(f"Error: {str(e)}")


# --- Main Loop ---
async def main():
    async with websockets.serve(handle_client, "0.0.0.0", 8765):
        print("✅ WebSocket server started on ws://localhost:8765")
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
