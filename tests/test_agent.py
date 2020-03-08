import asyncio
from asyncio.coroutines import iscoroutinefunction
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


def test_on_interval_decorator_adds_handler():
    a = Agent('test-agent')

    @a.on_interval('test-interval', 4.2)
    async def test_interval(frame):  # pragma: no cover
        pass

    assert a._handlers_interval['test-interval']


@pytest.mark.xfail(raises=KeyError)
def test_on_interval_decorator_fails_on_duplicate_name():
    a = Agent('test-agent')

    @a.on_interval('test-interval', 4.2)
    async def test_interval(frame):  # pragma: no cover
        pass

    assert a._handlers_interval['test-interval']

    @a.on_interval('test-interval', 4.2)
    async def test_interval_duplicate(frame):  # pragma: no cover
        pass


@pytest.mark.asyncio
async def test_on_interval_wrapper():
    a = Agent('test-agent')
    interval_handler_was_run = False

    @a.on_interval('test-interval', 0)
    async def test_interval(frame):  # pragma: no cover
        nonlocal interval_handler_was_run
        interval_handler_was_run = True
        a.stop()

    interval_handler = a._handlers_interval['test-interval']
    assert iscoroutinefunction(interval_handler)
    assert iscoroutinefunction(test_interval)

    asyncio.create_task(a.start())
    for _ in range(3):
        await asyncio.sleep(0)
    assert interval_handler_was_run is True


def test_on_event_decorator_adds_handler():
    a = Agent('test-agent')

    @a.on_event('startup')
    async def startup(frame):  # pragma: no cover
        pass

    assert a._handlers_event['startup']


@pytest.mark.xfail(raises=KeyError)
def test_on_event_decorator_fails_on_duplicate_name():
    a = Agent('test-agent')

    @a.on_event('startup')
    async def startup(frame):  # pragma: no cover
        pass

    assert a._handlers_event['startup']

    @a.on_event('startup')
    async def startup_duplicate(frame):  # pragma: no cover
        pass


@pytest.mark.asyncio
async def test_startup_handler_is_run():
    a = Agent('test-agent')
    startup_handler_was_run = False

    @a.on_event('startup')
    async def startup(frame):  # pragma: no cover
        nonlocal startup_handler_was_run
        startup_handler_was_run = True
        a.stop()

    asyncio.create_task(a.start())
    for _ in range(3):
        await asyncio.sleep(0)

    assert startup_handler_was_run is True


@pytest.mark.asyncio
async def test_shutdown_handler_is_run():
    a = Agent('test-agent')
    shutdown_handler_was_run = False

    @a.on_event('startup')
    async def startup(frame):  # pragma: no cover
        a.stop()

    @a.on_event('shutdown')
    async def shutdown(frame):  # pragma: no cover
        nonlocal shutdown_handler_was_run
        shutdown_handler_was_run = True
        a.stop()

    asyncio.create_task(a.start())
    for _ in range(3):
        await asyncio.sleep(0)

    assert shutdown_handler_was_run is True
