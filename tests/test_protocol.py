import pytest

from zentropi.protocol.frame import Frame
from zentropi.protocol.kind import Kind
from zentropi.protocol.protocol import Action
from zentropi.protocol.protocol import BinaryProtocol
from zentropi.protocol.protocol import JSONProtocol

def test_client_json_protocol():
    client_protocol = JSONProtocol()
    server_protocol = JSONProtocol(server=True)
    c_action, c_auth_frame = client_protocol.send_auth('agent-uuid', 'agent-token')

    s_action, s_auth_frame = server_protocol.parse(c_auth_frame)
    assert c_action == Action.SEND_FRAME
    assert s_action == Action.RECV_AUTH
    assert client_protocol._agent_uuid == 'agent-uuid'
    assert client_protocol._token == 'agent-token'
    assert server_protocol._agent_uuid == 'agent-uuid'
    assert server_protocol._token == 'agent-token'
    assert s_auth_frame.name == 'login'
    assert s_auth_frame.data['agent_uuid'] == 'agent-uuid'
    assert s_auth_frame.data['token'] == 'agent-token'

    c_action, c_frame = client_protocol.send(Frame('hello'))
    assert c_action == Action.SEND_FRAME
    assert isinstance(c_frame, str)
    s_action, s_frame = server_protocol.parse(c_frame)
    assert s_action == Action.RECV_FRAME
    assert s_frame.name == 'hello'

    s_action, s_frame = server_protocol.send(Frame('ping', Kind.COMMAND))
    c_action, c_frame = client_protocol.parse(s_frame)
    assert c_action == Action.SEND_FRAME
    assert c_frame.name == 'pong'


@pytest.mark.xfail(raises=PermissionError)
def test_client_protocol_exception_if_no_auth():
    client_protocol = JSONProtocol()
    client_protocol.parse(Frame('boom').to_json())


def test_client_binary_protocol():
    client_protocol = BinaryProtocol()
    server_protocol = BinaryProtocol(server=True)
    c_action, c_auth_frame = client_protocol.send_auth('agent-uuid', 'agent-token')

    s_action, s_auth_frame = server_protocol.parse(c_auth_frame)
    assert c_action == Action.SEND_FRAME
    assert s_action == Action.RECV_AUTH
    assert client_protocol._agent_uuid == 'agent-uuid'
    assert client_protocol._token == 'agent-token'
    assert server_protocol._agent_uuid == 'agent-uuid'
    assert server_protocol._token == 'agent-token'
    assert s_auth_frame.name == 'login'
    assert s_auth_frame.data['agent_uuid'] == 'agent-uuid'
    assert s_auth_frame.data['token'] == 'agent-token'

    c_action, c_frame = client_protocol.send(Frame('hello'))
    assert c_action == Action.SEND_FRAME
    assert isinstance(c_frame, bytes)
    s_action, s_frame = server_protocol.parse(c_frame)
    assert s_action == Action.RECV_FRAME
    assert s_frame.name == 'hello'

    s_action, s_frame = server_protocol.send(Frame('ping', Kind.COMMAND))
    c_action, c_frame = client_protocol.parse(s_frame)
    assert c_action == Action.SEND_FRAME
    assert c_frame.name == 'pong'
