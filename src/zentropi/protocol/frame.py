import json
from dataclasses import dataclass
from dataclasses import field
from struct import pack
from struct import unpack
from typing import Optional
from uuid import uuid4

from .kind import Kind


def deflate_dict(frame_as_dict):
    return {k: v for k, v in frame_as_dict.items() if v}


def binary_format(name_size, data_size, meta_size):
    str_format = f'!?LLLH32s{name_size}s{data_size}s{meta_size}s'
    return bytes(str_format, encoding='utf-8')


@dataclass(frozen=True)
class Frame:
    name: str
    kind: int = Kind.EVENT
    uuid: str = uuid4().hex
    data: Optional[dict] = field(default_factory=dict)
    meta: Optional[dict] = field(default_factory=dict)
    large: Optional[bool] = False

    def __post_init__(self):
        self.validate()

    def __repr__(self):
        return ('Frame(name={name!r}, kind={kind!r}, '
                'uuid={uuid!r}, data={data!r}, meta={meta!r})'.format(
                    name=self.name,
                    kind=int(self.kind),
                    uuid=self.uuid,
                    data=self.data,
                    meta=self.meta,
                ))

    def validate(self):
        uuid = self.uuid
        kind = int(self.kind)
        name = self.name
        data = self.data
        meta = self.meta
        assert len(uuid) == 32, (f'Frame.uuid {uuid!r} must be 32 bytes, got {len(uuid)}.')
        assert kind in {1, 2, 3, 4, 5, 6, 7}, (f'Frame.kind {kind} must be one of: [1, 2, 3, 4, 5, 6, 7].')
        assert len(name) >= 2, (f'Frame.name {name!r} must be no less than 2 bytes, got {len(name)}.')
        assert len(name) <= 128, (f'Frame.name {name!r} must be no more than 128 bytes, got {len(name)}.')
        assert name.strip(), (f'Frame.name {name!r} must be provided, found {len(name)} spaces instead.')
        try:
            data_as_json = json.dumps(data)
        except Exception:
            raise AssertionError(f'Frame.data must be JSON serializable, got: {data!r}')
        if not self.large:
            assert len(data_as_json) <= 512, (f'Frame.data must be no more than 512 bytes after serialization, '
                                              f'got {len(data_as_json)} bytes.')
        try:
            meta_as_json = json.dumps(meta)
        except Exception:
            raise AssertionError(f'Frame.meta must be JSON serializable, got: {meta!r}')
        if not self.large:
            assert len(meta_as_json) <= 256, (f'Frame.meta must be no more than {256} bytes after serialization, '
                                              f'got {len(meta_as_json)} bytes.')

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

    def to_bytes(self):
        data_as_json = json.dumps(self.data)
        meta_as_json = json.dumps(self.meta)
        name_size = len(self.name)
        data_size = len(data_as_json)
        meta_size = len(meta_as_json)

        bformat = binary_format(name_size, data_size, meta_size)
        assert isinstance(bformat, bytes)
        frame_as_bytes = pack(
            bformat,
            self.large,
            name_size,
            data_size,
            meta_size,
            self.kind,
            self.uuid.encode('utf-8'),
            self.name.encode('utf-8'),
            data_as_json.encode('utf-8'),
            meta_as_json.encode('utf-8'))
        return frame_as_bytes

    @staticmethod
    def from_bytes(frame_as_bytes):
        large, name_size, data_size, meta_size = unpack(b'!?LLL', frame_as_bytes[:13])
        large, _ns, _ds, _ms, kind, uuid, name, data_as_json, meta_as_json = unpack(
            binary_format(name_size, data_size, meta_size),
            frame_as_bytes)
        data = json.loads(data_as_json)
        meta = json.loads(meta_as_json)
        return Frame(name=name.decode('utf-8'),
                     kind=int(kind),
                     uuid=uuid.decode('utf-8'),
                     data=data,
                     meta=meta,
                     large=large)

    def reply(self, name='', data=None, meta=None):
        if isinstance(meta, dict):
            meta.update({'reply_to': self.uuid})
        else:
            meta = {'reply_to': self.uuid}
        return Frame(name=name or self.name, data=data, meta=meta)
