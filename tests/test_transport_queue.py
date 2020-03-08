import asyncio

import pytest

from zentropi import Agent
from zentropi import Frame
from zentropi import QueueTransport


@pytest.mark.asyncio
async def test_queue_transport():
    qt = QueueTransport()
    frame = Frame('test-frame')
    await qt.connect('test-endpoint', 'test-token')
    assert qt.connected is True
    await qt.send(frame)
    frame_sent = await qt.queue_send.get()
    assert frame == frame_sent
    frame_ = Frame('test-recv')
    await qt.queue_recv.put(frame_)
    frame_recv = await qt.recv()
    assert frame_ == frame_recv
    await qt.close()
    assert qt.connected is False


@pytest.mark.asyncio
async def test_agent_with_queue_endpoint():
    a = Agent('test-agent')
    test_event_handler_was_run = False

    @a.on_event('startup')
    async def startup(frame):  # pragma: no cover
        await a.connect('queue://test', 'test-token')
        await a.event('test')

    @a.on_event('test')
    async def test(frame):  # pragma: no cover
        nonlocal test_event_handler_was_run
        test_event_handler_was_run = True
        await a.close()
        a.stop()

    async def dummy_server():
        f = await a._transport.queue_send.get()
        await a._transport.queue_recv.put(f)

    asyncio.create_task(a.start())

    for _ in range(3):
        await asyncio.sleep(0)

    await dummy_server()

    for _ in range(3):
        await asyncio.sleep(0)

    assert test_event_handler_was_run is True


@pytest.mark.asyncio
async def test_agent_with_queue_transport():
    a = Agent('test-agent')
    test_event_handler_was_run = False
    qt = QueueTransport()

    @a.on_event('startup')
    async def startup(frame):  # pragma: no cover
        await a.connect('queue://test', 'test-token', transport=qt)
        await a.event('test')

    @a.on_event('test')
    async def test(frame):  # pragma: no cover
        nonlocal test_event_handler_was_run
        test_event_handler_was_run = True
        a.stop()

    async def dummy_server():
        f = await a._transport.queue_send.get()
        await a._transport.queue_recv.put(f)

    asyncio.create_task(a.start())

    for _ in range(3):
        await asyncio.sleep(0)

    await dummy_server()

    for _ in range(3):
        await asyncio.sleep(0)

    assert test_event_handler_was_run is True


@pytest.mark.asyncio
async def test_agent_with_invalid_endpoint():
    a = Agent('test-agent')
    exception_caught = False

    @a.on_event('startup')
    async def startup(frame):  # pragma: no cover
        try:
            await a.connect('invalid://', 'test-token')
        except RuntimeError:
            nonlocal exception_caught
            exception_caught = True
            a.stop()

    asyncio.create_task(a.start())

    for _ in range(3):
        await asyncio.sleep(0)

    assert a._running is False
    assert exception_caught is True


@pytest.mark.asyncio
async def test_agent_recv_loop_exits():
    a = Agent('test-agent')
    test_event_handler_was_run = False

    @a.on_event('startup')
    async def startup(frame):  # pragma: no cover
        await a.connect('queue://test', 'test-token')
        await a.event('test')

    @a.on_event('test')
    async def test(frame):  # pragma: no cover
        nonlocal test_event_handler_was_run
        test_event_handler_was_run = True
        await a.close()
        a.stop()

    async def dummy_server():
        f = await a._transport.queue_send.get()
        await a._transport.queue_recv.put(f)

    asyncio.create_task(a.start())

    for _ in range(3):
        await asyncio.sleep(0)

    await dummy_server()

    for _ in range(20):
        await asyncio.sleep(0)

    assert test_event_handler_was_run is True
