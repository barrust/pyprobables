''' Cuckoo Filter, python implementation
    License: MIT
    Author: Tyler Barrus (barrust@gmail.com)
'''

from __future__ import (unicode_literals, absolute_import, print_function,
                        division)
import random

from .. hashes import (fnv_1a)
from .. utilities import (get_leftmost_bits)


class CuckooFilter(object):
    def __init__(self, capacity=10000, bucket_size=4, max_swaps=500):
        self.__bucket_size = bucket_size
        self.__cuckoo_capacity = capacity
        self.__max_cuckoo_swaps = max_swaps
        self.__buckets = list()
        for _ in range(self.capacity):
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

        fingerprint = get_leftmost_bits(hash_val, 64, 32)

        idx_1 = hash_val % self.capacity
        idx_2 = (idx_1 ^ self.__hash_func(str(fingerprint))) % self.capacity

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
        rand_idx = random.choice([idx_1, idx_2])
        for _ in range(self.__max_cuckoo_swaps):
            # select one element to be swapped out...
            swap_idx = random.randrange(0, len(self.__buckets[rand_idx]))
            swb = self.__buckets[rand_idx][swap_idx]
            fingerprint, self.__buckets[rand_idx][swap_idx] = swb, fingerprint

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
