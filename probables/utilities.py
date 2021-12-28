""" some utility functions """

import array
import mmap
import os
import string
from pathlib import Path
from typing import Iterable, Optional, Union


def is_hex_string(hex_string: Optional[str]) -> bool:
    """check if the passed in string is really hex"""
    if hex_string is None:
        return False
    return all(c in string.hexdigits for c in hex_string)


def is_valid_file(filepath: Optional[Union[str, Path]]) -> bool:
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
    t.fromlist(arr)  # type: ignore
    return t


class MMap(object):
    """Simplified mmap.mmap class"""

    __slots__ = ("p", "__f", "m", "_closed")

    def __init__(self, path: Union[Path, str]):
        self.p = Path(path)
        self.__f = self.path.open("rb")
        self.m = mmap.mmap(self.__f.fileno(), 0, prot=mmap.PROT_READ)
        self._closed = False

    def __enter__(self) -> mmap.mmap:
        return self.map

    def __exit__(self, *args, **kwargs) -> None:
        if not self.map.closed:
            self.map.close()
        if self.__f:
            self.__f.close()
        self.__f = None
        self.m = None
        self._closed = True

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def map(self) -> mmap.mmap:
        return self.m

    @property
    def path(self) -> Path:
        return self.p

    def close(self) -> None:
        self.__exit__()
