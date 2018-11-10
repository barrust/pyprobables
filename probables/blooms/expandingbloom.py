''' BloomFilter, python implementation
    License: MIT
    Author: Tyler Barrus (barrust@gmail.com)
    URL: https://github.com/barrust/pyprobables
'''
from __future__ import (unicode_literals, absolute_import, print_function)

from . bloom import (BloomFilter)


class ExpandingBloomFilter(object):
    ''' Simple expanding Bloom Filter implementation for use in python; the
        Bloom Fiter will automatically expand, or grow, if the false
        positive rate is about to become greater than the desired false
        positive rate.

        Args:
            est_elements (int): The number of estimated elements to be added
            false_positive_rate (float): The desired false positive rate
            hash_function (function): Hashing strategy function to use \
            `hf(key, number)`
        Returns:
            ExpandingBloomFilter: An expanding Bloom Filter object
        Note:
            At this point, the expanding Bloom Filter does not support \
            `export` or `import` '''

    def __init__(self, est_elements=None, false_positive_rate=None,
                 hash_function=None):
        ''' initialize '''
        self._blooms = list()
        self.__fpr = false_positive_rate
        self.__est_elements = est_elements
        self.__hash_func = hash_function
        self.__added_elements = 0  # total added...
        # add in the initial bloom filter!
        self.__add_bloom_filter()

    def __contains__(self, key):
        ''' setup the `in` functionality '''
        return self.check(key)

    @property
    def expansions(self):
        ''' int: The number of expansions '''
        return len(self._blooms) - 1

    @property
    def false_positive_rate(self):
        ''' float: The desired false positive rate of the expanding Bloom \
                   Filter '''
        return self.__fpr

    @property
    def estimated_elements(self):
        '''int: The original number of elements estimated to be in the Bloom \
                Filter '''
        return self.__est_elements

    @property
    def elements_added(self):
        ''' int: The total number of elements added '''
        return self.__added_elements

    def __add_bloom_filter(self):
        ''' build a new bloom and add it on! '''
        blm = BloomFilter(self.__est_elements, self.__fpr, self.__hash_func)
        self._blooms.append(blm)

    def __check_for_growth(self):
        ''' detereming if the bloom filter should automatically grow '''
        if self._blooms[-1].elements_added >= self.__est_elements:
            self.__add_bloom_filter()

    def check(self, key):
        ''' Check to see if the key is in the Bloom Filter

            Args:
                key (str): The key to check for in the Bloom Filter
            Returns:
                bool: `True` if the element is likely present; `False` if \
                      definately not present '''
        hashes = self._blooms[0].hashes(key)
        return self.check_alt(hashes)

    def check_alt(self, hashes):
        ''' Check to see if the hashes are in the Bloom Filter

            Args:
                hashes (list): The hash representation to check for in the \
                               Bloom Filter
            Returns:
                bool: `True` if the element is likely present; `False` if \
                      definately not present '''
        for blm in self._blooms:
            if blm.check_alt(hashes):
                return True
        return False

    def add(self, key, force=False):
        ''' Add the key to the Bloom Filter

            Args:
                key (str): The element to be inserted
                force (bool): `True` will force it to be inserted, even if it \
                              likely has been inserted before \
                `False` will only insert if not found in the Bloom Filter '''
        hashes = self._blooms[0].hashes(key)
        self.add_alt(hashes, force)

    def add_alt(self, hashes, force=False):
        ''' Add the element represented by hashes into the Bloom Filter

            Args:
                hashes (list): A list of integers representing the key to insert
                force (bool): `True` will force it to be inserted, even if \
                              it likely has been inserted before \
                `False` will only insert if not found in the Bloom Filter '''
        self.__added_elements += 1
        if force or not self.check_alt(hashes):
            self.__check_for_growth()
            self._blooms[-1].add_alt(hashes)
