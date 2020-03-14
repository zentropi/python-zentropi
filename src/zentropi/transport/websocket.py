import websockets

from ..frame import Frame
from ..kind import Kind
from .base import BaseTransport


class WebsocketTransport(BaseTransport):
    def __init__(self):
        self.connection = None
        self.connected = False
        self.token = None
        self.endpoint = ''

    async def connect(self, endpoint, token):
        self.token = token
        self.endpoint = endpoint
        self.connection = await websockets.connect(endpoint)
        auth_frame = Frame('login', kind=Kind.COMMAND, data={'token': token})
        await self.connection.send(auth_frame.to_json())
        auth_ack = await self.recv()
        if not auth_ack.name == 'login-ok':
            raise PermissionError(f'Unable to connect to {endpoint}, got {auth_ack.to_dict()}')
        self.connected = True

    async def close(self):
        await self.connection.close()
        self.connected = False
        self.token = None

    async def send(self, frame: Frame) -> None:
        try:
            await self.connection.send(frame.to_json())
        except Exception as e:
            raise ConnectionError('Websocket was closed.') from e

    async def recv(self) -> Frame:
        try:
            _frame = await self.connection.recv()
            return Frame.from_json(_frame)
        except Exception as e:
            raise ConnectionError('Websocket was closed.') from e
