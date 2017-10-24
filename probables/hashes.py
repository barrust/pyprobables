''' Probables Hashing library '''
from __future__ import (unicode_literals, absolute_import, print_function)

from functools import (wraps)
from hashlib import (md5, sha256)
from struct import (unpack)

from . constants import (UINT64_T_MAX)


def hash_with_depth_bytes(func):
    ''' Decorator to turns a function taking a single key and hashes it to
        bytes. Wraps functions to be used in Bloom filters and Count-Min sketch
        data structures.

        Args:
            key (str): The element to be hashed
            depth (int): The number of hash permutations to compute
        Returns:
            list(int): 64-bit hashed representation of key
        Note:
            Arguments shown are as it will be after decorated '''
    @wraps(func)
    def hashing_func(key, depth=1):
        ''' wrapper function '''
        res = list()
        tmp = key.encode('utf-8')
        for _ in range(depth):
            tmp = func(tmp)
            res.append(unpack('Q', tmp[:8])[0])  # turn into 64 bit number
        return res
    return hashing_func


def hash_with_depth_int(func):
    ''' Decorator to turn a function that takes a single key and hashes it to
        an int. Wraps functions to be used in Bloom filters and Count-Min
        sketch data structures.

        Args:
            key (str): The element to be hashed
            depth (int): The number of hash permutations to compute
        Returns:
            list(int): 64-bit hashed representation of key
        Note:
            Arguments shown are as it will be after decorated '''
    @wraps(func)
    def hashing_func(key, depth=1):
        ''' wrapper function '''
        res = list()
        tmp = key
        for _ in range(depth):
            if tmp != key:
                tmp = func("{0:x}".format(tmp))
            else:
                tmp = func(key)
            res.append(tmp)
        return res
    return hashing_func


@hash_with_depth_int
def default_fnv_1a(key, depth=1):
    ''' The default fnv-1a hashing routine

        Args:
            key (str): The element to be hashed
            depth (int): The number of hash permutations to compute
        Returns:
            list(int): List of size depth hashes '''
    return fnv_1a(key)


def fnv_1a(key):
    ''' Pure python implementation of the 64 bit fnv-1a hash

        Args:
            key (str): The element to be hashed
        Returns:
            int: 64-bit hashed representation of key
        Note:
            Uses the lower 64 bits when overflows occur '''
    max64mod = UINT64_T_MAX + 1
    hval = 14695981039346656073
    fnv_64_prime = 1099511628211
    for t_str in key:
        hval = hval ^ ord(t_str)
        hval = (hval * fnv_64_prime) % max64mod
    return hval


@hash_with_depth_bytes
def default_md5(key, depth=1):
    ''' The default md5 hashing routine

        Args:
            key (str): The element to be hashed
            depth (int): The number of hash permutations to compute
        Returns:
            int: 64-bit hashed representation of key
        Note:
            Returns the upper-most 64 bits '''
    return md5(key).digest()


@hash_with_depth_bytes
def default_sha256(key, depth=1):
    ''' The default sha256 hashing routine

        Args:
            key (str): The element to be hashed
            depth (int): The number of hash permutations to compute
        Returns:
            int: 64-bit hashed representation of key
        Note:
            Returns the upper-most 64 bits '''
    return sha256(key).digest()
