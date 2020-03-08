import asyncio

import websockets

from zentropi import Frame
from zentropi import Kind


async def echo(websocket, path):
    async for message in websocket:
        frame = Frame.from_json(message)
        if frame.kind == Kind.COMMAND and frame.name == 'login':
            print(f'login-ok', frame.to_dict())
            await websocket.send(frame.reply('login-ok').to_json())
        else:
            print(frame.to_dict())
            await websocket.send(message)


if __name__ == '__main__':
    start_server = websockets.serve(echo, "localhost", 26514)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
