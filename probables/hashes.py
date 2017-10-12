''' Probables Hashing library '''
from __future__ import (unicode_literals, absolute_import, print_function)

from hashlib import (md5, sha256)
from struct import (unpack)

from . constants import (UINT64_T_MAX)


def default_fnv_1a(key, depth):
    ''' The default fnv-1a hashing routine

        Args:
            key (str): The element to be hashed
            depth (int): The number of hash permutations to compute
        Returns:
            list(int): List of size depth hashes '''
    res = list()
    tmp = key
    for _ in range(depth):
        if tmp != key:
            tmp = fnv_1a("{0:x}".format(tmp))
        else:
            tmp = fnv_1a(key)
        res.append(tmp)
    return res


def fnv_1a(key):
    ''' 64 bit fnv-1a hash

        Args:
            key (str): The element to be hashed
        Returns:
            int: 64-bit hashed representation of key '''
    max64mod = UINT64_T_MAX + 1
    hval = 14695981039346656073
    fnv_64_prime = 1099511628211
    for t_str in key:
        hval = hval ^ ord(t_str)
        hval = (hval * fnv_64_prime) % max64mod
    return hval


def default_md5(key, depth):
    ''' The defualt md5 hashing routine

        Args:
            key (str): The element to be hashed
            depth (int): The number of hash permutations to compute
        Returns:
            int: 64-bit hashed representation of key '''
    res = list()
    tmp = key.encode('utf-8')
    for _ in range(depth):
        tmp = md5(tmp).digest()
        res.append(unpack('Q', tmp[:8])[0])  # turn into 64 bit number
    return res


def default_sha256(key, depth):
    ''' The defualt sha256 hashing routine

        Args:
            key (str): The element to be hashed
            depth (int): The number of hash permutations to compute
        Returns:
            int: 64-bit hashed representation of key '''

    res = list()
    tmp = key.encode('utf-8')
    for _ in range(depth):
        tmp = sha256(tmp).digest()
        res.append(unpack('Q', tmp[:8])[0])  # turn into 64 bit number
    return res
