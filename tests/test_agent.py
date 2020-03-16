import asyncio
from asyncio import Event

import pytest
from zentropi import Agent
from zentropi.agent import clean_space_names
from zentropi.agent import select_transport
from zentropi.agent import random_string
from zentropi.transport.base import BaseTransport
from zentropi.transport.datagram import DatagramTransport
from zentropi.transport.queue import QueueTransport
from zentropi.transport.websocket import WebsocketTransport


def test_random_string():
    rs = random_string(length=10)
    assert len(rs) == 10


def test_select_transport_queue():
    transport = select_transport('queue://')
    assert transport == QueueTransport


def test_select_transport_websocket():
    transport = select_transport('ws://')
    assert transport == WebsocketTransport


def test_select_transport_websocket_tls():
    transport = select_transport('wss://')
    assert transport == WebsocketTransport


def test_select_transport_datagram():
    transport = select_transport('dgram://')
    assert transport == DatagramTransport


@pytest.mark.xfail(raises=ValueError)
def test_select_transport_invalid():
    select_transport('boogie://')


def test_clean_space_names_from_str():
    spaces = clean_space_names('this, this, that, test')
    assert spaces == {'this', 'that', 'test'}

    spaces = clean_space_names('this that test test')
    assert spaces == {'this', 'that', 'test'}


def test_clean_space_names_from_iterable():
    spaces = clean_space_names(['this', 'that', 'that', 'test'])
    assert spaces == {'this', 'that', 'test'}


def test_agent_init():
    agent = Agent('test-agent')
    assert agent.name == 'test-agent'

# def test_agent_run():
#     import threading, time
#     agent = Agent('test-agent')
#     threaded_agent = threading.Thread(target=agent.run, kwargs={'handle_signals': False})
#     threaded_agent.start()
#     time.sleep(0.5)
#     assert agent._running is True
#     agent.stop()
#     threaded_agent.join()
#     assert agent._running is False

@pytest.mark.asyncio
async def test_agent_stop_with_shutdown_trigger():
    agent = Agent('test-agent')
    shutdown_trigger = Event()
    task = asyncio.create_task(agent.start(shutdown_trigger=shutdown_trigger))
    await asyncio.sleep(0)
    assert agent._running is True
    assert agent._shutdown_trigger == shutdown_trigger
    shutdown_trigger.set()
    await asyncio.gather(task)
    assert agent._running is False

@pytest.mark.asyncio
async def test_agent_stop_with_stop():
    agent = Agent('test-agent')
    task = asyncio.create_task(agent.start())
    await asyncio.sleep(0)
    assert agent._running is True
    agent.stop()
    await asyncio.gather(task)
    assert agent._running is False
