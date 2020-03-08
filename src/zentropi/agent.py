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

    def run(self,
            loop: Optional[AbstractEventLoop] = None,
            shutdown_event: Optional[Event] = None) -> None:
        logger.info(f'Running agent {self.name}')
        self._loop = loop or asyncio.new_event_loop()
        self._loop.run_until_complete(self.start(shutdown_event))

    def stop(self) -> None:
        logger.info(f'Stopping agent {self.name}')
        self.shutdown_event.set()

    async def start(self, shutdown_event: Optional[Event] = None) -> None:
        self._loop = self._loop or asyncio.get_event_loop()
        self.shutdown_event = shutdown_event or Event()
        logger.info(f'Starting agent {self.name}')
        self._running = True
        # start interval tasks
        for int_name, int_task in self._handlers_interval.items():
            self.spawn(int_task(), name=int_name)
        if 'startup' in self._handlers_event:
            startup_handler = self._handlers_event['startup']
            startup_frame = Frame('startup', kind=Kind.EVENT)
            await startup_handler(startup_frame)
        await self.shutdown_event.wait()
        self._running = False
        logger.info(f'Shutting down agent {self.name}')
        if 'shutdown' in self._handlers_event:
            shutdown_handler = self._handlers_event['shutdown']
            shutdown_frame = Frame('startup', kind=Kind.EVENT)
            await shutdown_handler(shutdown_frame)
        for tname, task in self._spawned_tasks.items():
            task.cancel()

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
