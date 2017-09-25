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


def get_leftmost_bits(num, max_bits, left_bits):
    ''' ensure the correct number of bits and pull the upper x bits '''
    bits = bin(num).lstrip('0b')
    bits = bits.zfill(max_bits)
    return int(bits[:left_bits], 2)
