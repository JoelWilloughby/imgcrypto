import logging
import os

import imgreader
import utils.mathutils

class PngReader:
    SIGNATURE = {137, 80, 78, 71, 13, 10, 26, 10}

    def __init__(self, file: str) -> None:
        """
        Inits the object
        :rtype: str
        """
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

    def parse(self):
        self.rest = self.parse_signature(self.contents)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(message)s')
    reader = PngReader(os.path.join(imgreader.RESOURCES, 'testfile'))
    reader.parse()

    logging.info(reader.rest)
