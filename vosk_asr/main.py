import asyncio
import websockets
from vosk import Model, KaldiRecognizer

MODEL_PATH = "models/vosk-model-small-en-us-0.15"
model = Model(MODEL_PATH)


async def recognize(websocket):
    """
    WebSocket handler for Vosk streaming recognition
    """
    rec = KaldiRecognizer(model, 16000)
    try:
        async for message in websocket:
            if rec.AcceptWaveform(message):
                await websocket.send(rec.Result())
            else:
                await websocket.send(rec.PartialResult())

        # send final result when client disconnects
        try:
            await websocket.send(rec.FinalResult())
        except websockets.exceptions.ConnectionClosedOK:
            pass

    except websockets.exceptions.ConnectionClosedOK:
        pass


async def main():
    async with websockets.serve(recognize, "0.0.0.0", 2700):
        print("✅ Vosk WebSocket server running at ws://0.0.0.0:2700")
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
