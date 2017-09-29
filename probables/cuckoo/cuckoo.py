''' Cuckoo Filter, python implementation
    License: MIT
    Author: Tyler Barrus (barrust@gmail.com)
'''

from __future__ import (unicode_literals, absolute_import, print_function,
                        division)
import random
from itertools import chain

from .. hashes import (fnv_1a)
from .. utilities import (get_x_bits)
from .. exceptions import (CuckooFilterFullError)


class CuckooFilter(object):
    def __init__(self, capacity=10000, bucket_size=4, max_swaps=500):
        self.__bucket_size = bucket_size
        self.__cuckoo_capacity = capacity
        self.__max_cuckoo_swaps = max_swaps
        self.__buckets = list()
        for _ in range(self.capacity):
            self.__buckets.append(list())
        self.__hash_func = fnv_1a
        self.__inserted_elements = 0

    def __contains__(self, key):
        return self.check_element(key)

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
        hash_val = self.__hash_func(str(fingerprint))
        return hash_val % self.capacity

    def indicies_from_fingerprint(self, fingerprint):
        idx_1 = fingerprint % self.capacity
        idx_2 = self.__index_from_str(str(fingerprint))
        return idx_1, idx_2

    def generate_fingerprint_info(self, key):
        # generate the fingerprint along with the two possible indecies
        hash_val = self.__hash_func(key)
        fingerprint = get_x_bits(hash_val, 64, 32, True)
        idx_1, idx_2 = self.indicies_from_fingerprint(fingerprint)

        # NOTE: This should never happen...
        if idx_1 > self.capacity or idx_2 > self.capacity:
            msg = ('Either idx_1 {0} or idx_2 {1} is greater than {2}')
            raise ValueError(msg.format(idx_1, idx_2, self.capacity))
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

        for _ in range(self.__max_cuckoo_swaps):
            # select one element to be swapped out...
            swap_elm = random.randint(0, self.bucket_size - 1)

            swb = self.__buckets[idx][swap_elm]
            fingerprint, self.__buckets[idx][swap_elm] = swb, fingerprint

            # now find another place to put this fingerprint
            index_1, index_2 = self.indicies_from_fingerprint(fingerprint)

            idx = index_2 if idx == index_1 else index_1

            if self.__insert_element(fingerprint, idx):
                self.__inserted_elements += 1
                return idx
        raise CuckooFilterFullError('The CuckooFilter is currently full')

    def check_element(self, key):
        idx_1, idx_2, fingerprint = self.generate_fingerprint_info(key)
        if fingerprint in chain(self.__buckets[idx_1], self.__buckets[idx_2]):
            return True
        return False

    def remove_element(self, key):
        idx_1, idx_2, fingerprint = self.generate_fingerprint_info(key)
        if fingerprint in self.__buckets[idx_1]:
            self.__buckets[idx_1].remove(fingerprint)
            self.__inserted_elements -= 1
            return True
        elif fingerprint in self.__buckets[idx_2]:
            self.__buckets[idx_2].remove(fingerprint)
            self.__inserted_elements -= 1
            return True
        return False

    def __insert_element(self, fingerprint, idx):
        if len(self.__buckets[idx]) < self.__bucket_size:
            self.__buckets[idx].append(fingerprint)
            return True
        return False
