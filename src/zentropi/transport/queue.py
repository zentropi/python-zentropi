from asyncio import Queue

from zentropi import Frame

from .base import BaseTransport


class QueueTransport(BaseTransport):
    def __init__(self):
        self.queue_recv = Queue()
        self.queue_send = Queue()
        self.connected = False
        self.token = None
        self.endpoint = ''

    async def connect(self, endpoint, token):
        self.connected = True
        self.token = token
        self.endpoint = endpoint

    async def close(self):
        self.connected = False
        self.token = None

    async def send(self, frame: Frame) -> None:
        await self.queue_send.put(frame)

    async def recv(self) -> Frame:
        return await self.queue_recv.get()
