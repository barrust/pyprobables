""" some utility functions """

import array
import mmap
import os
import string
from pathlib import Path
from typing import Iterable, Optional


def is_hex_string(hex_string: Optional[str]) -> bool:
    """check if the passed in string is really hex"""
    if hex_string is None:
        return False
    return all(c in string.hexdigits for c in hex_string)


def is_valid_file(filepath: Optional[str]) -> bool:
    """check if the passed filepath points to a real file"""
    if filepath is None:
        return False
    return os.path.isfile(filepath)


def get_x_bits(num: int, max_bits: int, num_bits: int, right_bits: bool = True) -> int:
    """ensure the correct number of bits and pull the upper x bits"""
    bits = bin(num).lstrip("0b")
    bits = bits.zfill(max_bits)
    if right_bits:
        return int(bits[-num_bits:], 2)
    return int(bits[:num_bits], 2)


def convert_to_typed(tp: str, arr: Iterable[int]) -> array.array:
    """Converts a container of untyped ints into a typed array"""
    t = array.ArrayType(tp)
    t.fromlist(arr)
    return t


# mmap wrapper is taken from https://github.com/prebuilder/fsutilz.py/blob/master/fsutilz/__init__.py
class ommap(mmap.mmap):
    """Our children of `mmap.mmap` that closes its `_parent`"""

    __slots__ = ("parent",)

    def __init__(self, *args, _parent, **kwargs):
        self.parent = _parent

    __init__.__wraps__ = mmap.mmap.__init__

    def __new__(cls, *args, _parent, **kwargs):
        return mmap.mmap.__new__(cls, *args, **kwargs)

    __new__.__wraps__ = mmap.mmap.__new__

    def __exit__(self, *args, **kwargs):
        super().__exit__(*args, **kwargs)
        self.parent.__exit__(*args, **kwargs)


class MMap:
    """Our class for memory mapping making its usage much easier."""

    __slots__ = ("path", "f", "m")

    def __init__(self, path: Path):
        self.path = path
        self.f = None
        self.m = None

    def __enter__(self):
        self.f = self.path.open("rb").__enter__()
        self.m = ommap(self.f.fileno(), 0, prot=mmap.PROT_READ, _parent=self).__enter__()
        return self.m

    def __exit__(self, *args, **kwargs):
        self.m = None
        if self.f:
            self.f.__exit__(*args, **kwargs)
            self.f = None
