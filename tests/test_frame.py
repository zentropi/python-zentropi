import json
from logging import exception
import pytest
from zentropi.protocol.frame import Frame, binary_format

frame_as_dict = {'name': 'test-frame', 'data': {'item': 'one'}}
frame_as_json = json.dumps(frame_as_dict)

def test_frame():
    frame = Frame('test-frame', data={'item': 'one'})
    assert frame.name == 'test-frame'
    assert frame.data == {'item': 'one'}


def test_frame_from_dict():
    frame = Frame.from_dict(frame_as_dict)
    assert frame.name == 'test-frame'
    assert frame.data == {'item': 'one'}


def test_frame_to_dict():
    frame = Frame('test-frame', data={'item': 'one'})
    fdict = frame.to_dict() 
    assert fdict['name'] == 'test-frame'
    assert fdict['data'] == {'item': 'one'}


def test_frame_from_json():
    frame = Frame.from_json(frame_as_json)
    assert frame.name == 'test-frame'
    assert frame.data == {'item': 'one'}


def test_frame_to_json():
    frame = Frame('test-frame', data={'item': 'one'})
    fjson = frame.to_json()
    fdict = json.loads(fjson)
    assert fdict['name'] == 'test-frame'
    assert fdict['data'] == {'item': 'one'}


def test_binary_format():
    bformat = binary_format(10, 10, 10)
    assert bformat == b'!?LLLH32s10s10s10s'

def test_frame_as_bytes():
    frame = Frame('test-frame', data={'item': 'one'}, uuid='91328e1343924966b3c673c2d1264989')
    frame_as_bytes = frame.to_bytes()
    assert isinstance(frame_as_bytes, bytes)
    frame2 = Frame.from_bytes(frame_as_bytes)
    assert frame2.name == 'test-frame'    
    assert frame.data == {'item': 'one'}
    assert frame.uuid == '91328e1343924966b3c673c2d1264989'
    assert len(frame_as_bytes) == 74

def test_frame_repr():
    frame = Frame('test-frame', data={'item': 'one'}, uuid='91328e1343924966b3c673c2d1264989')
    frame_repr = str(frame)
    assert frame_repr == "Frame(name='test-frame', kind=2, uuid='91328e1343924966b3c673c2d1264989', data={'item': 'one'}, meta={})"


@pytest.mark.xfail(raises=AssertionError)
def test_data_not_json_serializable():
    data = open(__file__, 'r')
    Frame('test-frame', data=data)


@pytest.mark.xfail(raises=AssertionError)
def test_oversized_data_causes_exception():
    data = {k:'*' * k for k in range(100)}
    Frame('test-frame', data=data)



@pytest.mark.xfail(raises=AssertionError)
def test_meta_not_json_serializable():
    meta = open(__file__, 'r')
    Frame('test-frame', meta=meta)


@pytest.mark.xfail(raises=AssertionError)
def test_oversized_meta_causes_exception():
    meta = {k:'*' * k for k in range(100)}
    Frame('test-frame', meta=meta)


def test_oversized_meta_works_with_large():
    meta = {k:'*' * k for k in range(100)}
    Frame('test-frame', meta=meta, large=True)


def test_frame_reply_with_name_specified():
    frame = Frame.from_dict(frame_as_dict)
    reply = frame.reply('reply-frame')
    assert reply.meta['reply_to'] == frame.uuid
    assert reply.name == 'reply-frame'

def test_frame_reply_with_default_name():
    frame = Frame.from_dict(frame_as_dict)
    reply = frame.reply()
    assert reply.meta['reply_to'] == frame.uuid
    assert reply.name == frame.name

def test_frame_meta_passed_in():
    frame = Frame.from_dict(frame_as_dict)
    reply = frame.reply(meta={'item': 'one'})
    assert reply.meta['reply_to'] == frame.uuid
    assert reply.name == frame.name
    assert 'item' in reply.meta
