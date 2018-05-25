''' CountingBloomFilter, python implementation
    License: MIT
    Author: Tyler Barrus (barrust@gmail.com)
    URL: https://github.com/barrust/counting_bloom
'''
from __future__ import (unicode_literals, absolute_import, print_function,
                        division)

from . basebloom import (BaseBloom)
from .. constants import (UINT32_T_MAX, UINT64_T_MAX)

MISMATCH_MSG = ('The parameter second must be of type CountingBloomFilter')


def _verify_not_type_mismatch(second):
    ''' verify that there is not a type mismatch '''
    if not isinstance(second, (CountingBloomFilter)):
        return False
    return True


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
        super(CountingBloomFilter,
              self).__init__('counting', est_elements=est_elements,
                             false_positive_rate=false_positive_rate,
                             filepath=filepath, hex_string=hex_string,
                             hash_function=hash_function)

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
                int: Maximum number of insertions '''
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
                int: Maximum number of insertions '''
        res = UINT32_T_MAX
        for i in list(range(0, self.number_hashes)):
            k = int(hashes[i]) % self.number_bits
            j = self._get_element(k)
            tmp = j + num_els
            if tmp <= UINT32_T_MAX:
                self.bloom[k] = self._get_set_element(j + num_els)
            else:
                self.bloom[k] = UINT32_T_MAX
            if self.bloom[k] < res:
                res = self.bloom[k]
        self.elements_added += num_els
        if self.elements_added > UINT64_T_MAX:
            self.elements_added = UINT64_T_MAX
        return res

    def check(self, key):
        ''' Check if the key is likely in the Counting Bloom Filter

            Args:
                key (str): The element to be checked
            Returns:
                int: Maximum number of insertions '''
        hashes = self.hashes(key)
        return self.check_alt(hashes)

    def check_alt(self, hashes):
        ''' Check if the element represented by hashes is in the Counting
            Bloom Filter

            Args:
                hashes (list): A list of integers representing the key to \
                check
            Returns:
                int: Maximum number of insertions '''
        res = UINT32_T_MAX
        for i in list(range(0, self.number_hashes)):
            k = int(hashes[i]) % self.number_bits
            tmp = self._get_element(k)
            if tmp < res:
                res = tmp
        return res

    def remove(self, key, num_els=1):
        ''' Remove the element from the counting bloom

            Args:
                key (str): The element to be removed
                num_els (int): Number of times to remove the element
            Returns:
                int: Maximum number of insertions after the removal '''
        hashes = self.hashes(key)
        return self.remove_alt(hashes, num_els)

    def remove_alt(self, hashes, num_els=1):
        ''' Remvoe the element represented by hashes from the Counting Bloom \
            Filter

            Args:
                hashes (list): A list of integers representing the key to \
                remove
                num_els (int): Number of times to remove the element
            Returns:
                int: Maximum number of insertions after the removal '''
        tmp = self.check_alt(hashes)
        if tmp == UINT32_T_MAX:  # cannot remove if we have hit the max
            return UINT32_T_MAX
        elif tmp == 0:
            return 0

        # determine how many we can actually remove
        if tmp - num_els < 0:
            t_num_els = tmp
        else:
            t_num_els = num_els
        for i in list(range(self.number_hashes)):
            k = int(hashes[i]) % self.number_bits
            j = self._get_element(k)
            self.bloom[k] = self._get_set_element(j - t_num_els)
        self.elements_added -= t_num_els
        return tmp - t_num_els

    def intersection(self, second):
        ''' Take the intersection of two Counting Bloom Filters

            Args:
                second (CountingBloomFilter): The Bloom Filter with which to \
                take the intersection
            Returns:
                CountingBloomFilter: The new Counting Bloom Filter containing \
                the union
            Raises:
                TypeError: When second is not a :class:`CountingBloomFilter`
            Note:
                The elements_added property will be set to the estimated \
                number of unique elements added as found in \
                estimate_elements() '''
        if not _verify_not_type_mismatch(second):
            raise TypeError(MISMATCH_MSG)

        if super(CountingBloomFilter,
                 self)._verify_bloom_similarity(second) is False:
            return None
        res = CountingBloomFilter(est_elements=self.estimated_elements,
                                  false_positive_rate=self.false_positive_rate,
                                  hash_function=self.hash_function)

        for i in list(range(self.bloom_length)):
            if self._get_element(i) > 0 and second._get_element(i) > 0:
                tmp = self._get_element(i) + second._get_element(i)
                res.bloom[i] = self._get_set_element(tmp)
        res.elements_added = res.estimate_elements()
        return res

    def jaccard_index(self, second):
        ''' Take the Jaccard Index of two Counting Bloom Filters

            Args:
                second (CountingBloomFilter): The Bloom Filter with which to \
                take the jaccard index
            Returns:
                float: A numeric value between 0 and 1 where 1 is identical \
                and 0 means completely different
            Raises:
                TypeError: When second is not a :class:`CountingBloomFilter`
            Note:
                The Jaccard Index is based on the unique set of elements \
                added and not the number of each element added '''
        if not _verify_not_type_mismatch(second):
            raise TypeError(MISMATCH_MSG)

        if super(CountingBloomFilter,
                 self)._verify_bloom_similarity(second) is False:
            return None

        count_union = 0
        count_inter = 0
        for i in list(range(self.bloom_length)):
            if self._get_element(i) > 0 or second._get_element(i) > 0:
                count_union += 1
            if self._get_element(i) > 0 and second._get_element(i) > 0:
                count_inter += 1
        if count_union == 0:
            return 1.0
        return count_inter / count_union

    def union(self, second):
        ''' Return a new Countiong Bloom Filter that contains the union of
            the two

            Args:
                second (CountingBloomFilter): The Counting Bloom Filter with \
                which to calculate the union
            Returns:
                CountingBloomFilter: The new Counting Bloom Filter containing \
                the union
            Raises:
                TypeError: When second is not a :class:`CountingBloomFilter`
            Note:
                The elements_added property will be set to the estimated \
                number of unique elements added as found in \
                estimate_elements() '''
        if not _verify_not_type_mismatch(second):
            raise TypeError(MISMATCH_MSG)

        if super(CountingBloomFilter,
                 self)._verify_bloom_similarity(second) is False:
            return None
        res = CountingBloomFilter(est_elements=self.estimated_elements,
                                  false_positive_rate=self.false_positive_rate,
                                  hash_function=self.hash_function)
        for i in list(range(self.bloom_length)):
            tmp = self._get_element(i) + second._get_element(i)
            res.bloom[i] = self._get_set_element(tmp)
        res.elements_added = res.estimate_elements()
        return res

    def _cnt_number_bits_set(self):
        ''' calculate the total number of set bits in the bloom '''
        cnt = 0
        for i in list(range(self.bloom_length)):
            if self._get_element(i) > 0:
                cnt += 1
        return cnt
