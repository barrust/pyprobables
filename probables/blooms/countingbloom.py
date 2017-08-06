''' CountingBloomFilter, python implementation
    License: MIT
    Author: Tyler Barrus (barrust@gmail.com)
    URL: https://github.com/barrust/counting_bloom
'''
from __future__ import (unicode_literals, absolute_import, print_function,
                        division)
from .. exceptions import (NotSupportedError)
from . basebloom import (BaseBloom)


class CountingBloomFilter(BaseBloom):
    ''' Simple Counting Bloom Filter implementation for use in python;
        It can read and write the same format as the c version
        (https://github.com/barrust/counting_bloom)

        Args:
            est_elements (int): The number of estimated elements to be added
            false_positive_rate (float): The desired false positive rate
            filepath (string): Path to file to load
            hex_string (string): Hex based representation to be loaded
            hash_function (function): Hashing strategy function to use \
            `hf(key, number)`
        Returns:
            CountingBloomFilter: A Counting Bloom Filter object

        Note:
            Initialization order of operations:
                1) From file
                2) From Hex String
                3) From params '''
    def __init__(self, est_elements=None, false_positive_rate=None,
                 filepath=None, hex_string=None, hash_function=None):
        ''' setup the basic values needed '''
        super(CountingBloomFilter, self).__init__('counting', est_elements,
                                                  false_positive_rate,
                                                  filepath, hex_string,
                                                  hash_function)
        self.__uint32_t_max = 2 ** 32 - 1

    def __str__(self):
        ''' correctly handle python 3 vs python2 encoding if necessary '''
        return self.__unicode__()

    def __unicode__(self):
        ''' string / unicode representation of the counting bloom filter '''
        on_disk = "no" if self.is_on_disk is False else "yes"

        cnt = 0
        total = 0
        largest = 0
        largest_idx = 0
        for i, val in enumerate(self._bloom):
            total += val
            if val > 0:
                cnt += val
            if val > largest:
                largest = val
                largest_idx = i
        fullness = cnt / self.number_bits
        els_added = total // self.number_hashes

        stats = ('CountingBloom:\n'
                 '\tbits: {0}\n'
                 '\testimated elements: {1}\n'
                 '\tnumber hashes: {2}\n'
                 '\tmax false positive rate: {3:.6f}\n'
                 '\telements added: {4}\n'
                 '\tcurrent false positive rate: {5:.6f}\n'
                 '\tis on disk: {6}\n'
                 '\tindex fullness: {7:.6}\n'
                 '\tmax index usage: {8}\n'
                 '\tmax index id: {9}\n'
                 '\tcalculated elements: {10}\n')
        return stats.format(self.number_bits, self.estimated_elements,
                            self.number_hashes, self.false_positive_rate,
                            self.elements_added,
                            self.current_false_positive_rate(), on_disk,
                            fullness, largest, largest_idx, els_added)

    def add(self, key, num_els=1):
        ''' Add the key to the Counting Bloom Filter

            Args:
                key (str): The element to be inserted
                num_els (int): Number of times to insert the element
            Returns:
                int: Maximum number of insertions
        '''
        hashes = self.hashes(key)
        return self.add_alt(hashes, num_els)

    def add_alt(self, hashes, num_els=1):
        ''' Add the element represented by hashes into the Counting Bloom
            Filter

            Args:
                hashes (list): A list of integers representing the key to \
                insert
                num_els (int): Number of times to insert the element
            Returns:
                int: Maximum number of insertions
        '''
        res = self.__uint32_t_max
        for i in list(range(0, self.number_hashes)):
            k = int(hashes[i]) % self.number_bits
            j = self._get_element(k)
            tmp = j + num_els
            if tmp <= self.__uint32_t_max:
                self._bloom[k] = self._get_set_element(j + num_els)
            else:
                self._bloom[k] = self.__uint32_t_max
            if self._bloom[k] < res:
                res = self._bloom[k]
        self.elements_added += num_els
        return res

    def check(self, key):
        ''' Check if the key is likely in the Counting Bloom Filter

            Args:
                key (str): The element to be checked
            Returns:
                int: Maximum number of insertions
        '''
        hashes = self.hashes(key)
        return self.check_alt(hashes)

    def check_alt(self, hashes):
        ''' Check if the element represented by hashes is in the Counting
            Bloom Filter

            Args:
                hashes (list): A list of integers representing the key to \
                check
            Returns:
                int: Maximum number of insertions
        '''
        res = self.__uint32_t_max
        for i in list(range(0, self.number_hashes)):
            k = int(hashes[i]) % self.number_bits
            tmp = self._get_element(k)
            if tmp < res:
                res = tmp
        return res

    def union(self, second):
        msg = 'Union is not supported for counting blooms'
        raise NotSupportedError(msg)

    def intersection(self, second):
        msg = 'Intersection is not supported for counting blooms'
        raise NotSupportedError(msg)

    def jaccard_index(self, second):
        msg = 'Jaccard Index is not supported for counting blooms'
        raise NotSupportedError(msg)
