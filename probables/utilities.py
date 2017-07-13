''' some utility functions '''
from __future__ import (unicode_literals, absolute_import, print_function)
import string
import os


def is_hex_string(hex_string):
    ''' check if the passed in string is really hex '''
    if hex_string is None:
        return False
    return all(c in string.hexdigits for c in hex_string)


def is_valid_file(filepath):
    ''' check if the passed filepath points to a real file '''
    if filepath is None:
        return False
    return os.path.isfile(filepath)
