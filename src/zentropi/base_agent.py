import asyncio
import logging
import random
import string
from concurrent.futures import TimeoutError as FuturesTimeoutError
from concurrent.futures import CancelledError as FuturesCancelledError
from enum import IntEnum
from inspect import iscoroutinefunction
from inspect import signature
from typing import Awaitable
from typing import Callable
from typing import Optional
from typing import Any
from typing import Dict
from typing import List

from asgiref.sync import sync_to_async
from ratelimit import limits
from ratelimit.exception import RateLimitException

from . import configure_logging
from .kind import Kind
from .frame import Frame

logger = logging.getLogger(__name__)


def detect_handler_properties(func):
    if iscoroutinefunction(func):
        setattr(func, 'run_async', True)
    else:
        setattr(func, 'run_async', False)

    params = signature(func).parameters
    if params.get('frame', None):
        setattr(func, 'pass_frame', True)
    else:
        setattr(func, 'pass_frame', False)

period_miltipliers = {
    's': 1,
    'm': 60,
    'h': 60 * 60,
}

def parse_period(period_str: str):
    period_str = period_str.strip().lower()
    multiplier = period_str[-1]
    if len(period_str) > 1:
        period_base = int(period_str[:-1].strip())
    else:
        period_base = 1
    return period_base * period_miltipliers[multiplier]


def parse_rate_limit(limit: str):
    try:
        _calls, _period = limit.split('/')
        calls = int(_calls)
        period = parse_period(_period)
        return calls, period
    except:
        raise ValueError(f'Expected rate limit in format calls/period (10/1m), got: {limit}')


def apply_rate_limits(rate_limits: Optional[List[str]], func: Callable):
    if not rate_limits:
        return func
    if not isinstance(rate_limits, (list, set)):
        raise TypeError(f'Expected rate_limits to be a list or set, got: {(type(rate_limits))}')
    for rate_limit in rate_limits:
        calls, period = parse_rate_limit(rate_limit)
        func = limits(calls=calls, period=period)(func)
    return func

def random_string(length: int):
    return ''.join([random.choice(string.ascii_letters + string.digits) for n in range(length)])


# Decorators


def on_interval(name: str, interval: float):
    def wrapper(func: Callable):
        setattr(func, 'handler', name)
        setattr(func, 'kind', Kind.INTERVAL)
        setattr(func, 'interval', interval)
        detect_handler_properties(func)
        return func
    return wrapper


def on_command(name: str, rate_limits: Optional[List[str]] = None):
    def wrapper(func: Callable):
        setattr(func, 'handler', name)
        setattr(func, 'kind', Kind.COMMAND)
        detect_handler_properties(func)
        return apply_rate_limits(rate_limits, func)
    return wrapper


def on_event(name: str, rate_limits: Optional[List[str]] = None):
    def wrapper(func: Callable):
        setattr(func, 'handler', name)
        setattr(func, 'kind', Kind.EVENT)
        detect_handler_properties(func)
        return apply_rate_limits(rate_limits, func)
    return wrapper



def on_message(name: str, rate_limits: Optional[List[str]] = None):
    def wrapper(func: Callable):
        setattr(func, 'handler', name)
        setattr(func, 'kind', Kind.MESSAGE)
        detect_handler_properties(func)
        return apply_rate_limits(rate_limits, func)
    return wrapper


def on_request(name: str, rate_limits: Optional[List[str]] = None):
    def wrapper(func: Callable):
        setattr(func, 'handler', name)
        setattr(func, 'kind', Kind.REQUEST)
        detect_handler_properties(func)
        return apply_rate_limits(rate_limits, func)
    return wrapper


class BaseAgent(object):
    def __init__(self) -> None:
        self._spawned_tasks = {}  # Spawned tasks
        self._interval_handlers = {}
        self._event_handlers = {}
        self._command_handlers = {}
        self._message_handlers = {}
        self._request_handlers = {}
        self._handlers_map = {
            Kind.INTERVAL: self._interval_handlers,
            Kind.COMMAND: self._command_handlers,
            Kind.EVENT: self._event_handlers,
            Kind.MESSAGE: self._message_handlers,
            Kind.REQUEST: self._request_handlers,
        }
        self._detect_handlers()

    def configure_logging(self,
                          log_file='',
                          log_level='warning'):  # pragma: no cover
        if isinstance(log_level, str):
            log_level = getattr(logging, log_level.upper())
        if not log_file:
            log_file = 'zentropi-agent.log'
        configure_logging(
            log_file=log_file,
            log_level=log_level)

    def add_handler(self, kind: Kind, name: str, handler: Callable):
        if name in self._handlers_map[kind]:
            raise KeyError(f'Handler already set for kind {kind.name} {name}')
        self._handlers_map[kind][name] = handler

    def _detect_handlers(self):
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if not callable(attr):
                continue
            if getattr(attr, 'handler', None):
                name = getattr(attr, 'handler')
                kind = getattr(attr, 'kind')
                handler = attr
                self.add_handler(kind=kind, name=name, handler=handler)

    def on_interval(self, name: str, interval: float):
        def wrapper(func: Callable):
            setattr(func, 'interval', interval)
            detect_handler_properties(func)
            self.add_handler(Kind.INTERVAL, name, func)
            return func

        return wrapper

    def on_command(self, name: str, rate_limits: Optional[List[str]] = None):
        def wrapper(func: Callable):
            detect_handler_properties(func)
            self.add_handler(Kind.COMMAND, name, func)
            return apply_rate_limits(rate_limits, func)

        return wrapper

    def on_event(self, name: str, rate_limits: Optional[List[str]] = None):
        def wrapper(func: Callable):
            detect_handler_properties(func)
            self.add_handler(Kind.EVENT, name, func)
            return apply_rate_limits(rate_limits, func)

        return wrapper

    def on_message(self, name: str, rate_limits: Optional[List[str]] = None):
        def wrapper(func: Callable):
            detect_handler_properties(func)
            self.add_handler(Kind.MESSAGE, name, func)
            return apply_rate_limits(rate_limits, func)

        return wrapper

    def on_request(self, name: str, rate_limits: Optional[List[str]] = None):
        def wrapper(func: Callable):
            detect_handler_properties(func)
            self.add_handler(Kind.REQUEST, name, func)
            return apply_rate_limits(rate_limits, func)

        return wrapper

    def get_handler(self, kind: Kind, name: str):
        handlers = self._handlers_map[kind]
        if name in handlers:
            return handlers[name]
        elif '*' in handlers:
            return handlers['*']
        logger.debug(f'Unhandled frame {kind.name}: {name}')

    async def run_handler(self, kind: Kind, name: str, frame: Frame, timeout: float):
        args = []
        handler = self.get_handler(kind=kind, name=name)
        if not handler:
            return
        if handler.pass_frame:
            args.append(frame)
        try:
            if handler.run_async:
                return await asyncio.wait_for(
                    handler(*args),
                    timeout=timeout)
            return await asyncio.wait_for(
                sync_to_async(handler)(*args),
                timeout=timeout)
        except FuturesTimeoutError as e:
            msg = f'Handler timed out for {kind.name}: {name}'
            logger.warning(msg)
            raise TimeoutError(msg) from e
        except RateLimitException as e:
            msg = f'Rate limiting handler for {kind.name}: {name}'
            logger.warning(msg)
            raise RuntimeError(msg) from e

    async def watch(self, name: str, coro: Awaitable):
        try:
            logger.debug(f'Awaiting coro {name}')
            await coro
        except FuturesCancelledError:
            logger.debug(f'Spawned task {name} was cancelled')
        except Exception as e:
            msg = f'Encountered error in spawned task {name}'
            logger.fatal(msg)
            raise e
        finally:
            del self._spawned_tasks[name]

    def spawn(self, name: str, coro: Awaitable, single: bool = False):
        if single and name in self._spawned_tasks:
            msg = f'Could not spawn {name} as another instance is already running'
            logger.fatal(msg)
            raise RuntimeError(msg)
        elif not single:
            name = name + '-' + random_string(6)
        task = asyncio.create_task(self.watch(name, coro))
        self._spawned_tasks.update({name: task})
        return name, task

    async def cancel_spawned_tasks(self):
        tasks = []
        for name, task in self._spawned_tasks.items():
            logger.debug(f'Cancelling task {name}')
            tasks.append(task)
            task.cancel()
        await asyncio.gather(*tasks)
