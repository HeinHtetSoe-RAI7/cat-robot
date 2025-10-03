import asyncio
import websockets


async def chat():
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as websocket:
        while True:
            msg = input("You: ")
            await websocket.send(msg)
            print("Gemini: ", end="", flush=True)

            # Keep receiving until [[END]]
            while True:
                chunk = await websocket.recv()
                if chunk == "[[END]]":
                    print("\n")
                    break
                print(chunk, end="", flush=True)


asyncio.run(chat())
