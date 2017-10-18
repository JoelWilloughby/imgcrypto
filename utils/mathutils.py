import ctypes
import struct

__crc_tables__ = dict()


def crc_table(val, poly, little_endian=True):
    if (poly, little_endian) not in __crc_tables__:
        def oper(x, y):
            if little_endian:
                return (x >> y) & 0xffffffff
            return (x << y) & 0xffffffff

        entry = [None] * 256

        for n in range(256):
            c = n
            for i in range(0,8):
                if c & 1:
                    c = poly ^ (oper(c,1))
                else:
                    c = oper(c,1)

            entry[n] = c

        __crc_tables__[(poly, little_endian)] = entry

    return __crc_tables__[(poly, little_endian)][val]


def crc(buf, poly, initial=0x00000000, little_endian=True):
    def oper(x, y):
        if little_endian:
            return (x >> y) & 0xffffffff
        return (x << y) & 0xffffffff

    shift = int(initial)
    for val in buf:
        shift = crc_table((shift ^ val) & 0xff, poly, little_endian) ^ (oper(shift, 8))

    return shift

def clamp_bit_depth(val, depth):
    return val & (pow(2,depth)-1)
