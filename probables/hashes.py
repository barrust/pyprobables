"""Probables Hashing Utilities"""

from collections.abc import Callable
from functools import wraps
from hashlib import md5, sha256
from struct import unpack

from probables.constants import UINT32_T_MAX, UINT64_T_MAX

KeyT = str | bytes
SimpleHashT = Callable[[KeyT, int], int]
SimpleHashBytesT = Callable[[KeyT, int], bytes]
HashResultsT = list[int]
HashFuncT = Callable[[KeyT, int], HashResultsT]
HashFuncBytesT = Callable[[KeyT, int], bytes]


def hash_with_depth_bytes(func: HashFuncBytesT | SimpleHashBytesT) -> HashFuncT:
    """Decorator to turns a function taking a single key and hashes it to
    bytes. Wraps functions to be used in Bloom filters and Count-Min sketch
    data structures.

    Args:
        key (str): The element to be hashed
        depth (int): The number of hash permutations to compute
    Returns:
        list(int): 64-bit hashed representation of key
    Note:
        Arguments shown are as it will be after decorated"""

    @wraps(func)
    def hashing_func(key, depth=1):
        """wrapper function"""
        res = []
        tmp = key if not isinstance(key, str) else key.encode("utf-8")
        for idx in range(depth):
            tmp = func(tmp, idx)
            res.append(unpack("Q", tmp[:8])[0])  # turn into 64 bit number
        return res

    return hashing_func


def hash_with_depth_int(func: HashFuncT | SimpleHashT) -> HashFuncT:
    """Decorator to turn a function that takes a single key and hashes it to
    an int. Wraps functions to be used in Bloom filters and Count-Min
    sketch data structures.

    Args:
        key (str): The element to be hashed
        depth (int): The number of hash permutations to compute
    Returns:
        list(int): 64-bit hashed representation of key
    Note:
        Arguments shown are as it will be after decorated"""

    @wraps(func)
    def hashing_func(key, depth=1):
        """wrapper function"""
        res = []
        tmp = func(key, 0)
        res.append(tmp)
        for idx in range(1, depth):
            tmp = func(f"{tmp:x}", idx)
            res.append(tmp)
        return res

    return hashing_func


def default_fnv_1a(key: KeyT, depth: int = 1) -> list[int]:
    """The default fnv-1a hashing routine

    Args:
        key (str): The element to be hashed
        depth (int): The number of hash permutations to compute
    Returns:
        list(int): List of size depth hashes"""

    res = []
    for idx in range(depth):
        res.append(fnv_1a(key, idx))
    return res


def fnv_1a(key: KeyT, seed: int = 0) -> int:
    """Pure python implementation of the 64 bit fnv-1a hash

    Args:
        key (str): The element to be hashed
        seed (int): Add a seed to the initial starting point (0 means no seed)
    Returns:
        int: 64-bit hashed representation of key
    Note:
        Uses the lower 64 bits when overflows occur"""
    hval = (14695981039346656037 + (31 * seed)) & UINT64_T_MAX
    fnv_64_prime = 1099511628211
    tmp = list(key) if not isinstance(key, str) else list(map(ord, key))
    for t_str in tmp:
        hval ^= t_str
        hval *= fnv_64_prime
        hval &= UINT64_T_MAX
    return hval


def _fmix64(value: int) -> int:
    """64-bit finalizer with good avalanche properties"""
    value &= UINT64_T_MAX
    value ^= value >> 33
    value = (value * 0xFF51AFD7ED558CCD) & UINT64_T_MAX
    value ^= value >> 33
    value = (value * 0xC4CEB9FE1A85EC53) & UINT64_T_MAX
    value ^= value >> 33
    return value & UINT64_T_MAX


def hll_hash64(key: KeyT, seed: int = 0) -> int:
    """64-bit non-cryptographic hash tuned for HLL-style bit splitting.

    Args:
        key (str|bytes): The element to be hashed
        seed (int): Seed mixed into the initial state
    Returns:
        int: 64-bit hashed representation of key"""
    return _fmix64(fnv_1a(key, seed))


def default_hll_hash(key: KeyT, depth: int = 1) -> list[int]:
    """Return a list of HLL-appropriate 64-bit hashes.

    Args:
        key (str|bytes): The element to be hashed
        depth (int): Number of hashes to generate
    Returns:
        list(int): List of size depth hashes"""
    return [hll_hash64(key, idx) for idx in range(depth)]


def fnv_1a_32(key: KeyT, seed: int = 0) -> int:
    """Pure python implementation of the 32 bit fnv-1a hash
    Args:
        key (str): The element to be hashed
        seed (int): Add a seed to the initial starting point (0 means no seed)
    Returns:
        int: 32-bit hashed representation of key
    Note:
        Uses the lower 32 bits when overflows occur"""
    hval = (0x811C9DC5 + (31 * seed)) & UINT32_T_MAX
    fnv_32_prime = 0x01000193
    tmp = list(key) if not isinstance(key, str) else list(map(ord, key))
    for t_str in tmp:
        hval ^= t_str
        hval *= fnv_32_prime
        hval &= UINT32_T_MAX
    return hval


@hash_with_depth_bytes
def default_md5(key: KeyT, *args, **kwargs) -> bytes:
    """The default md5 hashing routine

    Args:
        key (str): The element to be hashed
        depth (int): The number of hash permutations to compute
    Returns:
        list(int): List of 64-bit hashed representation of key hashes
    Note:
        Returns the upper-most 64 bits"""
    return md5(key).digest()  # type: ignore


@hash_with_depth_bytes
def default_sha256(key: KeyT, *args, **kwargs) -> bytes:
    """The default sha256 hashing routine

    Args:
        key (str): The element to be hashed
        depth (int): The number of hash permutations to compute
    Returns:
        list(int): List of 64-bit hashed representation of key hashes
    Note:
        Returns the upper-most 64 bits"""
    return sha256(key).digest()  # type: ignore
