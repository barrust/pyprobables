"""utility functions"""

import functools
import re
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


def _version_tuple(version: str) -> tuple[int, ...]:
    """the release numbers of a version, ignoring any suffix: 0.8.0rc1 -> (0, 8, 0), so a release candidate
    counts as the release"""
    match = re.match(r"\d+(\.\d+)*", version)
    return tuple(int(part) for part in match.group().split(".")) if match else ()


def fail_after(version: str):
    """Decorator for tests of deprecated features: the test fails once probables reaches `version`,
    so the deprecated feature (and its test) must be removed by then

    Args:
        version (str): The version in which the deprecated feature must be removed"""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            from probables import __version__  # pylint: disable=import-outside-toplevel

            if _version_tuple(__version__) >= _version_tuple(version):
                raise AssertionError(
                    f"{func.__name__} tests a deprecated feature that must be removed in version {version}; "
                    f"probables is version {__version__}"
                )
            return func(*args, **kwargs)

        return wrapper

    return decorator
