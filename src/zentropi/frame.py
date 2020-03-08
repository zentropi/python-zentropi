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
    def __init__(self, name: str,
                 uuid: Optional[str] = None,
                 kind: Optional[int] = None,
                 data: Optional[Dict] = None,
                 meta: Optional[Dict] = None):
        """
        Frame constructor.
        """
        self._name = name
        self._uuid = uuid or uuid4().hex
        self._kind = kind or Kind.EVENT
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
