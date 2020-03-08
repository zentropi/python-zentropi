import asyncio

import websockets

from zentropi import Frame
from zentropi import Kind


async def echo(websocket, path):  # pragma: no cover
    async for message in websocket:
        frame = Frame.from_json(message)
        if frame.kind == Kind.COMMAND and frame.name == 'login' and frame.data.get('token') == 'fail-token':
            print(frame.to_dict())
            print(f'login-fail')
            await websocket.send(frame.reply('login-fail').to_json())
        elif frame.kind == Kind.COMMAND and frame.name == 'login':
            print(frame.to_dict())
            print(f'login-ok')
            await websocket.send(frame.reply('login-ok').to_json())
        else:
            print(frame.to_dict())
            await websocket.send(message)


if __name__ == '__main__':  # pragma: no cover
    start_server = websockets.serve(echo, "localhost", 6789)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
