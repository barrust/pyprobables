''' Counting Cuckoo Filter, python implementation
    License: MIT
    Author: Tyler Barrus (barrust@gmail.com)
'''
import random

from . cuckoo import (CuckooFilter)
from .. exceptions import (CuckooFilterFullError, NotSupportedError)


class CountingCuckooFilter(CuckooFilter):
    ''' Simple Counting Cuckoo Filter implementation

        Args:
            capacity (int): The number of bins
            bucket_size (int): The number of buckets per bin
            max_swaps (int): The number of cuckoo swaps before stopping
            expansion_rate (int): The rate at which to expand
            auto_expand (bool): If the filter should automatically expand
            filename (str): The path to the file to load or None if no file
        Returns:
            CountingCuckooFilter: A Cuckoo Filter object
        Raises:
            NotSupportedError: Loading a previously exported filter is \
            currently not supported
    '''
    def __init__(self, capacity=10000, bucket_size=4, max_swaps=500,
                 expansion_rate=2, auto_expand=True, filepath=None):
        ''' setup the data structure '''
        super(CountingCuckooFilter,
              self).__init__(capacity, bucket_size, max_swaps,
                             expansion_rate, auto_expand, filepath)
        self.__unique_elements = 0

    def __contains__(self, val):
        ''' setup the `in` keyword '''
        if self.check(val) > 0:
            return True
        return False

    @property
    def unique_elements(self):
        ''' int: unique number of elements inserted '''
        return self.__unique_elements

    def add(self, key):
        ''' Add element key to the filter

            Args:
                key (str): The element to add
            Raises:
                CuckooFilterFullError: When element not inserted after \
                maximum number of swaps or 'kicks' '''
        idx_1, idx_2, fingerprint = self._generate_fingerprint_info(key)

        is_present = self._check_if_present(idx_1, idx_2, fingerprint)
        if is_present is not None:
            for bucket in self.buckets[is_present]:
                if fingerprint in bucket:
                    bucket.increment()
                    self._inserted_elements += 1
                    return
        finger = self._insert_fingerprint(fingerprint, idx_1, idx_2)
        if finger is None:
            return
        elif self.auto_expand:
            self.__expand_logic(finger)
        else:
            msg = 'The CountingCuckooFilter is currently full'
            raise CuckooFilterFullError(msg)

    def check(self, key):
        ''' Check if an element is in the filter

            Args:
                key (str): Element to check
            Returns:
                int: The number of times inserted into the filter '''
        idx_1, idx_2, fingerprint = self._generate_fingerprint_info(key)
        is_present = self._check_if_present(idx_1, idx_2, fingerprint)
        if is_present is not None:
            # get the count out!
            for bucket in self.buckets[is_present]:
                if fingerprint in bucket:
                    return bucket.count
        return 0

    def remove(self, key):
        ''' Remove an element from the filter

            Args:
                key (str): Element to remove '''
        idx_1, idx_2, fingerprint = self._generate_fingerprint_info(key)
        idx = self._check_if_present(idx_1, idx_2, fingerprint)
        if idx is None:
            return False
        for bucket in self.buckets[idx]:
            if fingerprint in bucket:
                bucket.decrement()
                self._inserted_elements -= 1
                if bucket.count == 0:
                    self.buckets[idx].remove(bucket)
                    self.__unique_elements -= 1
                return True

    def expand(self):
        ''' Expand the cuckoo filter '''
        self.__expand_logic(None)

    def export(self, filepath):
        ''' Export cuckoo filter to file

            Args:
                filename (str): Path to file to export
            Raises:
                NotSupportedError: Currently not supported!
        '''
        msg = ('Exporting a counting cuckoo filter to file is not currently '
               'supported')
        raise NotSupportedError(msg)

    def _insert_fingerprint(self, fingerprint, idx_1, idx_2, count=1):
        ''' insert a fingerprint '''
        if self.__insert_element(fingerprint, idx_1, count):
            self._inserted_elements += 1
            self.__unique_elements += 1
            return
        elif self.__insert_element(fingerprint, idx_2, count):
            self._inserted_elements += 1
            self.__unique_elements += 1
            return

        # we didn't insert, so now we need to randomly select one index to use
        # and move things around to the other index, if possible, until we
        # either move everything around or hit the maximum number of swaps
        idx = random.choice([idx_1, idx_2])
        prv_bin = CountingCuckooBin(fingerprint, 1)
        for _ in range(self.max_swaps):
            # select one element to be swapped out...
            swap_elm = random.randint(0, self.bucket_size - 1)
            swap_finger = self.buckets[idx][swap_elm]
            prv_bin, self.buckets[idx][swap_elm] = swap_finger, prv_bin

            # now find another place to put this fingerprint
            index_1, index_2 = self._indicies_from_fingerprint(prv_bin.finger)

            idx = index_2 if idx == index_1 else index_1

            if self.__insert_element(prv_bin.finger, idx, prv_bin.count):
                self._inserted_elements += 1
                self.__unique_elements += 1
                return

        # if we got here we have an error... we might need to know what is left
        return prv_bin

    def _check_if_present(self, idx_1, idx_2, fingerprint):
        ''' wrapper for checking if fingerprint is already inserted '''
        if fingerprint in [x.finger for x in self.buckets[idx_1]]:
            return idx_1
        elif fingerprint in [x.finger for x in self.buckets[idx_2]]:
            return idx_2
        return None

    def _load(self, filepath):
        ''' load a previously exported filter '''
        msg = ('Loading a counting cuckoo filter from file is not currently '
               'supported')
        raise NotSupportedError(msg)

    def __expand_logic(self, extra_fingerprint):
        ''' the logic to acutally expand the cuckoo filter '''
        # get all the fingerprints
        fingerprints = self._setup_expand(extra_fingerprint)

        for elm in fingerprints:
            idx_1, idx_2 = self._indicies_from_fingerprint(elm.finger)
            res = self._insert_fingerprint(elm.finger, idx_1, idx_2,
                                           elm.count)
            if res is not None:  # again, this *shouldn't* happen
                msg = ('The CountingCuckooFilter failed to expand')
                raise CuckooFilterFullError(msg)

    def __insert_element(self, fingerprint, idx, count=1):
        ''' insert an element '''
        if len(self.buckets[idx]) < self.bucket_size:
            self.buckets[idx].append(CountingCuckooBin(fingerprint, count))
            return True
        return False


class CountingCuckooBin(object):
    ''' A container class for the counting cuckoo filter '''

    # keep it lightweight
    __slots__ = ['__fingerprint', '__count']

    def __init__(self, fingerprint, count):
        ''' init '''
        self.__fingerprint = fingerprint
        self.__count = count

    def __contains__(self, val):
        ''' setup the `in` construct '''
        return self.__fingerprint == val

    @property
    def finger(self):
        ''' fingerprint property '''
        return self.__fingerprint

    @property
    def count(self):
        ''' count property '''
        return self.__count

    def __repr__(self):
        ''' how do we represent this? '''
        return self.__str__()

    def __str__(self):
        ''' convert it into a string '''
        return '(fingerprint:{} count:{})'.format(self.__fingerprint,
                                                  self.__count)

    def increment(self):
        ''' increment '''
        self.__count += 1
        return self.__count

    def decrement(self):
        ''' decrement '''
        self.__count -= 1
        return self.__count
