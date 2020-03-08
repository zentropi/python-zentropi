import asyncio
from threading import Event

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

@pytest.mark.asyncio
async def test_agent_spawn():
    stop_waiting = Event()

    async def wait_a_sec():
        await stop_waiting.wait()

    a = Agent('test-agent')
    asyncio.create_task(a.start())
    await asyncio.sleep(0)
    task_id, task = a.spawn(wait_a_sec())
    assert task_id in a._spawned_tasks
    assert task == a._spawned_tasks[task_id]
    stop_waiting.set()
    await asyncio.sleep(0)
    assert task_id not in a._spawned_tasks
    a.stop()

@pytest.mark.asyncio
async def test_agent_spawn_exception_in_task():
    stop_waiting = Event()

    async def wait_a_sec():
        await stop_waiting.wait()
        raise Exception('boom')  # pragma: no cover

    a = Agent('test-agent')
    asyncio.create_task(a.start())
    await asyncio.sleep(0)
    task_id, task = a.spawn(wait_a_sec())
    assert task_id in a._spawned_tasks
    assert task == a._spawned_tasks[task_id]
    stop_waiting.set()
    await asyncio.sleep(0)
    assert task_id not in a._spawned_tasks
    await asyncio.sleep(0)
    assert a._running is False
