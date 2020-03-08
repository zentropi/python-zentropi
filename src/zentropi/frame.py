from typing import Dict
from typing import Optional


class Frame(object):
    """Frame contains the information that is sent over wire
    between Zentropian Instances and Agents.
    """
    def __init__(self, name: str,
                 uuid: Optional[str] = None,
                 kind: Optional[int] = None,
                 data: Optional[Dict] = None,
                 meta: Optional[Dict] = None):
        """
        Frame constructor.
        """
        self.name = name
        self.uuid = uuid
        self.kind = kind
        self._data = data
        self._meta = meta

    @property
    def data(self):
        if self._data is None:
            self._data = {}
        return self._data

    @data.setter
    def data(self, value):
        if not isinstance(value, dict):
            raise TypeError('Frame.data must be a dict.')
        self._data = value

    @property
    def meta(self):
        if self._meta is None:
            self._meta = {}
        return self._meta

    @meta.setter
    def meta(self, value):
        if not isinstance(value, dict):
            raise TypeError('Frame.meta must be a dict.')
        self._meta = value
