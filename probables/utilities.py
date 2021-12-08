""" some utility functions """

import os
import string
import typing


def is_hex_string(hex_string: typing.Optional[str]) -> bool:
    """ check if the passed in string is really hex """
    if hex_string is None:
        return False
    return all(c in string.hexdigits for c in hex_string)


def is_valid_file(filepath: typing.Optional[str]) -> bool:
    """ check if the passed filepath points to a real file """
    if filepath is None:
        return False
    return os.path.isfile(filepath)


def get_x_bits(num: int, max_bits: int, num_bits: int, right_bits: bool = True) -> int:
    """ ensure the correct number of bits and pull the upper x bits """
    bits = bin(num).lstrip("0b")
    bits = bits.zfill(max_bits)
    if right_bits:
        return int(bits[-num_bits:], 2)
    return int(bits[:num_bits], 2)
