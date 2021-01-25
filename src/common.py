import struct


def raise_(ex):
    raise ex


def to_bytes(value, size=1, endin='>'):
    return {
        1: lambda: struct.pack(endin + 'B', value),
        2: lambda: struct.pack(endin + 'H', value),
        4: lambda: struct.pack(endin + 'I', value)
    }.get(size, lambda: raise_(RuntimeError("invalid size")))()


def from_bytes(value, size=1, endin='>'):
    return {
        1: lambda: struct.unpack(endin + 'B', value)[0],
        2: lambda: struct.unpack(endin + 'H', value)[0],
        4: lambda: struct.unpack(endin + 'I', value)[0]
    }.get(size, lambda: raise_(RuntimeError("invalid size")))()
