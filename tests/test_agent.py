import asyncio 

import pytest

from zentropi import Agent


def test_agent_run_and_stop():
    a = Agent('test-agent')
    loop = asyncio.get_event_loop()
    async def shutdown():
        while not a._running:
            await asyncio.sleep(0)
        a.stop()
    loop.create_task(shutdown())
    a.run(loop=loop)


def test_agent_run_and_shutdown():
    a = Agent('test-agent')
    loop = asyncio.get_event_loop()
    async def shutdown():
        while not a._running:
            await asyncio.sleep(0)
        a.shutdown_event.set()
    loop.create_task(shutdown())
    a.run(loop=loop)


@pytest.mark.asyncio
async def test_agent_start_and_stop():
    a = Agent('test-agent')
    asyncio.create_task(a.start())
    await asyncio.sleep(0)
    assert a._running is True
    a.stop()
    await asyncio.sleep(0)
    assert a._running is False


@pytest.mark.asyncio
async def test_agent_start_and_shutdown():
    a = Agent('test-agent')
    asyncio.create_task(a.start())
    await asyncio.sleep(0)
    assert a._running is True
    a.shutdown_event.set()
    await asyncio.sleep(0)
    assert a._running is False
