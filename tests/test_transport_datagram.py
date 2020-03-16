import pytest

from zentropi import Agent
from zentropi import Frame
from zentropi.transport import datagram


class MockDatagram(object):
    def __init__(self, login_ok=True, send_ok=True, recv_ok=True):
        self._login_ok = login_ok
        self._send_ok = send_ok
        self._recv_ok = recv_ok
        self.frame = None

    async def connect(self, endpoint):
        return self

    async def close(self):
        pass

    async def send(self, data):
        if not self._send_ok:
            raise ConnectionAbortedError()
        frame = Frame.from_json(data.decode('utf-8'))
        if frame.name == 'login':
            if self._login_ok:
                self.frame = frame.reply('login-ok').to_json().encode('utf-8')
            else:
                self.frame = frame.reply('login-failed').to_json().encode('utf-8')
            return
        self.frame = data

    async def recv(self):
        if not self._recv_ok:
            raise ConnectionAbortedError()
        return self.frame, '127.0.0.1:9999'

    


@pytest.mark.asyncio
async def test_datagram_transport(monkeypatch):
    monkeypatch.setattr(datagram, 'asyncio_dgram', MockDatagram())
    dt = datagram.DatagramTransport()
    frame = Frame('test-frame')
    await dt.connect('dgram://127.0.0.1:6789/', 'test-token')
    assert dt.connected is True
    await dt.send(frame)
    assert dt.connection.frame 
    frame_recv = await dt.recv()
    assert frame_recv.name == 'test-frame'
    await dt.close()
    assert dt.connected is False


@pytest.mark.asyncio
@pytest.mark.xfail(raises=PermissionError)
async def test_datagram_transport_login_fail(monkeypatch):
    monkeypatch.setattr(datagram, 'asyncio_dgram', MockDatagram(login_ok=False))
    dt = datagram.DatagramTransport()
    frame = Frame('test-frame')
    await dt.connect('dgram://127.0.0.1:6789/', 'test-token')


@pytest.mark.asyncio
@pytest.mark.xfail(raises=ConnectionError)
async def test_datagram_transport_send_fail(monkeypatch):
    monkeypatch.setattr(datagram, 'asyncio_dgram', MockDatagram(send_ok=False))
    dt = datagram.DatagramTransport()
    frame = Frame('test-frame')
    await dt.connect('dgram://127.0.0.1:6789/', 'test-token')

@pytest.mark.asyncio
@pytest.mark.xfail(raises=ConnectionError)
async def test_datagram_transport_recv_fail(monkeypatch):
    monkeypatch.setattr(datagram, 'asyncio_dgram', MockDatagram(recv_ok=False))
    dt = datagram.DatagramTransport()
    frame = Frame('test-frame')
    await dt.connect('dgram://127.0.0.1:6789/', 'test-token')
