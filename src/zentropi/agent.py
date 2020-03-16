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

from . import KB
from . import configure_logging
from .base_agent import BaseAgent
from .frame import Frame
from .kind import Kind
from .mdns import resolve_zeroconf_address
from .transport.base import BaseTransport
from .transport.datagram import DatagramTransport
from .transport.queue import QueueTransport
from .transport.websocket import WebsocketTransport

logger = logging.getLogger(__name__)

INTERNAL_EVENT_NAMES = {'startup', 'shutdown'}


def random_string(length: int):
    return ''.join([random.choice(string.ascii_letters + string.digits) for n in range(length)])


def select_transport(endpoint: str):
    if endpoint.startswith('queue://'):
        return QueueTransport
    elif endpoint.startswith('ws://') or endpoint.startswith('wss://'):
        return WebsocketTransport
    elif endpoint.startswith('dgram://'):
        return DatagramTransport


def clean_space_names(spaces):
    if isinstance(spaces, str):
        if ',' in spaces:
            spaces = {s.strip() for s in spaces.split(',')}
        else:
            spaces = {s.strip() for s in spaces.split(' ')}
    else:
        spaces = set(spaces)
    return spaces


class Agent(BaseAgent):
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
        self._send_queue = None
        self._frame_max_size = 1 * KB
        self._response_wait_queues = {}
        super().__init__()

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
            transport: Optional[BaseTransport] = None,
            handle_signals=True) -> None:
        logger.info(f'Running agent {self.name}')
        self._endpoint = endpoint
        self._token = token
        self._transport = transport
        self._join_all_spaces = join_all_spaces
        if shutdown_trigger:
            self._loop = loop or asyncio.get_event_loop()
        else:
            self._loop = loop or asyncio.new_event_loop()
        self._loop.run_until_complete(self.start(
            endpoint=endpoint,
            token=token,
            join_all_spaces=join_all_spaces,
            loop=loop,
            shutdown_trigger=shutdown_trigger,
            transport=transport,
            handle_signals=handle_signals,
            ))

    async def start(self,
            endpoint: Optional[str] = '',
            token: Optional[str] = '',
            join_all_spaces=True,
            loop: Optional[AbstractEventLoop] = None,
            shutdown_trigger: Optional[Event] = None,
            transport: Optional[BaseTransport] = None,
            handle_signals=True) -> None:
        logger.info(f'Starting agent {self.name}')
        self._endpoint = endpoint
        self._token = token
        self._transport = transport
        self._join_all_spaces = join_all_spaces
        self._loop = self._loop or asyncio.get_event_loop()
        if handle_signals:
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
        await self.cancel_spawned_tasks()
        self._running = False

    def stop(self) -> None:
        logger.info(f'Stopping agent {self.name}')
        self._scheduler.pause()
        self._shutdown_trigger.set()

    ### Asynchronous Tasks

    async def _cancel_send_recv_loops(self):
        tasks = []
        for name in {'frame-send-loop', 'frame-receive-loop'}:
            if name in self._spawned_tasks:
                task = self._spawned_tasks[name]
                tasks.append(task)
                task.cancel()
        await asyncio.gather(*tasks)

    ### Connection

    async def _ensure_connection(self):
        logger.debug('Checking connection status')
        if self._connected:
            logger.debug('Agent is connected')
            return
        if not self._endpoint and not self._token:
            logger.debug('Skip connecting as endpoint and token not provided')
            return
        if not self._endpoint and self._token:
            try:
                self._endpoint = resolve_zeroconf_address(name='zencelium', schema='ws')
                logger.info(f'Found server through zeroconf at {self._endpoint}')
            except Exception as e:
                logger.fatal('Unable to resolve address through zeroconf')
                self.stop()
                return
                # raise ConnectionError('Unable to resolve address through zeroconf')
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
            await self._cancel_send_recv_loops()
            self.spawn(
                'frame-receive-loop',
                self._frame_receive_loop(),
                single=True)
            await self.filter_frames()
            if self._joined_spaces:
                await self.join(self._joined_spaces)
            elif self._join_all_spaces:
                await self.join('*')
            self.spawn(
                'frame-send-loop',
                self._frame_send_loop(),
                single=True)
        except Exception as e:
            logger.exception(e)
            self.stop()

    async def _frame_receive_loop(self):
        try:
            while self._connected:
                frame = await self._connection.recv()
                if frame.kind == Kind.EVENT and frame.name in INTERNAL_EVENT_NAMES:
                    logger.debug(f'Skip frame with internal name: {frame.to_dict()!r}')
                    continue
                if frame.kind == Kind.RESPONSE:
                    response_to_uuid = frame.meta.get('reply_to')
                    if response_to_uuid in self._response_wait_queues:
                        await self._response_wait_queues[response_to_uuid].put(frame)
                    continue
                await self.handle_frame(frame)
        except CancelledError:
            logger.debug('Receive loop cancelled')
        except ConnectionError:
            logger.warning('Connection closed')
            self._connected = False

    async def _frame_send_loop(self):
        try:
            while self._connected:
                frame = await self._send_queue.get()
                await self._connection.send(frame)
        except CancelledError:
            logger.debug('Receive loop cancelled')
        except ConnectionError:
            logger.warning('Connection closed')
            self._connected = False

    async def _close_connection(self):
        if not self._connected:
            logger.debug('Called close on a disconnected connection.')
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

    event = emit

    async def message(self, _name: str, text='', locale='en_US', **_data):
        meta = {'locale': locale}
        _data.update({'text': text})
        frame = Frame(_name, kind=Kind.MESSAGE, data=_data, meta=meta)
        await self.send(frame)

    async def request(self, _name: str, timeout: int, **_data):
        frame = Frame(_name, kind=Kind.REQUEST, data=_data)
        await self.send(frame)
        try:
            return await asyncio.wait_for(self._wait_for_response(frame), timeout=timeout)
        except Exception as e:
            raise TimeoutError('Timed out waiting for response') from e

    async def _wait_for_response(self, frame: Frame):
        self._response_wait_queues[frame.uuid] = Queue()
        try:
            response = await self._response_wait_queues[frame.uuid].get()
            if '_response' in response.data:
                return response.data['_response']
            return response.data
        finally:
            del self._response_wait_queues[frame.uuid]

    ### Standard frame formatters

    async def measure(self, _name: str, value: float, unit: str):
        await self.emit(_name, value=value, unit=unit)

    async def notify(self, _message: str, **_data):
        await self.message('notification', text=_message, **_data)

    async def alert(self, _message: str, **_data):
        await self.message('alert', text=_message, **_data)

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

    async def filter_frames(self):
        filters = {'event': {}, 'message': {}, 'size': self._frame_max_size}
        filters['event'] = list(set(self._event_handlers.keys()) - INTERNAL_EVENT_NAMES)
        filters['message'] = list(self._message_handlers.keys())
        filters['request'] = list(self._request_handlers.keys())
        await self.command('filter', names=filters, size=self._frame_max_size)

    async def handle_frame(self, frame: Frame):
        kind = frame.kind
        name = frame.name
        if not self.get_handler(kind, name):
            return
        self.spawn(
            f'handler-{frame.name}-{frame.uuid}',
            self.handle_response(frame),
            single=True)

    async def handle_response(self, frame: Frame):
        kind = frame.kind
        name = frame.name
        response = await self.run_handler(kind, name, frame, timeout=10)
        if not response:
            return
        logger.debug(f'Handler for frame {frame.name} returned response {response!r}')
        if isinstance(response, dict):
            await self.send(frame.reply(data=response))
        else:
            await self.send(frame.reply(data={'_response': response}))

    async def _start_interval_handlers(self):
        for name, int_task in self._interval_handlers.items():
            interval = int_task.interval
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
