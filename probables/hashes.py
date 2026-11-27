"""Probables Hashing Utilities"""

from collections.abc import Callable
from functools import wraps
from hashlib import md5, sha256
from struct import Struct, unpack

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


_FNV_64_OFFSET = 14695981039346656037
_FNV_64_PRIME = 1099511628211
# Each seed's 64-bit state lives in its own 128-bit lane of one integer. A 64-bit
# value times the 41-bit prime fits in 105 bits, so lanes never carry into each
# other and every lane is exactly fnv_1a(key, seed).
_FNV_LANE_BITS = 128
_fnv_lanes: dict[int, tuple[int, int, int, Callable[[bytes], tuple[int, ...]]]] = {}


def _fnv_1a_lanes(depth: int) -> tuple[int, int, int, Callable[[bytes], tuple[int, ...]]]:
    """Build (and cache) the constants to hash all `depth` seeds at once"""
    ones = sum(1 << (_FNV_LANE_BITS * i) for i in range(depth))
    start = sum(((_FNV_64_OFFSET + 31 * i) & UINT64_T_MAX) << (_FNV_LANE_BITS * i) for i in range(depth))
    lanes = (ones, start, ones * UINT64_T_MAX, Struct(f"<{2 * depth}Q").unpack)
    _fnv_lanes[depth] = lanes
    return lanes


def default_fnv_1a(key: KeyT, depth: int = 1) -> list[int]:
    """The default fnv-1a hashing routine

    Args:
        key (str): The element to be hashed
        depth (int): The number of hash permutations to compute
    Returns:
        list(int): List of size depth hashes
    Note:
        The result is `[fnv_1a(key, 0), ..., fnv_1a(key, depth - 1)]`; all the seeds
        are hashed in a single pass over the key"""
    if depth == 1:
        return [fnv_1a(key)]
    if depth < 0:
        raise ValueError("depth must be zero or greater")
    lanes = _fnv_lanes.get(depth)
    ones, hval, mask, unpack_lanes = lanes if lanes is not None else _fnv_1a_lanes(depth)
    for t_str in key if not isinstance(key, str) else map(ord, key):
        hval = ((hval ^ (t_str * ones)) * _FNV_64_PRIME) & mask
    return list(unpack_lanes(hval.to_bytes(16 * depth, "little"))[::2])


def fnv_1a(key: KeyT, seed: int = 0) -> int:
    """Pure python implementation of the 64 bit fnv-1a hash

    Args:
        key (str): The element to be hashed
        seed (int): Add a seed to the initial starting point (0 means no seed)
    Returns:
        int: 64-bit hashed representation of key
    Note:
        Uses the lower 64 bits when overflows occur"""
    hval = (_FNV_64_OFFSET + (31 * seed)) & UINT64_T_MAX
    for t_str in key if not isinstance(key, str) else map(ord, key):
        hval = ((hval ^ t_str) * _FNV_64_PRIME) & UINT64_T_MAX
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
    for t_str in key if not isinstance(key, str) else map(ord, key):
        hval = ((hval ^ t_str) * 0x01000193) & UINT32_T_MAX
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
