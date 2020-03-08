from uuid import uuid4

import pytest

from zentropi import Frame


@pytest.mark.xfail(raises=TypeError)
def test_frame_creation_requires_name():
    Frame()


def test_frame_creation_with_only_name():
    f = Frame('test-frame')
    assert f.name == 'test-frame'


def test_frame_creation_with_uuid():
    uuid = uuid4().hex
    f = Frame('test-frame', uuid=uuid)
    assert f.name == 'test-frame'
    assert f.uuid == uuid
