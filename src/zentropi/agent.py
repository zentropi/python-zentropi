import asyncio
import logging
from asyncio import AbstractEventLoop
from asyncio import Event
from asyncio.tasks import Task
from typing import Optional, Tuple
from uuid import uuid4

logger = logging.getLogger(__name__)


class Agent(object):
    def __init__(self, name: str) -> None:
        self.name = name
        self.shutdown_event = None
        self._running = False
        self._loop = None
        self._spawned_tasks = {}

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
        await self.shutdown_event.wait()
        self._running = False
        logger.info(f'Shutting down agent {self.name}')

    def spawn(self, coro) -> Tuple[str, Task]:
        async def watch(task_id, coro):
            try:
                await coro
            except Exception as e:
                logger.exception(e)
                self.stop()
            finally:
                del self._spawned_tasks[task_id]
        task_id = uuid4().hex
        task = self._loop.create_task(watch(task_id, coro))
        self._spawned_tasks.update({task_id: task})
        return task_id, task
