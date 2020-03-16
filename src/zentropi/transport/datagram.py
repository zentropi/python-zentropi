import asyncio_dgram
from ..frame import Frame
from ..kind import Kind
from .base import BaseTransport


class DatagramTransport(BaseTransport):
    def __init__(self):
        self._host = '127.0.0.1'
        self._port = 26514
        self.connection = None
        self.connected = False
    
    async def connect(self, endpoint, token):
        from zentropi import Kind
        from zentropi import Frame

        self.token = token
        self.endpoint = endpoint
        self._host, self._port = endpoint.replace('dgram://', '').split(':')
        self.connection = await asyncio_dgram.connect((self._host, self._port))
        await self.send(Frame('login', kind=Kind.COMMAND, data=dict(token=token)))
        auth_ack = await self.recv()
        if auth_ack.name == 'login-ok':
            self.connected = True
        else:
            raise PermissionError(f'Unable to connect to {endpoint}, got {auth_ack.to_dict()}')


    async def close(self):
        self.connection.close()
        self.connected = False

    async def send(self, frame):
        await self.connection.send(frame.to_json().encode('utf-8'))

    async def recv(self):
        data, remote_addr = await self.connection.recv()
        frame = Frame.from_json(data.decode('utf-8'))
        return frame
