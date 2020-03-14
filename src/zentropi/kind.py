from enum import IntEnum


class Kind(IntEnum):
    """Kind enumerates frames that serve specific purposes
    and must be handled differently by instances and agents.
    """
    COMMAND = 1
    EVENT = 2
    MESSAGE = 3


KIND_VALUES = {
    int(Kind.COMMAND),
    int(Kind.EVENT),
    int(Kind.MESSAGE),
}


KIND_LABELS = {
    int(Kind.COMMAND): Kind.COMMAND.name,
    int(Kind.EVENT): Kind.EVENT.name,
    int(Kind.MESSAGE): Kind.MESSAGE.name,
}
