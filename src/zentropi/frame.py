import json
from enum import IntEnum
from typing import Dict
from typing import Optional
from uuid import uuid4


class Kind(IntEnum):
    """Kind enumerates frames that serve specific purposes
    and must be handled differently by instances and agents.
    """
    COMMAND = 1
    EVENT = 2


class Frame(object):
    """Frame contains the information that is sent over wire
    between instances and agents.
    """
    __slots__ = ('_name', '_kind', '_uuid', '_meta', '_data')

    def __init__(self, name: str,
                 kind: Optional[int] = None,
                 uuid: Optional[str] = None,
                 data: Optional[Dict] = None,
                 meta: Optional[Dict] = None):
        """
        Frame constructor.
        """
        self._name = name
        self._kind = kind or Kind.EVENT
        self._uuid = uuid or uuid4().hex
        self._data = data
        self._meta = meta

    @property
    def name(self):
        return self._name

    @property
    def uuid(self):
        return self._uuid

    @property
    def kind(self):
        return self._kind

    @property
    def data(self):
        if self._data is None:
            self._data = {}
        return self._data

    @property
    def meta(self):
        if self._meta is None:
            self._meta = {}
        return self._meta

    def to_dict(self) -> dict:
        return deflate_dict({
            'name': str(self.name),
            'kind': int(self.kind),
            'uuid': str(self.uuid),
            'data': dict(self.data) if self.data else {},
            'meta': dict(self.meta) if self.meta else {},
        })

    @staticmethod
    def from_dict(frame_as_dict):
        return Frame(**frame_as_dict)

    def to_json(self):
        return json.dumps(self.to_dict())

    @staticmethod
    def from_json(frame_as_json):
        return Frame.from_dict(json.loads(frame_as_json))

    def reply(self, name='', data=None, meta=None):
        if isinstance(meta, dict):
            meta.update({'reply_to': self.uuid})
        else:
            meta = {'reply_to': self.uuid}
        return Frame(name=name or self.name, data=data, meta=meta)


def deflate_dict(frame_as_dict):
    return {k: v for k, v in frame_as_dict.items() if v}
