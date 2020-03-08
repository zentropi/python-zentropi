from uuid import uuid4

import pytest

from zentropi import Frame
from zentropi import Kind


@pytest.mark.xfail(raises=TypeError)
def test_frame_creation_requires_name():
    Frame()


def test_frame_creation_with_name():
    f = Frame('test-frame')
    assert f.name == 'test-frame'
    assert len(f.uuid) == 32
    assert f.kind == Kind.EVENT
    assert f.data == {}
    assert f.meta == {}


def test_frame_creation_with_kind():
    f = Frame('test-frame', kind=1)
    assert f.name == 'test-frame'
    assert f.kind == 1


def test_frame_creation_with_uuid():
    uuid = uuid4().hex
    f = Frame('test-frame', uuid=uuid)
    assert f.name == 'test-frame'
    assert f.uuid == uuid


def test_frame_creation_with_data():
    data = {'test': 'item'}
    f = Frame('test-frame', data=data)
    assert f.name == 'test-frame'
    assert f.data == data


def test_frame_creation_with_meta():
    meta = {'test': 'item'}
    f = Frame('test-frame', meta=meta)
    assert f.name == 'test-frame'
    assert f.meta == meta
