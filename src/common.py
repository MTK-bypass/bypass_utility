import struct


def raise_(ex):
    raise ex


def to_bytes(value, size=1):
    return {
        1: lambda: struct.pack('>B', value),
        2: lambda: struct.pack('>H', value),
        4: lambda: struct.pack('>I', value)
    }.get(size, lambda: raise_(RuntimeError("invalid size")))()


def from_bytes(value, size=1):
    return {
        1: lambda: struct.unpack('>B', value)[0],
        2: lambda: struct.unpack('>H', value)[0],
        4: lambda: struct.unpack('>I', value)[0]
    }.get(size, lambda: raise_(RuntimeError("invalid size")))()
