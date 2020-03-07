import socket
import ssl

import websockets
from zeroconf import Zeroconf

from zentropi.protocol.protocol import Action
from zentropi.protocol.protocol import JSONProtocol
from zentropi.symbol import APP_NAME


class Websocket(object):
    def __init__(self) -> None:
        self._connected = False
        self._auth_complete = False
        self._protocol = None

    async def connect(self, agent_uuid, token, endpoint='', protocol=JSONProtocol, connection=websockets, zeroconf=Zeroconf):
        self._uuid = agent_uuid
        self._token = token
        self._endpoint = endpoint
        self._protocol = protocol(server=False)
        self._connected = False
        self._auth_complete = False
        self._websockets = connection
        self._zeroconf = zeroconf()
        if self._endpoint:
            endpoint = self._endpoint
        else:
            endpoint = await self._resolve_endpoint()
        if endpoint.startswith('ws://'):
            self._connection = await self._websockets.connect(endpoint)
        elif endpoint.startswith('wss://'):
            self._connection = await self._websockets.connect(endpoint, ssl=ssl._create_unverified_context())
        else:
            raise AssertionError(f'Uknown websocket schema: {endpoint}')
        self._connected = True
        await self._perform_auth()

    async def disconnect(self):
        await self._connection.close()
        self._connected = False
        self._auth_complete = False

    async def send(self, frame):
        action, frame_on_wire = self._protocol.send(frame)
        assert action == Action.SEND_FRAME
        await self._connection.send(frame_on_wire)

    async def recv(self):
        frame_from_wire = await self._connection.recv()
        action, frame = self._protocol.parse(frame_from_wire)
        assert action == Action.RECV_FRAME
        return frame

    async def _resolve_endpoint(self, server_name=APP_NAME):
        TYPE = '_http._tcp.local.'
        zeroconf = self._zeroconf
        try:
            sinfo = zeroconf.get_service_info(TYPE, server_name + '.' + TYPE)
        finally:
            zeroconf.close()
        if not sinfo:
            raise Exception('Unable to resolve server through Zeroconf.')
        addr = socket.inet_ntoa(sinfo.addresses[0])
        tls = bool(sinfo.properties[b'tls'])
        if tls:
            schema = 'wss'
        else:
            schema = 'ws'
        return f'{schema}://{addr}:{sinfo.port}/ws/'

    async def _perform_auth(self):
        action, frame = self._protocol.send_auth(self._uuid, self._token)
        assert action == Action.SEND_FRAME
        await self._connection.send(frame)
        frame_from_wire = await self._connection.recv()
        action, frame = self._protocol.parse(frame_from_wire)
        assert action == Action.ACK_AUTH
        self._auth_complete = True
