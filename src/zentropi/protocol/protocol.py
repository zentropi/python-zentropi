from enum import Enum
from enum import auto

from zentropi.protocol.frame import Frame
from zentropi.protocol.kind import Kind


class Action(Enum):
    RECV_AUTH = auto()
    RECV_FRAME = auto()
    SEND_FRAME = auto()
    ACK_AUTH = auto()


class BaseProtocol(object):
    def __init__(self, server=False) -> None:
        self._agent_uuid = ''
        self._server = server
        self._token = ''

    def parse(self, frame: Frame):
        if self._server and not self._token:
            return self._recv_auth(frame)
        elif not self._server and not self._token:
            raise PermissionError('Must send auth first.')
        elif frame.kind == Kind.COMMAND and frame.name == 'ping':
            return (Action.SEND_FRAME, frame.reply('pong'))
        elif frame.kind == Kind.COMMAND and frame.name == 'login':
            return (Action.ACK_AUTH, frame)
        return (Action.RECV_FRAME, frame)

    def _recv_auth(self, frame):
        assert frame.name == 'login'
        assert 'agent_uuid' in frame.data
        assert 'token' in frame.data
        self._agent_uuid = frame.data['agent_uuid']
        self._token = frame.data['token']
        return (Action.RECV_AUTH, frame)

    def send_auth(self, agent_uuid, token):
        self._agent_uuid = agent_uuid
        self._token = token
        auth_frame = Frame('login', kind=Kind.COMMAND, data=dict(agent_uuid=agent_uuid, token=token))
        return (Action.SEND_FRAME, auth_frame)

    def send(self, frame: Frame):
        return (Action.SEND_FRAME, frame)


class JSONProtocol(BaseProtocol):
    def parse(self, data: str):
        frame = Frame.from_json(data)
        return super().parse(frame)

    def send(self, frame: Frame):
        action, frame = super().send(frame)
        return (action, frame.to_json())

    def send_auth(self, agent_uuid, token):
        action, frame = super().send_auth(agent_uuid, token)
        return (action, frame.to_json())


class BinaryProtocol(BaseProtocol):
    def parse(self, data: bytes):
        frame = Frame.from_bytes(data)
        return super().parse(frame)

    def send(self, frame: Frame):
        action, frame = super().send(frame)
        return (action, frame.to_bytes())

    def send_auth(self, agent_uuid, token):
        action, frame = super().send_auth(agent_uuid, token)
        return (action, frame.to_bytes())
