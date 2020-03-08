import pytest

from zentropi import Frame
from zentropi import QueueTransport


@pytest.mark.asyncio
async def test_queue_transport():
    qt = QueueTransport()
    frame = Frame('test-frame')
    await qt.connect('test-token')
    assert qt.connected is True
    await qt.send(frame)
    frame_sent = await qt.queue_send.get()
    assert frame == frame_sent
    frame_ = Frame('test-recv')
    await qt.queue_recv.put(frame_)
    frame_recv = await qt.recv()
    assert frame_ == frame_recv
    await qt.close()
    assert qt.connected is False
