import asyncio
import logging
import random
import string
from asyncio import AbstractEventLoop
from asyncio import CancelledError
from asyncio import Event
from asyncio import Queue
from asyncio.tasks import Task
from signal import SIGINFO
from signal import SIGINT
from signal import SIGTERM
from typing import Optional
from typing import Tuple

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from . import configure_logging
from .frame import Frame
from .kind import Kind
from .transport.base import BaseTransport
from .transport.queue import QueueTransport
from .transport.websocket import WebsocketTransport

logger = logging.getLogger(__name__)


def random_string(length: int):
    return ''.join([random.choice(string.ascii_letters + string.digits) for n in range(length)])


def select_transport(endpoint: str):
    if endpoint.startswith('queue://'):
        return QueueTransport
    elif endpoint.startswith('ws://') or endpoint.startswith('wss://'):
        return WebsocketTransport


def clean_space_names(spaces):
    if isinstance(spaces, str):
        if ',' in spaces:
            spaces = {s.strip() for s in spaces.split(',')}
        else:
            spaces = {s.strip() for s in spaces.split(' ')}
    else:
        spaces = set(spaces)
    return spaces


class Agent(object):
    def __init__(self, name: str) -> None:
        self.name = name
        self._scheduler = None
        self._shutdown_trigger = None
        self._endpoint = ''
        self._token = ''
        self._transport = None
        self._connection = None
        self._connected = False
        self._loop = None
        self._join_all_spaces = True
        self._joined_spaces = set()
        self._running = False
        self._async_tasks = {}
        self._interval_handlers = {}
        self._event_handlers = {}
        self._command_handlers = {}
        self._send_queue = None

    ### Logging

    def configure_logging(self,
                          log_file='',
                          log_level='warning'):
        if isinstance(log_level, str):
            log_level = getattr(logging, log_level.upper())
        if not log_file:
            log_file = 'zentropi-agent-{}.log'.format(self.name)
        configure_logging(
            log_file=log_file,
            log_level=log_level)

    ### Signal Handling

    def _siginfo_handler(self, *args) -> None:  # pragma: no cover
        print(f'Agent {self.name}.')
        print(f'Running {len(self._async_tasks)} tasks:')
        for task_id in self._async_tasks:
            print(f'\t{task_id}')

    def _sigint_handler(self, *args) -> None:  # pragma: no cover
        print('')
        logger.warning('Received keyboard interrupt.')
        self._shutdown_trigger.set()

    def _sigterm_handler(self, *args) -> None:  # pragma: no cover
        logger.warning('Received termination signal.')
        self._shutdown_trigger.set()

    ### Run/Start/Stop

    def run(self,
            endpoint: Optional[str] = '',
            token: Optional[str] = '',
            join_all_spaces=True,
            loop: Optional[AbstractEventLoop] = None,
            shutdown_trigger: Optional[Event] = None,
            transport: Optional[BaseTransport] = None) -> None:
        logger.info(f'Running agent {self.name}')
        self._endpoint = endpoint
        self._token = token
        self._transport = transport
        self._join_all_spaces = join_all_spaces
        if shutdown_trigger:
            self._loop = loop or asyncio.get_event_loop()
        else:
            self._loop = loop or asyncio.new_event_loop()
        self._loop.run_until_complete(self.start(shutdown_trigger))

    async def start(self, shutdown_trigger: Optional[Event] = None) -> None:
        logger.info(f'Starting agent {self.name}')
        self._loop = self._loop or asyncio.get_event_loop()
        self._loop.add_signal_handler(SIGINT, self._sigint_handler)
        self._loop.add_signal_handler(SIGTERM, self._sigterm_handler)
        self._loop.add_signal_handler(SIGINFO, self._siginfo_handler)
        self._shutdown_trigger = shutdown_trigger or Event()
        self._send_queue = Queue()
        self._scheduler = AsyncIOScheduler()
        self._scheduler.add_job(self._ensure_connection, 'interval', seconds=5)
        self._scheduler.start()
        logger.info(f'Agent {self.name} is running.')
        self._running = True
        await self._ensure_connection()
        await self._run_startup_handler()
        await self._start_interval_handlers()
        await self._shutdown_trigger.wait()
        logger.info(f'Agent {self.name} is stopping.')
        await self._run_shutdown_handler()
        await self._close_connection()
        await self._cancel_async_tasks()
        self._running = False

    def stop(self) -> None:
        logger.info(f'Stopping agent {self.name}')
        self._scheduler.pause()
        self._shutdown_trigger.set()

    ### Asynchronous Tasks

    async def watch(self, name, coro):
        try:
            await coro
        except CancelledError:
            logger.debug(f'Task {name} was cancelled.')
        except Exception as e:
            logger.exception(e)
            self.stop()
        finally:
            del self._async_tasks[name]

    def spawn(self, name, coro, ensure_single_instance=False):
        if ensure_single_instance and name in self._async_tasks:
            logger.fatal(f'Could not spawn {name} as another instance is already running.')
            self.stop()
        elif not ensure_single_instance:
            name = name + '-' + random_string(6)
        task = self._loop.create_task(self.watch(name, coro))
        self._async_tasks.update({name: task})
        return name, task

    async def _cancel_async_tasks(self):
        for task_id, task in self._async_tasks.items():
            logger.debug(f'Cancelling task {task_id}')
            task.cancel()

    ### Connection

    async def _ensure_connection(self):
        logger.debug('Checking connection status')
        if self._connected:
            logger.debug('Agent is connected')
            return
        if not (self._endpoint and self._token):
            logger.debug('Skip connecting as endpoint and token not provided')
            return
        if not self._transport:
            self._transport = select_transport(self._endpoint)
        self._connection = self._transport()
        try:
            await self._connection.connect(
                endpoint=self._endpoint,
                token=self._token)
            self._connected = True
        except PermissionError:
            logger.fatal(f'Login failed when connecting to {self._endpoint} with token {self._token!r}')
            await self._connection.close()
            self.stop()
        except Exception as e:
            logger.info(f'Unable to connect to {self._endpoint}, will try again later.')
            return
        try:
            self.spawn(
                'frame-receive-loop',
                self._frame_receive_loop(),
                ensure_single_instance=True)
            if self._joined_spaces:
                await self.join(self._joined_spaces)
            elif self._join_all_spaces:
                await self.join('*')
            self.spawn(
                'frame-send-loop',
                self._frame_send_loop(),
                ensure_single_instance=True)
        except Exception as e:
            logger.exception(e)
            self.stop()

    async def _frame_receive_loop(self):
        try:
            while self._connected:
                frame = await self._connection.recv()
                await self.handle_frame(frame)
        except CancelledError:
            logger.debug('Receive loop cancelled')
        except ConnectionError:
            logger.warning('Connection was closed.')
            self._connected = False

    async def _frame_send_loop(self):
        try:
            while self._connected:
                frame = await self._send_queue.get()
                await self._connection.send(frame)
        except CancelledError:
            logger.debug('Receive loop cancelled')
        except ConnectionError:
            logger.warning('Connection was closed.')
            self._connected = False

    async def _close_connection(self):
        if not self._connected:
            logger.warning('Called close on a disconnected connection.')
            return
        await self._connection.close()

    ### Send Frames

    async def send(self, frame: Frame, queue=True):
        if not (self._endpoint and self._token):
            logger.debug('Agent not connected, handling sent frame locally')
            await self.handle_frame(frame)
            return
        if queue:
            logger.debug('Queue frame for remote server')
            await self._send_queue.put(frame)
        else:
            logger.debug('Sending frame to remote server')
            try:
                await self._connection.send(frame)
            except ConnectionError:
                logger.warning('Connection was closed.')
                self._connected = False

    async def command(self, _name: str, _queue=False, **_data):
        frame = Frame(_name, kind=Kind.COMMAND, data=_data)
        await self.send(frame, queue=_queue)

    async def emit(self, _name: str, **_data):
        frame = Frame(_name, kind=Kind.EVENT, data=_data)
        await self.send(frame)

    ### Protocol Commands

    async def join(self, spaces):
        spaces = clean_space_names(spaces)
        logger.info(f'Joining spaces: {spaces!r}')
        [self._joined_spaces.add(s) for s in spaces]
        await self.command('join', spaces=list(spaces))

    async def leave(self, spaces):
        spaces = clean_space_names(spaces)
        logger.info(f'Leaving spaces: {spaces!r}')
        [self._joined_spaces.remove(s) for s in spaces]
        await self.command('leave', spaces=list(spaces))

    ### Frame Handlers

    def on_interval(self, _name: str, interval: float):
        def wrapper(func):
            if _name in self._interval_handlers:
                raise KeyError(f'Interval handler already set for {_name!r}')
            self._interval_handlers[(_name, interval)] = func
            return func

        return wrapper

    def on_command(self, _name):
        def wrapper(func):
            if _name in self._command_handlers:
                raise KeyError(f'Command handler already set for {_name!r}')
            self._command_handlers[_name] = func
            return func

        return wrapper

    def on_event(self, _name):
        def wrapper(func):
            if _name in self._event_handlers:
                raise KeyError(f'Event handler already set for {_name!r}')
            self._event_handlers[_name] = func
            return func

        return wrapper

    async def get_handler(self, frame: Frame):
        kind = frame.kind
        name = frame.name
        if kind == Kind.COMMAND:
            handlers = self._command_handlers
        elif kind == Kind.EVENT:
            handlers = self._event_handlers
        else:
            raise KeyError(f'Unknown kind {kind} in {name}')
        if name in handlers:
            handler = handlers[name]
        elif '*' in handlers:
            handler = handlers['*']
        else:
            logger.warning(f'Unhandled frame: {frame.name} {frame.data}')
            return
        return handler

    async def handle_frame(self, frame: Frame):
        kind = frame.kind
        name = frame.name
        handler = await self.get_handler(frame)
        if not handler:
            return
        self.spawn(
            f'handler-{frame.name}-{frame.uuid}', 
            self._run_handler(handler, frame),
            ensure_single_instance=True)

    async def _run_handler(self, handler, frame: Frame):
        response = await handler(frame)
        if not response:
            return
        logger.debug(f'Handler for frame {frame.name} returned response {response!r}')

    async def _start_interval_handlers(self):
        for int_spec, int_task in self._interval_handlers.items():
            name, interval = int_spec
            logger.debug(f'Starting interval handler: {name} @ {interval} seconds.')
            self._scheduler.add_job(int_task, 'interval', seconds=interval)

    async def _run_startup_handler(self):
        if 'startup' in self._event_handlers:
            logger.debug(f'Running startup event handler.')
            startup_handler = self._event_handlers['startup']
            startup_frame = Frame('startup', kind=Kind.EVENT)
            await startup_handler(startup_frame)

    async def _run_shutdown_handler(self):
        if 'shutdown' in self._event_handlers:
            logger.debug(f'Running shutdown event handler.')
            shutdown_handler = self._event_handlers['shutdown']
            shutdown_frame = Frame('shutdown', kind=Kind.EVENT)
            await shutdown_handler(shutdown_frame)
