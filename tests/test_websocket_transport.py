import socket
from asyncio.queues import Queue
from collections import namedtuple

import pytest

from zentropi.protocol.frame import Frame
from zentropi.protocol.kind import Kind
from zentropi.transport.websocket import Websocket


class DummyWebsocketConnection(object):
    def __init__(self, send_q, recv_q) -> None:
        self.send_q = send_q
        self.recv_q = recv_q

    async def connect(self, endpoint, ssl=False):
        return self

    async def close(self):
        pass

    async def send(self, data):
        await self.send_q.put(data)

    async def recv(self):
        return await self.recv_q.get()


class DummyZeroconf(object):
    def get_service_info(self, *args):
        ServiceInfo = namedtuple('ServiceInfo', 'addresses properties port')
        addr = socket.inet_aton('127.0.0.1')
        sinfo = ServiceInfo([addr], {b'tls': True}, 26514)
        return sinfo

    def close(self):
        pass


class DummyZeroconfNOTLS(object):
    def get_service_info(self, *args):
        ServiceInfo = namedtuple('ServiceInfo', 'addresses properties port')
        addr = socket.inet_aton('127.0.0.1')
        sinfo = ServiceInfo([addr], {b'tls': False}, 26514)
        return sinfo

    def close(self):
        pass


class DummyOfflineZeroconf(object):
    def get_service_info(self, *args):
        return None

    def close(self):
        pass


@pytest.mark.asyncio
async def test_websocket():
    ws = Websocket()
    send_q = Queue(maxsize=2)
    recv_q = Queue(maxsize=2)
    await recv_q.put(Frame('login', kind=Kind.COMMAND).to_json())
    await ws.connect(
        agent_uuid='test-agent',
        token='test-token',
        endpoint='ws://localhost:26514/ws/',
        connection=DummyWebsocketConnection(send_q, recv_q),
        zeroconf=DummyZeroconf)
    auth_sent = await send_q.get()
    auth_frame = Frame.from_json(auth_sent)
    assert auth_frame.kind == Kind.COMMAND
    assert auth_frame.name == 'login'
    assert auth_frame.data['agent_uuid'] == 'test-agent'
    assert auth_frame.data['token'] == 'test-token'
    await ws.send(Frame('hello'))
    sent_frame = await send_q.get()
    assert 'hello' in sent_frame
    recv_frame = Frame('ohai').to_json()
    await recv_q.put(recv_frame)
    ohai_frame = await ws.recv()
    assert ohai_frame.name == 'ohai'
    await ws.disconnect()


@pytest.mark.asyncio
async def test_websocket_zeroconf():
    ws = Websocket()
    send_q = Queue(maxsize=2)
    recv_q = Queue(maxsize=2)
    await recv_q.put(Frame('login', kind=Kind.COMMAND).to_json())
    await ws.connect(
        agent_uuid='test-agent',
        token='test-token',
        connection=DummyWebsocketConnection(send_q, recv_q),
        zeroconf=DummyZeroconf)
    auth_sent = await send_q.get()
    auth_frame = Frame.from_json(auth_sent)
    assert auth_frame.kind == Kind.COMMAND
    assert auth_frame.name == 'login'
    assert auth_frame.data['agent_uuid'] == 'test-agent'
    assert auth_frame.data['token'] == 'test-token'


@pytest.mark.asyncio
async def test_websocket_zeroconf_notls():
    ws = Websocket()
    send_q = Queue(maxsize=2)
    recv_q = Queue(maxsize=2)
    await recv_q.put(Frame('login', kind=Kind.COMMAND).to_json())
    await ws.connect(
        agent_uuid='test-agent',
        token='test-token',
        connection=DummyWebsocketConnection(send_q, recv_q),
        zeroconf=DummyZeroconfNOTLS)
    auth_sent = await send_q.get()
    auth_frame = Frame.from_json(auth_sent)
    assert auth_frame.kind == Kind.COMMAND
    assert auth_frame.name == 'login'
    assert auth_frame.data['agent_uuid'] == 'test-agent'
    assert auth_frame.data['token'] == 'test-token'


@pytest.mark.asyncio
@pytest.mark.xfail(raises=AssertionError)
async def test_unknown_websocket_schema():
    ws = Websocket()
    send_q = Queue(maxsize=2)
    recv_q = Queue(maxsize=2)
    await recv_q.put(Frame('login', kind=Kind.COMMAND).to_json())
    await ws.connect(
        agent_uuid='test-agent',
        token='test-token',
        endpoint='http://localhost:26514/',
        connection=DummyWebsocketConnection(send_q, recv_q),
        zeroconf=DummyZeroconf)


@pytest.mark.asyncio
@pytest.mark.xfail(raises=Exception)
async def test_websocket_zeroconf_fails():
    ws = Websocket()
    send_q = Queue(maxsize=2)
    recv_q = Queue(maxsize=2)
    await recv_q.put(Frame('login', kind=Kind.COMMAND).to_json())
    await ws.connect(
        agent_uuid='test-agent',
        token='test-token',
        connection=DummyWebsocketConnection(send_q, recv_q),
        zeroconf=DummyOfflineZeroconf)
