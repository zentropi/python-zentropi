import json
from uuid import uuid4

import pytest

from zentropi import Frame
from zentropi import Kind
from zentropi.frame import deflate_dict


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


def test_frame_to_dict():
    uuid = uuid4().hex
    frame_as_dict = {'name': 'test-frame', 'uuid': uuid, 'kind': Kind.EVENT}
    f = Frame('test-frame', uuid=uuid)
    fdict = f.to_dict()
    assert fdict == frame_as_dict


def test_frame_from_dict():
    uuid = uuid4().hex
    frame_as_dict = {'name': 'test-frame', 'uuid': uuid, 'kind': Kind.EVENT}
    f = Frame.from_dict(frame_as_dict)
    assert f.name == 'test-frame'
    assert f.uuid == uuid
    assert f.kind == Kind.EVENT


def test_frame_to_json():
    uuid = uuid4().hex
    frame_as_dict = {'name': 'test-frame', 'uuid': uuid, 'kind': Kind.EVENT}
    f = Frame('test-frame', uuid=uuid)
    fjson = f.to_json()
    fdict = json.loads(fjson)
    assert fdict == frame_as_dict


def test_frame_from_json():
    uuid = uuid4().hex
    frame_as_dict = {'name': 'test-frame', 'uuid': uuid, 'kind': Kind.EVENT}
    frame_as_json = json.dumps(frame_as_dict)
    f = Frame.from_json(frame_as_json)
    assert f.name == 'test-frame'
    assert f.uuid == uuid
    assert f.kind == Kind.EVENT


def test_frame_reply():
    f = Frame('test-frame')
    freply = f.reply()
    assert freply.meta.get('reply_to') == f.uuid


def test_frame_reply_with_name():
    f = Frame('test-frame')
    freply = f.reply('test-reply')
    assert freply.name == 'test-reply'
    assert freply.meta.get('reply_to') == f.uuid


def test_frame_reply_with_data():
    data = {'test': 'item'}
    f = Frame('test-frame')
    freply = f.reply(data=data)
    assert freply.meta.get('reply_to') == f.uuid
    assert freply.data.get('test') == 'item'


def test_frame_reply_with_meta():
    meta = {'test': 'item'}
    f = Frame('test-frame')
    freply = f.reply(meta=meta)
    assert freply.meta.get('reply_to') == f.uuid
    assert freply.meta.get('test') == 'item'


def test_delate_dict():
    inflated_dict = {'test': 'item', 'empty': ''}
    deflated_dict = deflate_dict(inflated_dict)
    assert deflated_dict == {'test': 'item'}


@pytest.mark.xfail(raises=TypeError)
def test_frame_validate_name_must_be_string():
    Frame(42)


@pytest.mark.xfail(raises=ValueError)
def test_frame_validate_name_must_not_be_empty():
    Frame('     ')


@pytest.mark.xfail(raises=TypeError)
def test_frame_validate_kind_must_be_integer():
    Frame('test-frame', kind='event')


@pytest.mark.xfail(raises=ValueError)
def test_frame_validate_kind_must_be_within_range():
    Frame('test-frame', -1)


@pytest.mark.xfail(raises=TypeError)
def test_frame_validate_uuid_must_be_string():
    Frame('test-frame', uuid=42)


@pytest.mark.xfail(raises=ValueError)
def test_frame_validate_uuid_must_not_be_empty():
    Frame('test-frame', uuid='     ')


@pytest.mark.xfail(raises=TypeError)
def test_frame_validate_data_must_be_dict():
    Frame('test-frame', data='expect failure')


@pytest.mark.xfail(raises=TypeError)
def test_frame_validate_meta_must_be_dict():
    Frame('test-frame', meta='expect failure')
