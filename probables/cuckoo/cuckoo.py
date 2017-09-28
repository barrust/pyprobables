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
        # self.__fingerprint_size = len(bin(capacity).lstrip('0b')) // 16
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

    def __index_from_str(self, fingerprint):
        hash_val = self.__hash_func(fingerprint)
        return hash_val % self.capacity

    def indicies_from_fingerprint(self, fingerprint):
        idx_1 = self.__index_from_str(fingerprint)
        idx_2 = self.__index_from_str(fingerprint[::-1])
        return idx_1, idx_2

    def generate_fingerprint_info(self, key):
        # generate the fingerprint along with the two possible indecies
        hash_val = self.__hash_func(key)
        fingerprint = str(hash_val).encode()[:8]
        idx_1, idx_2 = self.indicies_from_fingerprint(str(fingerprint))

        if idx_1 > self.capacity or idx_2 > self.capacity:
            msg = ('Either idx_1 {0} or idx_2 {1} is greater than {2}')
            print(msg.format(idx_1, idx_2, self.capacity))
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
        idx = random.choice([idx_1, idx_2])
        # print(idx)
        for i in range(self.__max_cuckoo_swaps):
            # select one element to be swapped out...
            swap_elm = random.randint(0, self.bucket_size - 1)

            swb = self.__buckets[idx][swap_elm]
            fingerprint, self.__buckets[idx][swap_elm] = swb, fingerprint

            # now find another place to put this fingerprint
            index_1, index_2 = self.indicies_from_fingerprint(fingerprint)

            if idx == index_1:
                idx = index_2
            else:
                idx = index_1

            if self.__insert_element(fingerprint, idx):
                self.__inserted_elements += 1
                return idx
        # TODO: This should throw an exception
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
