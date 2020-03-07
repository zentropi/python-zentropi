from enum import IntEnum as _IntEnum


class Kind(_IntEnum):
    COMMAND = 1
    EVENT = 2
    MESSAGE = 3
    REQUEST = 4
    RESPONSE = 5
    STATE = 6
    STREAM = 7
