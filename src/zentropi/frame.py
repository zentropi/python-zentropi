import json
from typing import Dict
from typing import Optional
from uuid import uuid4

from .kind import KIND_VALUES
from .kind import Kind


def deflate_dict(frame_as_dict: dict) -> dict:
    return {k: v for k, v in frame_as_dict.items() if v}


class Frame(object):
    """Frame contains the information that is sent over wire
    between instances and agents.
    """

    __slots__ = ("_name", "_kind", "_uuid", "_meta", "_data")

    def __init__(
        self,
        name: str,
        kind: Optional[int] = None,
        uuid: Optional[str] = None,
        data: Optional[Dict] = None,
        meta: Optional[Dict] = None,
    ) -> None:
        """
        Frame constructor.
        """
        self._name = name
        self._kind = Kind(kind or Kind.EVENT)
        self._uuid = uuid or uuid4().hex
        self._data = data
        self._meta = meta
        self.validate()

    def validate(self) -> None:
        # name
        if not isinstance(self._name, str):
            raise TypeError(f"Frame.name must be string, got {type(self._name)}")
        if not self._name.strip():
            raise ValueError(f"Frame.name must not be empty, got: {self._name!r}")

        # uuid
        if not isinstance(self._uuid, str):
            raise TypeError(f"Frame.uuid must be string, got {type(self._uuid)}")
        if not self._uuid.strip():
            raise ValueError(f"Frame.uuid must not be empty, got: {self._name!r}")

        # data
        if self._data is not None and not isinstance(self._data, dict):
            raise TypeError(f"Frame.data must be dict, got {type(self._data)}")

        # meta
        if self._meta is not None and not isinstance(self._meta, dict):
            raise TypeError(f"Frame.meta must be dict, got {type(self._meta)}")

    @property
    def name(self) -> str:
        return self._name

    @property
    def uuid(self) -> str:
        return self._uuid

    @property
    def kind(self) -> int:
        return self._kind

    @property
    def data(self) -> dict:
        if self._data is None:
            self._data = {}
        return self._data

    @property
    def meta(self) -> dict:
        if self._meta is None:
            self._meta = {}
        return self._meta

    def to_dict(self) -> dict:
        return deflate_dict(
            {
                "name": str(self.name),
                "kind": int(self.kind),
                "uuid": str(self.uuid),
                "data": dict(self.data) if self.data else {},
                "meta": dict(self.meta) if self.meta else {},
            }
        )

    @staticmethod
    def from_dict(frame_as_dict: dict) -> "Frame":
        return Frame(**frame_as_dict)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @staticmethod
    def from_json(frame_as_json) -> "Frame":
        return Frame.from_dict(json.loads(frame_as_json))

    def reply(
        self, name: str = "", data: Optional[Dict] = None, meta: Optional[Dict] = None
    ) -> "Frame":
        if isinstance(meta, dict):
            meta.update({"reply_to": self.uuid})
        else:
            meta = {"reply_to": self.uuid}
        if self.kind == Kind.REQUEST:
            return Frame(name=self.name, kind=Kind.RESPONSE, data=data, meta=meta)
        return Frame(name=name or self.name, kind=self.kind, data=data, meta=meta)
