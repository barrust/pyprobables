''' Cuckoo Filter, python implementation
    License: MIT
    Author: Tyler Barrus (barrust@gmail.com)
'''

from __future__ import (unicode_literals, absolute_import, print_function,
                        division)
import os
import random
from struct import (pack, unpack, calcsize)

from .. hashes import (fnv_1a)
from .. utilities import (get_x_bits)
from .. exceptions import (CuckooFilterFullError)


class CuckooFilter(object):
    ''' Simple Cuckoo Filter implementation

        Args:
            capacity (int): The number of bins
            bucket_size (int): The number of buckets per bin
            max_swaps (int): The number of cuckoo swaps before stopping
            expansion_rate (int): The rate at which to expand
            auto_expand (bool): If the filter should automatically expand
            filename (str): The path to the file to load or None if no file
        Returns:
            CuckooFilter: A Cuckoo Filter object
    '''
    def __init__(self, capacity=10000, bucket_size=4, max_swaps=500,
                 expansion_rate=2, auto_expand=True, filepath=None):
        ''' setup the data structure '''
        self.__bucket_size = bucket_size
        self.__cuckoo_capacity = capacity
        self.__max_cuckoo_swaps = max_swaps
        self.__expansion_rate = None
        self.expansion_rate = expansion_rate
        self.__auto_expand = None
        self.auto_expand = auto_expand

        self.__hash_func = fnv_1a
        self.__inserted_elements = 0
        if filepath is None:
            self.__buckets = list()
            for _ in range(self.capacity):
                self.__buckets.append(list())
        else:
            self.__load(filepath)

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

    @property
    def buckets(self):
        ''' list(list): The buckets holding the fingerprints

            Note:
                Not settable '''
        return self.__buckets

    @property
    def expansion_rate(self):
        ''' int: The rate at expansion when the filter grows'''
        return self.__expansion_rate

    @expansion_rate.setter
    def expansion_rate(self, val):
        ''' set the self expand value '''
        self.__expansion_rate = int(val)

    @property
    def auto_expand(self):
        ''' bool: True if the cuckoo filter will expand automatically '''
        return self.__auto_expand

    @auto_expand.setter
    def auto_expand(self, val):
        ''' set the self expand value '''
        self.__auto_expand = bool(val)

    def load_factor(self):
        ''' float: How full the Cuckoo Filter is currently '''
        return self.elements_added / (self.capacity * self.bucket_size)

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
            return
        finger = self._insert_fingerprint(fingerprint, idx_1, idx_2)
        if finger is None:
            return
        elif self.__auto_expand:
            self.__expand_logic(finger)
        else:
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

    def export(self, filename):
        ''' Export cuckoo filter to file

            Args:
                filename (str): Path to file to export
        '''
        with open(filename, 'wb') as filepointer:
            for bucket in self.__buckets:
                # do something for each...
                rep = len(bucket) * 'I'
                filepointer.write(pack(rep, *bucket))
                leftover = self.bucket_size - len(bucket)
                rep = leftover * 'I'
                filepointer.write(pack(rep, *([0] * leftover)))
            # now put out the required information at the end
            filepointer.write(pack('II', self.bucket_size, self.max_swaps))

    def expand(self):
        ''' Expand the cuckoo filter '''
        self.__expand_logic(None)

    def _insert_fingerprint(self, fingerprint, idx_1, idx_2):
        ''' insert a fingerprint '''
        if self.__insert_element(fingerprint, idx_1):
            self.__inserted_elements += 1
            return
        elif self.__insert_element(fingerprint, idx_2):
            self.__inserted_elements += 1
            return

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
                return

        # if we got here we have an error... we might need to know what is left
        return fingerprint

    def __load(self, filename):
        ''' load a cuckoo filter from file '''
        with open(filename, 'rb') as filepointer:
            offset = calcsize('II')
            int_size = calcsize('I')
            filepointer.seek(offset * -1, os.SEEK_END)
            list_size = filepointer.tell()
            mybytes = unpack('II', filepointer.read(offset))
            self.__bucket_size = mybytes[0]
            self.__max_cuckoo_swaps = mybytes[1]
            self.__cuckoo_capacity = list_size // int_size // self.bucket_size
            self.__inserted_elements = 0
            # now pull everything in!
            filepointer.seek(0, os.SEEK_SET)
            self.__buckets = list()
            for i in range(self.capacity):
                self.__buckets.append(list())
                for _ in range(self.bucket_size):
                    fingerprint = unpack('I', filepointer.read(int_size))[0]
                    if fingerprint != 0:
                        self.__buckets[i].append(fingerprint)
                        self.__inserted_elements += 1

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

    def __expand_logic(self, extra_fingerprint):
        ''' the logic to acutally expand the cuckoo filter '''
        # get all the fingerprints
        fingerprints = list()
        if extra_fingerprint is not None:
            fingerprints.append(extra_fingerprint)
        for idx in range(self.capacity):
            fingerprints.extend(self.buckets[idx])

        self.__cuckoo_capacity = self.capacity * self.expansion_rate
        self.__buckets = list()
        self.__inserted_elements = 0
        for _ in range(self.capacity):
            self.buckets.append(list())

        for finger in fingerprints:
            idx_1, idx_2 = self._indicies_from_fingerprint(finger)
            res = self._insert_fingerprint(finger, idx_1, idx_2)
            if res is not None:  # again, this *shouldn't* happen
                msg = ('The CuckooFilter failed to expand')
                raise CuckooFilterFullError(msg)

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
