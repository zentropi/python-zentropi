import pytest

from zentropi import Agent
from zentropi import Frame
from zentropi import WebsocketTransport


@pytest.mark.asyncio
async def test_websocket_transport():
    wt = WebsocketTransport()
    frame = Frame('test-frame')
    await wt.connect('ws://localhost:6789/', 'test-token')
    assert wt.connected is True
    await wt.send(frame)
    frame_recv = await wt.recv()
    assert frame_recv.name == 'test-frame'
    await wt.close()
    assert wt.connected is False


@pytest.mark.asyncio
async def test_agent_with_websocket_endpoint():
    a = Agent('test-agent')
    test_event_handler_was_run = False

    @a.on_event('startup')
    async def startup(frame):  # pragma: no cover
        await a.connect('ws://localhost:6789/', 'test-token')
        await a.event('test')

    @a.on_event('test')
    async def test(frame):  # pragma: no cover
        nonlocal test_event_handler_was_run
        test_event_handler_was_run = True
        await a.close()
        a.stop()

    await a.start()

    assert test_event_handler_was_run is True


@pytest.mark.asyncio
@pytest.mark.xfail(raises=ConnectionError)
async def test_agent_with_websocket_login_fail():
    a = Agent('test-agent')

    @a.on_event('startup')
    async def startup(frame):  # pragma: no cover
        await a.connect('ws://localhost:6789/', 'fail-token')

    await a.start()
