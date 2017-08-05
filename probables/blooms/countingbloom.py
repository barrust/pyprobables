''' CountingBloomFilter, python implementation
    License: MIT
    Author: Tyler Barrus (barrust@gmail.com)
    URL: https://github.com/barrust/counting_bloom
'''
from __future__ import (unicode_literals, absolute_import, print_function,
                        division)
import sys
import math
import os
from struct import (pack, unpack, calcsize, Struct)
from binascii import (hexlify, unhexlify)
from .. exceptions import (InitializationError)
from .. hashes import (default_fnv_1a)
from .. utilities import (is_hex_string, is_valid_file)


class CountingBloomFilter(object):
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
        self._bloom = None
        self.__num_bits = 0  # number of bits
        self.__est_elements = 0
        self.__fpr = 0.0
        self.__number_hashes = 0
        self.__bloom_length = self.number_bits
        self.__hash_func = default_fnv_1a
        self._els_added = 0
        self._on_disk = False  # not on disk
        # self.__int32_t_min = -2147483648
        # self.__int32_t_max = 2147483647
        # self.__int64_t_min = -9223372036854775808
        # self.__int64_t_max = 9223372036854775807
        self.__uint64_t_max = 2 ** 64
        self.__uint32_t_max = 2 ** 32

        if is_valid_file(filepath):
            self.__load(filepath, hash_function)
        elif is_hex_string(hex_string):
            self._load_hex(hex_string, hash_function)
        elif est_elements is not None and false_positive_rate is not None:
            self._set_optimized_params(est_elements, false_positive_rate, 0,
                                       hash_function)
            self._bloom = [0] * self.bloom_length
        else:
            msg = ('Insufecient parameters to set up the Counting Bloom '
                   'Filter')
            raise InitializationError(msg)

    @property
    def false_positive_rate(self):
        ''' float: The maximum desired false positive rate

            Note:
                Not settable '''
        return self.__fpr

    @property
    def estimated_elements(self):
        ''' int: The maximum number of elements estimated to be added at setup

            Note:
                Not settable '''
        return self.__est_elements

    @property
    def number_hashes(self):
        ''' int: The number of hashes required for the Counting Bloom Filter \
            hashing strategy

            Note:
                Not settable '''
        return self.__number_hashes

    @property
    def number_bits(self):
        ''' int: Number of bits in the Counting Bloom Filter

            Note:
                Not settable '''
        return self.__num_bits

    @property
    def elements_added(self):
        ''' int: Number of elements added to the Counting Bloom Filter

        Note:
            Not settable '''
        return self._els_added

    @property
    def is_on_disk(self):
        ''' bool: Is the Counting Bloom Filter on Disk or not

        Note:
            Not settable '''
        return self._on_disk

    @property
    def bloom_length(self):
        ''' int: Length of the Counting Bloom Filter array

        Note:
            Not settable '''
        return self.__bloom_length

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

    def __contains__(self, key):
        ''' setup the `in` keyword '''
        return self.check(key)

    def clear(self):
        ''' Clear or reset the Counting Bloom Filter '''
        self._els_added = 0
        for idx in range(self.bloom_length):
            self._bloom[idx] = self._get_set_element(0)

    def hashes(self, key, depth=None):
        ''' Return the hashes based on the provided key

            Args:
                key (str): Description of arg1
                depth (int): Number of permutations of the hash to generate; \
                if None, generate `number_hashes`
            Returns:
                List(int): A list of the hashes for the key in int form
        '''
        tmp = depth if depth is not None else self.number_hashes
        return self.__hash_func(key, tmp)

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
            if self._bloom[k] < res:
                res = self._bloom[k]
        self._els_added += num_els
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

    def export(self, filename):
        ''' Export the Counting Bloom Filter to disk

            Args:
                filename (str): The filename to which the Bloom Filter will \
                be written.
        '''
        with open(filename, 'wb') as filepointer:
            rep = 'I' * self.bloom_length
            filepointer.write(pack(rep, *self._bloom))
            filepointer.write(pack('QQf', self.estimated_elements,
                                   self.elements_added,
                                   self.false_positive_rate))

    def __load(self, filename, hash_function=None):
        ''' load the Counting Bloom Filter from file '''
        # read in the needed information, and then call _set_optimized_params
        # to set everything correctly
        with open(filename, 'rb') as filepointer:
            offset = calcsize('QQf')
            filepointer.seek(offset * -1, os.SEEK_END)
            mybytes = unpack('QQf', filepointer.read(offset))
            self._set_optimized_params(mybytes[0], mybytes[2],
                                       mybytes[1], hash_function)

            # now read in the bit array!
            filepointer.seek(0, os.SEEK_SET)
            offset = calcsize('I') * self.bloom_length
            rep = 'I' * self.bloom_length
            self._bloom = list(unpack(rep, filepointer.read(offset)))

    def export_hex(self):
        ''' Export the Bloom Filter as a hex string

            Return:
                str: Hex representation of the Counting Bloom Filter
        '''
        mybytes = pack('>QQf', self.estimated_elements,
                       self.elements_added, self.false_positive_rate)
        bytes_string = hexlify(bytearray(self._bloom)) + hexlify(mybytes)
        if sys.version_info > (3, 0):  # python 3 gives us bytes
            return str(bytes_string, 'utf-8')
        return bytes_string

    def _load_hex(self, hex_string, hash_function=None):
        ''' placeholder for loading from hex string '''
        offset = calcsize('>QQf') * 2
        stct = Struct('>QQf')
        tmp_data = stct.unpack_from(unhexlify(hex_string[-offset:]))
        self._set_optimized_params(tmp_data[0], tmp_data[2], tmp_data[1],
                                   hash_function)
        tmp_bloom = unhexlify(hex_string[:-offset])
        rep = 'B' * self.bloom_length
        self._bloom = list(unpack(rep, tmp_bloom))

    def export_size(self):
        ''' Calculate the size of the counting bloom on disk

            Returns:
                int: Size of the Bloom Filter when exported to disk in bytes
        '''
        tmp_b = calcsize('I')
        return (self.bloom_length * tmp_b) + calcsize('QQf')

    def current_false_positive_rate(self):
        ''' Calculate the current false positive rate based on elements added

            Return:
                float: The current false positive rate
        '''
        num = self.number_hashes * -1 * self.elements_added
        dbl = num / float(self.number_bits)
        exp = math.exp(dbl)
        return math.pow((1 - exp), self.number_hashes)

    def _set_optimized_params(self, estimated_elements, false_positive_rate,
                              elements_added, hash_function):
        ''' set the parameters to the optimal sizes '''
        if hash_function is None:
            self.__hash_func = default_fnv_1a
        else:
            self.__hash_func = hash_function
        self.__est_elements = estimated_elements
        fpr = pack('f', float(false_positive_rate))
        self.__fpr = unpack('f', fpr)[0]  # to mimic the c version!
        self._els_added = elements_added
        # optimal caluclations
        n_els = self.estimated_elements
        fpr = float(self.__fpr)
        m_bt = math.ceil((-n_els * math.log(fpr)) / 0.4804530139182)  # ln(2)^2
        self.__number_hashes = int(round(math.log(2.0) * m_bt / n_els))
        self.__num_bits = int(m_bt)
        self.__bloom_length = self.__num_bits  # shortcut!

    def _get_element(self, idx):
        ''' wrappper for getting an element from the bloom filter! '''
        return self._bloom[idx]

    @staticmethod
    def _get_set_element(tmp_bit):
        ''' wrappper to use similar functions always! '''
        return tmp_bit
