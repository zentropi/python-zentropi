from abc import ABC
from abc import abstractmethod

from ..frame import Frame


class BaseTransport(ABC):  # pragma: no cover
    @abstractmethod
    async def connect(self, endpoint, token) -> None:
        pass

    @abstractmethod
    async def close(self) -> None:
        pass

    @abstractmethod
    async def send(self, frame: Frame) -> None:
        pass

    @abstractmethod
    async def recv(self) -> Frame:
        pass
