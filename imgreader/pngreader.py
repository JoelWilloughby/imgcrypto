import logging
import os
import struct

import imgreader
from utils import mathutils as mu


class PngChunk(object):
    def __init__(self, type, length, data, crc):
        self.type = type
        self.length = length
        self.data = data
        self.chunk_crc = crc
        self.computed_crc = mu.crc(data, 0xedb88320, initial=0xffffffff) ^ 0xffffffffff


class PngHeaderChunk(PngChunk):
    pass


class ChunkFactory(object):
    __CHUNK_MAP__ = {
        'IHDR': PngHeaderChunk
    }

    @staticmethod
    def make_chunk(type, length, data, crc):
        chunk_class = ChunkFactory.__CHUNK_MAP__[str.upper(type)]
        return chunk_class(type, length, data, crc)


class PngReader(object):
    SIGNATURE = {137, 80, 78, 71, 13, 10, 26, 10}

    """
        Inits the object
        :rtype: str
        """
    def __init__(self, file: str) -> None:
        try:
            with open(file, 'r') as openfile:
                self.contents = openfile.read()
        except IOError:
            self.contents = ''

    def parse_signature(self, rem_contents):
        try:
            content_signature = rem_contents[0:len(self.SIGNATURE)]
            if content_signature == rem_contents:
                return rem_contents[len(self.SIGNATURE):]

        except:
            return None

        return None

    def parse_length(self, rem_contents):
        return struct.unpack(">I", rem_contents), rem_contents[4:]

    def parse_chunk_type(self, rem_contents):
        return rem_contents[0:3], rem_contents[4:]

    def parse_chunk_data(self, rem_contents, length):
        return rem_contents[0:length], rem_contents[length:]

    def parse_crc(self, rem_contents):
        return struct.unpack(">I", rem_contents), rem_contents[4:]

    def parse_chunk(self, rem_contents):
        (length, rem_contents) = self.parse_length(rem_contents)
        (chunk_type, rem_contents) = self.parse_chunk_type(rem_contents)
        (chunk_data, rem_contents) = self.parse_chunk_data(rem_contents, length)
        (crc, rem_contents) = self.parse_crc(rem_contents)

    def parse(self):
        self.rest = self.parse_signature(self.contents)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(message)s')
    reader = PngReader(os.path.join(imgreader.RESOURCES, 'testfile'))
    reader.parse()

    logging.info(reader.rest)
