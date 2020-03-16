import pytest

from zentropi import Agent
from zentropi import Frame
from zentropi import WebsocketTransport
from zentropi.transport import websocket


class MockWebsockets(object):
    def __init__(self, login_ok=True, send_ok=True, recv_ok=True):
        self._login_ok = login_ok
        self._send_ok = send_ok
        self._recv_ok = recv_ok
        self.frame = None

    async def connect(self, endpoint):
        return self

    async def close(self):
        pass

    async def send(self, data):
        if not self._send_ok:
            raise ConnectionAbortedError()
        frame = Frame.from_json(data)
        if frame.name == 'login':
            if self._login_ok:
                self.frame = frame.reply('login-ok').to_json()
            else:
                self.frame = frame.reply('login-failed').to_json()
            return
        self.frame = data

    async def recv(self):
        if not self._recv_ok:
            raise ConnectionAbortedError()
        return self.frame

    


@pytest.mark.asyncio
async def test_websocket_transport(monkeypatch):
    monkeypatch.setattr(websocket, 'websockets', MockWebsockets())
    wt = WebsocketTransport()
    frame = Frame('test-frame')
    await wt.connect('ws://localhost:6789/', 'test-token')
    assert wt.connected is True
    await wt.send(frame)
    assert wt.connection.frame 
    frame_recv = await wt.recv()
    assert frame_recv.name == 'test-frame'
    await wt.close()
    assert wt.connected is False


@pytest.mark.asyncio
@pytest.mark.xfail(raises=PermissionError)
async def test_websocket_transport_login_fail(monkeypatch):
    monkeypatch.setattr(websocket, 'websockets', MockWebsockets(login_ok=False))
    wt = WebsocketTransport()
    frame = Frame('test-frame')
    await wt.connect('ws://localhost:6789/', 'test-token')


@pytest.mark.asyncio
@pytest.mark.xfail(raises=ConnectionError)
async def test_websocket_transport_send_fail(monkeypatch):
    monkeypatch.setattr(websocket, 'websockets', MockWebsockets(send_ok=False))
    wt = WebsocketTransport()
    frame = Frame('test-frame')
    await wt.connect('ws://localhost:6789/', 'test-token')

@pytest.mark.asyncio
@pytest.mark.xfail(raises=ConnectionError)
async def test_websocket_transport_recv_fail(monkeypatch):
    monkeypatch.setattr(websocket, 'websockets', MockWebsockets(recv_ok=False))
    wt = WebsocketTransport()
    frame = Frame('test-frame')
    await wt.connect('ws://localhost:6789/', 'test-token')


# @pytest.mark.asyncio
# async def test_agent_with_websocket_endpoint():
#     a = Agent('test-agent')
#     test_event_handler_was_run = False

#     @a.on_event('startup')
#     async def startup(frame):  # pragma: no cover
#         await a.connect('ws://localhost:6789/', 'test-token')
#         await a.event('test')

#     @a.on_event('test')
#     async def test(frame):  # pragma: no cover
#         nonlocal test_event_handler_was_run
#         test_event_handler_was_run = True
#         await a.close()
#         a.stop()

#     await a.start()

#     assert test_event_handler_was_run is True


# @pytest.mark.asyncio
# @pytest.mark.xfail(raises=ConnectionError)
# async def test_agent_with_websocket_login_fail():
#     a = Agent('test-agent')

#     @a.on_event('startup')
#     async def startup(frame):  # pragma: no cover
#         await a.connect('ws://localhost:6789/', 'fail-token')

#     await a.start()
