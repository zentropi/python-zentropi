from asyncio import Queue

from zentropi import Frame


class QueueTransport(object):
    def __init__(self):
        self.queue_recv = Queue()
        self.queue_send = Queue()
        self.connected = False
        self.agent_token = None

    async def connect(self, agent_token):
        self.connected = True
        self.agent_token = agent_token

    async def close(self):
        self.connected = False
        self.agent_token = None

    async def send(self, frame: Frame) -> None:
        await self.queue_send.put(frame)

    async def recv(self) -> Frame:
        return await self.queue_recv.get()
