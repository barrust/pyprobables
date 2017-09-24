''' Cuckoo Filter, python implementation
    License: MIT
    Author: Tyler Barrus (barrust@gmail.com)
'''

from __future__ import (unicode_literals, absolute_import, print_function,
                        division)
import sys
import random
import struct
import binascii

from .. hashes import (fnv_1a)


class CuckooFilter(object):
    def __init__(self, capacity=10000, bucket_size=4, max_swaps=500):
        self.__bucket_size = bucket_size
        self.__cuckoo_capacity = capacity
        self.__max_cuckoo_swaps = max_swaps
        self.__buckets = list()
        for i in range(self.capacity):
            self.__buckets.append(list())  # we could pre-populate it with bins
        self.__hash_func = fnv_1a
        self.__inserted_elements = 0

    @property
    def elements_added(self):
        return self.__inserted_elements

    @property
    def capacity(self):
        return self.__cuckoo_capacity

    @property
    def max_swaps(self):
        return self.__max_cuckoo_swaps

    @property
    def bucket_size(self):
        return self.__bucket_size

    def generate_fingerprint_info(self, key):
        # generate the fingerprint along with the two possible indecies
        hash_val = self.__hash_func(key)

        # NOTE: these do not match in py2/py3
        hash_bytes = b'' + struct.pack(">Q", int(hash_val))
        hex_data = hex(int(hash_val))
        print(hex_data)
        hash_bytes = bytearray.fromhex(hex_data[2:])
        print(hash_bytes)

        idx_1 = hash_val % self.capacity

        fingerprint = bytes(hash_bytes[:4])  # fingerprint is the first 32 bits
        print(hash_val, hash_bytes, fingerprint)

        idx_2 = (idx_1 ^ self.__hash_func(str(fingerprint))) % self.capacity

        print(idx_1, idx_2, fingerprint, hash_bytes)

        return idx_1, idx_2, fingerprint

    def add_element(self, key):
        idx_1, idx_2, fingerprint = self.generate_fingerprint_info(key)
        if self.__insert_element(fingerprint, idx_1):
            self.__inserted_elements += 1
            return idx_1
        elif self.__insert_element(fingerprint, idx_2):
            self.__inserted_elements += 1
            return idx_2

        # we didn't insert, so now we need to randomly select one index to use
        # and move things around to the other index, if possible, until we
        # either move everything around or hit the maximum number of swaps
        rand_index = random.choice(idx_1, idx_2)
        for _ in range(self.__max_cuckoo_swaps):
            # select one element to be swapped out...
            swap_idx = random.randrange(0, len(self.__buckets[rand_index]))
            fingerprint, self.__buckets[rand_index][swap_idx] = self.__buckets[rand_index][swap_idx], fingerprint

            # now find another place to put this fingerprint
            _, _, rand_idx = self.generate_fingerprint_info(fingerprint)
            if self.__insert_element(fingerprint, rand_idx):
                self.__inserted_elements += 1
                return rand_idx
        print('Cuckoo Filter is full')

    def check_element(self, key):
        idx_1, idx_2, fingerprint = self.generate_fingerprint_info(key)
        if fingerprint in self.__buckets[idx_1]:
            return True
        if fingerprint in self.__buckets[idx_2]:
            return True
        return False

    def __insert_element(self, fingerprint, idx):
        if len(self.__buckets[idx]) < self.__bucket_size:
            self.__buckets[idx].append(fingerprint)
            return True
        return False
