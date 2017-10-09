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


def get_x_bits(num, max_bits, num_bits, right_bits=True):
    ''' ensure the correct number of bits and pull the upper x bits '''
    bits = bin(num).lstrip('0b')
    bits = bits.zfill(max_bits)
    if right_bits:
        return int(bits[-num_bits:], 2)
    return int(bits[:num_bits], 2)
