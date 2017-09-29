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
    ''' Simple Cuckoo Filter implementation

        Args:
            capacity (int): The number of bins
            bucket_size (int): The number of buckets per bin
            max_swaps (int): The number of cuckoo swaps before stopping
        Returns:
            CuckooFilter: A Cuckoo Filter object
    '''
    def __init__(self, capacity=10000, bucket_size=4, max_swaps=500):
        ''' setup the data structure '''
        self.__bucket_size = bucket_size
        self.__cuckoo_capacity = capacity
        self.__max_cuckoo_swaps = max_swaps
        self.__buckets = list()
        for _ in range(self.capacity):
            self.__buckets.append(list())
        self.__hash_func = fnv_1a
        self.__inserted_elements = 0

    def __contains__(self, key):
        ''' setup the `in` keyword '''
        return self.check(key)

    @property
    def elements_added(self):
        ''' int: The number of elements added

            Note:
                Not settable '''
        return self.__inserted_elements

    @property
    def capacity(self):
        ''' int: The number of bins

            Note:
                Not settable '''
        return self.__cuckoo_capacity

    @property
    def max_swaps(self):
        ''' int: The maximum number of swaps to perform

            Note:
                Not settable '''
        return self.__max_cuckoo_swaps

    @property
    def bucket_size(self):
        ''' int: The number of buckets per bin

            Note:
                Not settable '''
        return self.__bucket_size

    def add(self, key):
        ''' Add element key to the filter

            Args:
                key (str): The element to add
            Raises:
                CuckooFilterFullError: When element not inserted after \
                maximum number of swaps or 'kicks' '''
        idx_1, idx_2, fingerprint = self._generate_fingerprint_info(key)

        is_present = self._check_if_present(idx_1, idx_2, fingerprint)
        if is_present is not None:  # already there, nothing to do
            return is_present

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
            index_1, index_2 = self._indicies_from_fingerprint(fingerprint)

            idx = index_2 if idx == index_1 else index_1

            if self.__insert_element(fingerprint, idx):
                self.__inserted_elements += 1
                return idx
        raise CuckooFilterFullError('The CuckooFilter is currently full')

    def check(self, key):
        ''' Check if an element is in the filter

            Args:
                key (str): Element to check '''
        idx_1, idx_2, fingerprint = self._generate_fingerprint_info(key)
        is_present = self._check_if_present(idx_1, idx_2, fingerprint)
        if is_present is not None:
            return True
        return False

    def remove(self, key):
        ''' Remove an element from the filter

            Args:
                key (str): Element to remove '''
        idx_1, idx_2, fingerprint = self._generate_fingerprint_info(key)
        idx = self._check_if_present(idx_1, idx_2, fingerprint)
        if idx is None:
            return False
        self.__buckets[idx].remove(fingerprint)
        self.__inserted_elements -= 1
        return True

    def _check_if_present(self, idx_1, idx_2, fingerprint):
        ''' wrapper for checking if fingerprint is already inserted '''
        if fingerprint in self.__buckets[idx_1]:
            return idx_1
        elif fingerprint in self.__buckets[idx_2]:
            return idx_2
        return None

    def __insert_element(self, fingerprint, idx):
        ''' insert element wrapper '''
        if len(self.__buckets[idx]) < self.__bucket_size:
            self.__buckets[idx].append(fingerprint)
            return True
        return False

    def _indicies_from_fingerprint(self, fingerprint):
        ''' Generate the possible insertion indicies from a fingerprint

            Args:
                fingerprint (int): The fingerprint to use for generating \
                indicies '''
        # NOTE: Should this even be public???
        idx_1 = fingerprint % self.capacity
        idx_2 = self.__hash_func(str(fingerprint)) % self.capacity
        return idx_1, idx_2

    def _generate_fingerprint_info(self, key):
        ''' Generate the fingerprint and indicies using the provided key

            Args:
                key (str): The element for which information is to be generated
        '''
        # NOTE: Should this even be public?
        # generate the fingerprint along with the two possible indecies
        hash_val = self.__hash_func(key)
        fingerprint = get_x_bits(hash_val, 64, 32, True)
        idx_1, idx_2 = self._indicies_from_fingerprint(fingerprint)

        # NOTE: This should never happen...
        if idx_1 > self.capacity or idx_2 > self.capacity:
            msg = ('Either idx_1 {0} or idx_2 {1} is greater than {2}')
            raise ValueError(msg.format(idx_1, idx_2, self.capacity))
        return idx_1, idx_2, fingerprint
