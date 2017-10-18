import logging
import os
import struct
from enum import Enum

import imgreader
from utils import mathutils as mu

class PngColorTypes(Enum):
    GREYSCALE = 0
    TRUECOLOR = 2
    INDEXED = 3
    GREYSCALE_ALPHA = 4
    TRUECOLOR_ALPHA = 6

    @classmethod
    def make(cls, color_type):
        try:
            return cls(color_type)
        except ValueError:
            return None

    @classmethod
    def is_indexed(cls, color_type):
        return color_type in [cls.INDEXED]

    @classmethod
    def is_greyscale(cls, color_type):
        return color_type in [cls.GREYSCALE, cls.GREYSCALE_ALPHA]

    @classmethod
    def is_truecolor(cls, color_type):
        return color_type in [cls.TRUECOLOR, cls.TRUECOLOR_ALPHA]

    @classmethod
    def is_alpha(cls, color_type):
        return color_type in [cls.TRUECOLOR_ALPHA, cls.GREYSCALE_ALPHA]

class Color(object):
    def __init__(self):
        self.bit_depth = 8

    def _val_str(self, val):
        temp = "0%ix" % (self.bit_depth / 4)
        return ("0x%" + temp) % mu.clamp_bit_depth(val, self.bit_depth)


class TrueColor(Color):
    def __init__(self, red, green, blue, alpha=None):
        self._red = red
        self._green = green
        self._blue = blue

        self._alpha = 0xffff
        if alpha is not None:
            self._alpha = alpha

    def __str__(self):
        return "(r:%s,g:%s,b:%s,a:%s)" % (
            self._val_str(self._red),
            self._val_str(self._green),
            self._val_str(self._blue),
            self._val_str(self._alpha)
        )

class GreyscaleColor(Color):
    def __init__(self, grey, alpha=None):
        self.grey = grey

        self.alpha = 0xffff
        if alpha is not None:
            self.alpha = alpha

    def __str__(self):
        return "(g:%s,a:%s)" % (
            self._val_str(self.grey),
            self._val_str(self.alpha),
        )

class IndexColor(Color):
    def __init__(self, index):
        self.index = index

    def __str__(self):
        return "(i:%s)" %  self._val_str(self.index),

class ColorFactory(object):

    @staticmethod
    def parse_truecolor(data, color_type, use_alpha=True):
        red = struct.unpack(">H", data[0:2])[0]
        green = struct.unpack(">H", data[2:4])[0]
        blue = struct.unpack(">H", data[4:6])[0]

        alpha = None
        if use_alpha and PngColorTypes.is_alpha(color_type):
            alpha = struct.unpack(">H", data[6:8])[0]

        return TrueColor(red, green, blue, alpha)

    @staticmethod
    def parse_greyscale(data, color_type, use_alpha=True):
        grey = struct.unpack(">H", data[0:2])[0]

        alpha = None
        if use_alpha and PngColorTypes.is_alpha(color_type):
            alpha = struct.unpack(">H", data[2:4])[0]

        return GreyscaleColor(grey, alpha)

    @staticmethod
    def parse_indexed(data):
        index = struct.unpack("B", data[0:1])[0]

        return IndexColor(index)

    @staticmethod
    def parse_color(data, color_type, use_alpha=True):
        if PngColorTypes.is_truecolor(color_type):
            return ColorFactory.parse_truecolor(data, color_type, use_alpha)
        elif PngColorTypes.is_greyscale(color_type):
            return ColorFactory.parse_greyscale(data, color_type, use_alpha)
        elif PngColorTypes.is_indexed(color_type):
            return ColorFactory.parse_indexed(data)

        return None


class PngChunk(object):
    __PUBLIC = 0
    __PRIVATE = 1

    __CRITICAL = 0
    __ANCILLARY = 1

    __RESERVED_VALID = 0
    __RESERVED_INVALID = 1

    __COPY = 0
    __NO_COPY = 1

    def __init__(self, type, length, data, crc, previous_chunks=[]):
        self.type = type
        self.__read_type()
        self.length = length
        self.data = data
        self.chunk_crc = crc
        ord_type = bytearray()
        ord_type.extend(map(ord, type))
        self.computed_crc = mu.crc(ord_type + data, 0xedb88320, initial=0xffffffff) ^ 0xffffffff

    def parse_data(self):
        pass

    @property
    def is_valid(self):
        return self.computed_crc == self.chunk_crc

    def __read_type(self):
        property_bit = 5

        self.ancillary_bit = (ord(self.type[0]) >> 5) & 1
        self.private_bit = (ord(self.type[1]) >> 5) & 1
        self.reserved_bit = (ord(self.type[2]) >> 5) & 1
        self.safe_to_copy_bit = (ord(self.type[3]) >> 5) & 1

    def __str__(self):
        return '%s -- %s(%i%i%i%i): len = %i, ' \
               'chunk_crc = 0x%08x, ' \
               'comp_crc = 0x%08x, ' \
               'valid = %r' % \
               (self.__class__.__name__,
                self.type,
                1 if self.ancillary_bit else 0,
                1 if self.private_bit else 0,
                1 if self.reserved_bit else 0,
                1 if self.safe_to_copy_bit else 0,
                self.length,
                self.chunk_crc,
                self.computed_crc,
                self.is_valid)


class PngHeaderChunk(PngChunk):
    def __init__(self, type, length, data, crc, previous_chunks=[]):
        super().__init__(type, length, data, crc, previous_chunks)
        if self.is_valid:
            self.parse_data()


    def parse_data(self):
        self.width = struct.unpack(">I", self.data[0:4])[0]
        self.height = struct.unpack(">I", self.data[4:8])[0]
        self.bit_depth = int(self.data[8])
        self.color_type = PngColorTypes.make(int(self.data[9]))
        self.compression_method = int(self.data[10])
        self.filter_method = int(self.data[11])
        self.interlace_method = int(self.data[12])

    def __str__(self):
        s = '%s\nw: %i, h: %i' % (
            super().__str__(),
            self.width,
            self.height
        )

        return s


class PngBackgroundChunk(PngChunk):
    def __init__(self, type, length, data, crc, previous_chunks=[]):
        super().__init__(type, length, data, crc)

        ihdr_chunk = next((c for c in previous_chunks if isinstance(c, PngHeaderChunk)), None)

        if ihdr_chunk is not None:
            self.color_type = ihdr_chunk.color_type
            self.bit_depth = ihdr_chunk.bit_depth
        else:
            self.color_type = None
            self.bit_depth = None

        if self.is_valid:
            self.parse_data()


    def parse_data(self):
        self.color = ColorFactory.parse_color(self.data, self.color_type, use_alpha=False)
        self.color.bit_depth = self.bit_depth

    def __str__(self):
        s = '%s\nw: color: %s' % (
            super().__str__(),
            str(self.color)
        )

        return s


class ChunkFactory(object):
    __CHUNK_MAP__ = {
        'IHDR': PngHeaderChunk,
        'BKGD': PngBackgroundChunk
    }

    @staticmethod
    def make_chunk(type, length, data, crc, previous_chunks=[]):
        chunk_class = PngChunk

        if str.upper(type) in ChunkFactory.__CHUNK_MAP__:
            chunk_class = ChunkFactory.__CHUNK_MAP__[str.upper(type)]

        return chunk_class(type, length, data, crc, previous_chunks=previous_chunks)

    @staticmethod
    def parse_length(rem_contents):
        return struct.unpack(">I", rem_contents[0:4])[0], rem_contents[4:]

    @staticmethod
    def parse_chunk_type(rem_contents):
        return rem_contents[0:4].decode('utf-8'), rem_contents[4:]

    @staticmethod
    def parse_chunk_data(rem_contents, length):
        return rem_contents[0:length], rem_contents[length:]

    @staticmethod
    def parse_crc(rem_contents):
        return struct.unpack(">I", rem_contents[0:4])[0], rem_contents[4:]

    @staticmethod
    def parse_chunk(rem_contents, previous_chunks=[]):
        (length, rem_contents) = ChunkFactory.parse_length(rem_contents)
        (chunk_type, rem_contents) = ChunkFactory.parse_chunk_type(rem_contents)
        (chunk_data, rem_contents) = ChunkFactory.parse_chunk_data(rem_contents, length)
        (crc, rem_contents) = ChunkFactory.parse_crc(rem_contents)

        return ChunkFactory.make_chunk(chunk_type,
                                       length,
                                       chunk_data,
                                       crc,
                                       previous_chunks=previous_chunks), \
               rem_contents


class PngReader(object):
    SIGNATURE = [137, 80, 78, 71, 13, 10, 26, 10]

    def __init__(self, file: str) -> None:
        try:
            with open(file, 'rb') as openfile:
                self.contents = openfile.read()
        except IOError:
            self.contents = ''

    def parse_signature(self, rem_contents):
        try:
            content_signature = rem_contents[0:len(self.SIGNATURE)]

            match = True
            for i in range(0,len(self.SIGNATURE)):
                if content_signature[i] != self.SIGNATURE[i]:
                    match = False
                    break

            if match:
                return rem_contents[len(self.SIGNATURE):]

        except:
            logging.error("Exception in parse_signature")
            return None

        return None

    def parse(self):
        rem_content = self.parse_signature(self.contents)
        self.chunks = []
        while len(rem_content) > 0:
            (chunk, rem_content) = ChunkFactory.parse_chunk(rem_content, self.chunks)
            self.chunks.append(chunk)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(message)s')
    reader = PngReader(os.path.join(imgreader.RESOURCES, 'smiley.png'))
    reader.parse()

    for chunk in reader.chunks:
        logging.info(str(chunk))
