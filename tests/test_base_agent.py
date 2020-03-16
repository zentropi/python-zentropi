import asyncio

import pytest

from zentropi.base_agent import BaseAgent
from zentropi.base_agent import Kind
from zentropi.base_agent import on_interval
from zentropi.base_agent import on_command
from zentropi.base_agent import on_event
from zentropi.base_agent import on_message
from zentropi.base_agent import on_request
from zentropi.base_agent import parse_period
from zentropi.base_agent import parse_rate_limit
from zentropi.base_agent import apply_rate_limits


def test_agent_class_method_decorators():
    class TestAgent(BaseAgent):
        @on_interval('test-interval', 10)
        async def test_interval():
            pass

        @on_command('test-command')
        async def test_command():
            pass

        @on_event('test-event')
        async def test_event():
            pass

        @on_message('test-message')
        async def test_message():
            pass

        @on_request('test-request')
        async def test_request():
            pass

    test_agent = TestAgent()


    assert test_agent.test_interval.interval == 10
    assert test_agent.test_interval.handler == 'test-interval'
    assert test_agent.test_interval.kind == Kind.INTERVAL

    assert test_agent._interval_handlers['test-interval'] == test_agent.test_interval
    assert test_agent._command_handlers['test-command'] == test_agent.test_command
    assert test_agent._event_handlers['test-event'] == test_agent.test_event
    assert test_agent._message_handlers['test-message'] == test_agent.test_message
    assert test_agent._request_handlers['test-request'] == test_agent.test_request


def test_agent_function_decorators():
    class TestAgent(BaseAgent):
        pass

    test_agent = TestAgent()

    @test_agent.on_interval('test-interval', 10)
    async def test_interval():
        pass

    @test_agent.on_command('test-command')
    async def test_command():
        pass

    @test_agent.on_event('test-event')
    async def test_event():
        pass

    @test_agent.on_message('test-message')
    async def test_message():
        pass

    @test_agent.on_request('test-request')
    async def test_request():
        pass

    assert test_agent._interval_handlers['test-interval'] == test_interval
    assert test_agent._command_handlers['test-command'] == test_command
    assert test_agent._event_handlers['test-event'] == test_event
    assert test_agent._message_handlers['test-message'] == test_message
    assert test_agent._request_handlers['test-request'] == test_request


@pytest.mark.xfail(raises=KeyError)
def test_agent_duplicate_handlers_raise_key_error():
    class TestAgent(BaseAgent):
        pass

    test_agent = TestAgent()

    @test_agent.on_command('test-command')
    async def test_command():
        pass

    @test_agent.on_command('test-command')
    async def duplicate_test_command():
        pass

def test_agent_get_handler():
    class TestAgent(BaseAgent):
        @on_event('test-event')
        async def test_event(self):
            pass

    test_agent = TestAgent()

    @test_agent.on_event('*')
    async def test_all_events():
        pass

    assert test_agent.get_handler(Kind.EVENT, 'test-event') == test_agent.test_event
    assert test_agent.get_handler(Kind.EVENT, 'test-something-else') == test_all_events
    assert test_agent.get_handler(Kind.COMMAND, 'test-gets-none') is None

@pytest.mark.asyncio
async def test_agent_handle_frame_sync():
    got_frame = None

    class TestAgent(BaseAgent):
        pass

    test_agent = TestAgent()

    @test_agent.on_event('test-event')
    def test_event(frame):
        nonlocal got_frame
        got_frame = frame
        return frame


    got_return = await test_agent.run_handler(Kind.EVENT, 'test-event', True, timeout=0.1)

    assert got_return is True
    assert got_frame is True


@pytest.mark.asyncio
async def test_agent_handle_frame_async():
    got_frame = None

    class TestAgent(BaseAgent):
        @on_event('test-event')
        async def test_event(self, frame):
            nonlocal got_frame
            got_frame = frame
            return frame

    test_agent = TestAgent()

    got_return = await test_agent.run_handler(Kind.EVENT, 'test-event', True, timeout=0.1)

    assert got_return is True
    assert got_frame is True


@pytest.mark.asyncio
async def test_agent_skip_frame_for_nonexistent_handler():
    class TestAgent(BaseAgent):
        pass

    test_agent = TestAgent()
    expected_none = await test_agent.run_handler(Kind.EVENT, 'test-nonexistent', True, timeout=0.1)
    assert expected_none is None


def test_agent_sets_coro_attribute():
    class TestAgent(BaseAgent):
        @on_event('test-event-sync')
        def test_event():
            pass

        @on_event('test-event-async')
        async def test_event_async():
            pass
        
    test_agent = TestAgent()

    assert getattr(test_agent.test_event, 'run_async') is False
    assert getattr(test_agent.test_event_async, 'run_async') is True

@pytest.mark.asyncio
async def test_agent_handle_without_passing_frame():
    got_no_frame = None

    class TestAgent(BaseAgent):
        @on_event('test-event')
        async def test_event(self):
            nonlocal got_no_frame
            got_no_frame = True
            return True

    test_agent = TestAgent()

    got_return = await test_agent.run_handler(Kind.EVENT, 'test-event', True, timeout=0.1)

    assert got_return is True
    assert got_no_frame is True


def test_period_parse():
    period = parse_period('s')
    assert period == 1
    period = parse_period('9 s')
    assert period == 9
    period = parse_period('m')
    assert period == 60
    period = parse_period('3m')
    assert period == 3 * 60
    period = parse_period('7h')
    assert period == 7 * 60 * 60


def test_parse_rate_limit():
    calls, period = parse_rate_limit('10/m')
    assert calls == 10
    assert period == 60


@pytest.mark.xfail(raises=ValueError)
def test_parse_rate_limit_fails_on_invalid_input():
    parse_rate_limit('fail')


@pytest.mark.xfail(raises=TypeError)
def test_apply_rate_limits_fails_on_invalid_type():
    apply_rate_limits('1/s', lambda: None)


@pytest.mark.asyncio
async def test_rate_limits():
    got_frame = None

    class TestAgent(BaseAgent):
        @on_command('test-event', rate_limits=['2/s'])
        async def test_event(self, frame):
            nonlocal got_frame
            got_frame = frame
            return frame

    test_agent = TestAgent()

    got_return = await test_agent.run_handler(Kind.COMMAND, 'test-event', True, timeout=0.1)
    assert got_return is True
    assert got_frame is True
    await asyncio.sleep(0.1)
    got_return = await test_agent.run_handler(Kind.COMMAND, 'test-event', False, timeout=0.1)
    assert got_return is False
    assert got_frame is False


@pytest.mark.asyncio
@pytest.mark.xfail(raises=RuntimeError)
async def test_rate_limits_exceeded():
    got_frame = None

    class TestAgent(BaseAgent):
        @on_command('test-event', rate_limits=['1/m'])
        async def test_event(self, frame):
            nonlocal got_frame
            got_frame = frame
            return frame

    test_agent = TestAgent()

    got_return = await test_agent.run_handler(Kind.COMMAND, 'test-event', True, timeout=0.1)
    assert got_return is True
    assert got_frame is True
    await test_agent.run_handler(Kind.COMMAND, 'test-event', False, timeout=0.1)
    

@pytest.mark.asyncio
@pytest.mark.xfail(raises=TimeoutError)
async def test_handler_timeout_exceeded_for_sync_handler():
    got_frame = None

    class TestAgent(BaseAgent):
        @on_command('test-event', rate_limits=['2/s'])
        def test_event(self, frame):
            nonlocal got_frame
            got_frame = frame
            import time
            time.sleep(frame)
            return frame

    test_agent = TestAgent()

    got_return = await test_agent.run_handler(Kind.COMMAND, 'test-event', 0, timeout=0.1)
    assert got_return is 0
    assert got_frame is 0
    await test_agent.run_handler(Kind.COMMAND, 'test-event', 1, timeout=0.1)


@pytest.mark.asyncio
async def test_spawn_and_watch():
    class TestAgent(BaseAgent):
        pass

    test_agent = TestAgent()

    async def test_task():
        await asyncio.sleep(0)
    
    name, task = test_agent.spawn('test-task', test_task())
    await asyncio.sleep(0)
    assert len(test_agent._spawned_tasks) == 1
    assert name == list(test_agent._spawned_tasks.keys())[0]
    assert task == test_agent._spawned_tasks[name]
    assert isinstance(task, asyncio.Task)
    await asyncio.gather(task)
    assert len(test_agent._spawned_tasks) == 0


@pytest.mark.asyncio
async def test_spawn_and_watch_and_cancel():
    class TestAgent(BaseAgent):
        pass

    test_agent = TestAgent()

    async def test_task():
        while True:
            await asyncio.sleep(1)
    
    name, task = test_agent.spawn('test-task', test_task())
    await asyncio.sleep(0)
    assert len(test_agent._spawned_tasks) == 1
    assert name == list(test_agent._spawned_tasks.keys())[0]
    assert task == test_agent._spawned_tasks[name]
    assert isinstance(task, asyncio.Task)
    await test_agent.cancel_spawned_tasks()
    await asyncio.sleep(0)
    assert len(test_agent._spawned_tasks) == 0

@pytest.mark.asyncio
async def test_spawn_single():
    class TestAgent(BaseAgent):
        pass

    test_agent = TestAgent()

    async def test_task():
        while True:
            await asyncio.sleep(1)
    
    name, task = test_agent.spawn('test-task', test_task(), single=True)
    await asyncio.sleep(0)
    assert name == 'test-task'
    assert len(test_agent._spawned_tasks) == 1
    assert name == list(test_agent._spawned_tasks.keys())[0]
    assert task == test_agent._spawned_tasks[name]
    assert isinstance(task, asyncio.Task)
    await test_agent.cancel_spawned_tasks()
    await asyncio.sleep(0)
    assert len(test_agent._spawned_tasks) == 0

@pytest.mark.asyncio
@pytest.mark.xfail(raises=RuntimeError)
async def test_spawn_single_fails_on_duplicate():
    class TestAgent(BaseAgent):
        pass

    test_agent = TestAgent()

    async def test_task():
        await asyncio.sleep(1)
    
    name, task = test_agent.spawn('test-task', test_task(), single=True)
    await asyncio.sleep(0)
    name, task = test_agent.spawn('test-task', lambda: None, single=True)
    await test_agent.cancel_spawned_tasks()
    await asyncio.sleep(0)


@pytest.mark.asyncio
@pytest.mark.xfail(raises=NotImplementedError)
async def test_spawn_exception_is_forwarded():
    class TestAgent(BaseAgent):
        pass

    test_agent = TestAgent()

    async def test_task():
        raise NotImplementedError('boom')
    
    name, task = test_agent.spawn('test-task', test_task())
    await asyncio.gather(task)
