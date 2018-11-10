''' BloomFilter, python implementation
    License: MIT
    Author: Tyler Barrus (barrust@gmail.com)
    URL: https://github.com/barrust/pyprobables
'''
from __future__ import (unicode_literals, absolute_import, print_function)

from . bloom import (BloomFilter)


class ExpandingBloomFilter(object):

    def __init__(self, est_elements=None, false_positive_rate=None,
                 hash_function=None):
        ''' '''
        self._blooms = list()
        self.__fpr = false_positive_rate
        self.__est_elements = est_elements
        self.__hash_func = hash_function
        self.__added_elements = 0  # total added...
        # add in the initial bloom filter!
        self.__add_bloom_filter()

    def __contains__(self, key):
        return self.check(key)

    @property
    def blooms(self):
        return self._blooms

    @property
    def false_positive_rate(self):
        return self.__fpr

    @property
    def estimated_elements(self):
        return self.__est_elements

    @property
    def elements_added(self):
        return self.__added_elements

    def __add_bloom_filter(self):
        ''' build a new bloom and add it on! '''
        blm = BloomFilter(self.__est_elements, self.__fpr, self.__hash_func)
        self._blooms.append(blm)

    def __check_for_growth(self):
        if self._blooms[-1].elements_added >= self.__est_elements:
            self.__add_bloom_filter()

    def check(self, key):
        ''' check to see if it is in any of the bloom filters '''
        hashes = self._blooms[0].hashes(key)
        return self.check_alt(hashes)

    def check_alt(self, hashes):
        ''' an alternative method to check the bloom filter '''
        for blm in self._blooms:
            if blm.check_alt(hashes):
                return True
        return False

    def add(self, key, force=False):
        ''' Adds the key if it isn't in the bloom filter '''
        hashes = self._blooms[0].hashes(key)
        self.add_alt(hashes, force)

    def add_alt(self, hashes, force=False):
        ''' '''
        self.__added_elements += 1
        if force or not self.check_alt(hashes):
            self.__check_for_growth()
            self._blooms[-1].add_alt(hashes)
