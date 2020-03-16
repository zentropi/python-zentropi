import asyncio_dgram
from ..frame import Frame
from ..kind import Kind
from .base import BaseTransport


class DatagramTransport(BaseTransport):
    def __init__(self):
        self._host = '127.0.0.1'
        self._port = 26514
        self._connection = None
    
    async def connect(self, endpoint, token):
        from zentropi import Kind
        from zentropi import Frame

        self.token = token
        self.endpoint = endpoint
        self._host, self._port = endpoint.replace('dgram://', '').split(':')
        self._connection = await asyncio_dgram.connect((self._host, self._port))
        await self.send(Frame('login', kind=Kind.COMMAND, data=dict(token=token)))

    async def close(self):
        self._connection.close()

    async def send(self, frame):
        print(f'send {frame.name}')
        await self._connection.send(frame.to_json().encode('utf-8'))

    async def recv(self):
        data, remote_addr = await self._connection.recv()
        print(f'recv {data}')
        return Frame.from_json(data.decode('utf-8'))
