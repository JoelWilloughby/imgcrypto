import ctypes
import struct


def crc_table(val, poly, little_endian=True):
    oper = lambda x, y: x >> y
    if not little_endian:
        oper = lambda x, y: x << y

    c = ctypes.c_uint32(val)
    p = ctypes.c_uint32(poly)

    for i in range(0,8):
        if c & 1:
            c = p ^ (oper(c,1))
        else:
            c = oper(c,1)

    return c


def crc(buf, poly, initial=0x00000000, little_endian=True):
    oper = lambda x, y: x >> y
    if not little_endian:
        oper = lambda x,y: x << y

    shift = ctypes.uint32(initial)
    for val in buf:
        shift = crc_table((shift ^ val) & 0xff, poly, little_endian) ^ (oper(shift, 8))

    return shift
