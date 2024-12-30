import asyncio

import websockets

from zentropi import Frame
from zentropi import Kind


async def echo(websocket):
    async for message in websocket:
        frame = Frame.from_json(message)
        if frame.kind == Kind.COMMAND and frame.name == "login":
            print(f"login-ok", frame.to_dict())
            await websocket.send(frame.reply("login-ok").to_json())
        else:
            print(frame.to_dict())
            await websocket.send(message)


async def main():
    server = await websockets.serve(echo, "localhost", 26514)
    await server.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
