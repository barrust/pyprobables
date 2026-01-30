"""utility functions"""

from hashlib import md5
from pathlib import Path

from probables.constants import UINT64_T_MAX
from probables.hashes import KeyT


def calc_file_md5(filename: str | Path) -> str:
    """calc the md5 of a file"""
    with open(filename, "rb") as filepointer:
        res = filepointer.read()
    return md5(res).hexdigest()


def different_hash(key: KeyT, depth: int) -> list[int]:
    """the default fnv-1a hashing routine, but different"""

    def __fnv_1a(key: KeyT) -> int:
        """64 bit fnv-1a hash"""
        hval = 14695981039346656074  # made minor change
        fnv_64_prime = 1099511628211
        tmp = list(key) if not isinstance(key, str) else list(map(ord, key))
        for t_str in tmp:
            hval ^= t_str
            hval *= fnv_64_prime
            hval &= UINT64_T_MAX
        return hval

    res = []
    for _ in range(depth):
        res.append(__fnv_1a(key))
    return res
