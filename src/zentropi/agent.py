import asyncio
import logging
from asyncio import AbstractEventLoop
from asyncio import CancelledError
from asyncio import Event
from asyncio.tasks import Task
from typing import Optional
from typing import Tuple
from uuid import uuid4

from .frame import Frame
from .kind import Kind
from .transport.base import BaseTransport
from .transport.queue import QueueTransport
from .transport.websocket import WebsocketTransport

logger = logging.getLogger(__name__)


class Agent(object):
    def __init__(self, name: str) -> None:
        self.name = name
        self.shutdown_event = None
        self._running = False
        self._loop = None
        self._spawned_tasks = {}
        self._handlers_interval = {}
        self._handlers_event = {}
        self._transport = None
        self._connected = False

    def run(self,
            loop: Optional[AbstractEventLoop] = None,
            shutdown_event: Optional[Event] = None) -> None:
        logger.info(f'Running agent {self.name}')
        self._loop = loop or asyncio.new_event_loop()
        self._loop.run_until_complete(self.start(shutdown_event))

    def stop(self) -> None:
        logger.info(f'Stopping agent {self.name}')
        self.shutdown_event.set()

    async def _start_interval_tasks(self):
        for int_name, int_task in self._handlers_interval.items():
            self.spawn(int_task(), name=int_name)

    async def _run_startup_handler(self):
        if 'startup' in self._handlers_event:
            startup_handler = self._handlers_event['startup']
            startup_frame = Frame('startup', kind=Kind.EVENT)
            await startup_handler(startup_frame)

    async def _run_shutdown_handler(self):
        if 'shutdown' in self._handlers_event:
            shutdown_handler = self._handlers_event['shutdown']
            shutdown_frame = Frame('startup', kind=Kind.EVENT)
            await shutdown_handler(shutdown_frame)

    async def _cancel_spawned_tasks(self):
        for task_id, task in self._spawned_tasks.items():
            logger.debug(f'Cancelling task {task_id}')
            task.cancel()

    async def start(self, shutdown_event: Optional[Event] = None) -> None:
        self._loop = self._loop or asyncio.get_event_loop()
        self.shutdown_event = shutdown_event or Event()
        logger.info(f'Starting agent {self.name}')
        self._running = True
        await self._start_interval_tasks()
        await self._run_startup_handler()
        await self.shutdown_event.wait()
        self._running = False
        logger.info(f'Shutting down agent {self.name}')
        await self._run_shutdown_handler()
        await self._cancel_spawned_tasks()

    def spawn(self, coro, name='') -> Tuple[str, Task]:
        async def watch(task_id, coro):
            try:
                await coro
            except CancelledError:
                pass
            except Exception as e:
                logger.exception(e)
                self.stop()
            finally:
                del self._spawned_tasks[task_id]
        task_id = name or uuid4().hex
        task = self._loop.create_task(watch(task_id, coro))
        self._spawned_tasks.update({task_id: task})
        return task_id, task

    def on_interval(self, _name: str, interval: float):
        def wrapper(func):
            if _name in self._handlers_interval:
                raise KeyError(f'Handler already set for {_name!r}')

            async def run_on_interval():
                count = 1
                while self._running:
                    await asyncio.sleep(interval)  # pragma: no cover
                    frame = Frame('interval-elapsed', kind=Kind.EVENT, data={'count': count})
                    await func(frame)
                    count += 1
            self._handlers_interval[_name] = run_on_interval
            return func
        return wrapper

    def on_event(self, _name):
        def wrapper(func):
            if _name in self._handlers_event:
                raise KeyError(f'Handler already set for {_name!r}')
            self._handlers_event[_name] = func
            return func

        return wrapper

    async def event(self, _name, **_data):
        frame = Frame(_name, kind=Kind.EVENT, data=_data)
        if not self._transport and _name in self._handlers_event:
            handler = self._handlers_event[_name]
            self.spawn(handler(frame))
        else:
            await self._transport.send(frame)

    async def connect(self,
                      endpoint: str,
                      token: str,
                      transport: Optional[BaseTransport] = None):
        if transport:
            self._transport = transport
        elif endpoint.startswith('queue://'):
            self._transport = QueueTransport()
        elif endpoint.startswith('ws://') or endpoint.startswith('wss://'):
            self._transport = WebsocketTransport()
        else:
            raise RuntimeError(f'Unable to select a transport for endpoint {endpoint!r}')
        await self._transport.connect(endpoint, token)
        self._connected = True
        self.spawn(self._recv_loop(), name='recv-loop')

    async def close(self):
        await self._transport.close()
        self._connected = False
        if 'recv-loop' in self._spawned_tasks:
            self._spawned_tasks['recv-loop'].cancel()

    async def _recv_loop(self):
        try:
            while self._connected:
                frame = await self._transport.recv()
                handler = self._handlers_event[frame.name]
                self.spawn(handler(frame))
        except CancelledError:
            logger.debug('Receive loop cancelled')
        except ConnectionError:
            logger.debug('Connection was closed.')
