import logging
import os
import struct

import imgreader
from utils import mathutils as mu


class PngChunk(object):
    __PUBLIC = 0
    __PRIVATE = 1

    __CRITICAL = 0
    __ANCILLARY = 1

    __RESERVED_VALID = 0
    __RESERVED_INVALID = 1

    __COPY = 0
    __NO_COPY = 1

    def __init__(self, type, length, data, crc):
        self.type = type
        self.__read_type()
        self.length = length
        self.data = data
        self.chunk_crc = crc
        ord_type = bytearray()
        ord_type.extend(map(ord, type))
        self.computed_crc = mu.crc(ord_type + data, 0xedb88320, initial=0xffffffff) ^ 0xffffffff

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
        return '%s(%i%i%i%i): len = %i, ' \
               'chunk_crc = 0x%08x, ' \
               'comp_crc = 0x%08x, ' \
               'valid = %r' % \
               (self.type,
                1 if self.ancillary_bit else 0,
                1 if self.private_bit else 0,
                1 if self.reserved_bit else 0,
                1 if self.safe_to_copy_bit else 0,
                self.length,
                self.chunk_crc,
                self.computed_crc,
                self.is_valid)


class PngHeaderChunk(PngChunk):
    def __init__(self, type, length, data, crc):
        super().__init__(type, length, data, crc)

        self.parse_data()

    def parse_data(self):
        self.width = struct.unpack(">I", self.data[0:4])[0]
        self.height = struct.unpack(">I", self.data[4:8])[0]
        self.bit_depth = int(self.data[8])
        self.color_type = int(self.data[9])
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


class ChunkFactory(object):
    __CHUNK_MAP__ = {
        'IHDR': PngHeaderChunk
    }

    @staticmethod
    def make_chunk(type, length, data, crc):
        chunk_class = PngChunk

        if str.upper(type) in ChunkFactory.__CHUNK_MAP__:
            chunk_class = ChunkFactory.__CHUNK_MAP__[str.upper(type)]

        return chunk_class(type, length, data, crc)

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
    def parse_chunk(rem_contents):
        (length, rem_contents) = ChunkFactory.parse_length(rem_contents)
        (chunk_type, rem_contents) = ChunkFactory.parse_chunk_type(rem_contents)
        (chunk_data, rem_contents) = ChunkFactory.parse_chunk_data(rem_contents, length)
        (crc, rem_contents) = ChunkFactory.parse_crc(rem_contents)

        return ChunkFactory.make_chunk(chunk_type, length, chunk_data, crc), rem_contents


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
            (chunk, rem_content) = ChunkFactory.parse_chunk(rem_content)
            self.chunks.append(chunk)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(message)s')
    reader = PngReader(os.path.join(imgreader.RESOURCES, 'smiley.png'))
    reader.parse()

    for chunk in reader.chunks:
        logging.info(str(chunk))
