''' BloomFilter, python implementation
    License: MIT
    Author: Tyler Barrus (barrust@gmail.com)
'''
from __future__ import (unicode_literals, absolute_import, print_function,
                        division)
import sys
import math
import os
from numbers import Number
from abc import (abstractmethod)
from struct import (pack, unpack, calcsize, Struct)
from binascii import (hexlify, unhexlify)

from .. exceptions import (InitializationError)
from .. hashes import (default_fnv_1a)
from .. utilities import (is_hex_string, is_valid_file)


class BaseBloom(object):
    ''' basic bloom filter object '''
    def __init__(self, blm_type, est_elements=None, false_positive_rate=None,
                 filepath=None, hex_string=None, hash_function=None):
        ''' setup the basic values needed '''
        self._bloom = None
        self.__num_bits = 0  # number of bits
        self.__est_elements = est_elements
        self.__fpr = 0.0
        self.__number_hashes = 0
        self.__hash_func = default_fnv_1a
        self._els_added = 0
        self._on_disk = False  # not on disk
        self.__blm_type = blm_type
        if self.__blm_type in ['regular', 'reg-ondisk']:
            self.__impt_type = 'B'
        else:
            self.__impt_type = 'I'

        if blm_type in ['regular', 'reg-ondisk']:
            msg = ('Insufecient parameters to set up the Bloom Filter')
        else:
            msg = ('Insufecient parameters to set up the Counting Bloom '
                   'Filter')

        if is_valid_file(filepath):
            self.__load(blm_type, filepath, hash_function)
        elif is_hex_string(hex_string):
            self._load_hex(hex_string, hash_function)
        elif est_elements is not None and false_positive_rate is not None:
            vals = self._set_optimized_params(est_elements,
                                              false_positive_rate,
                                              hash_function)
            self.__hash_func = vals[0]
            self.__fpr = vals[1]
            self.__number_hashes = vals[2]
            self.__num_bits = vals[3]
            if blm_type in ['regular', 'reg-ondisk']:
                self.__bloom_length = int(math.ceil(self.__num_bits / 8.0))
            else:
                self.__bloom_length = self.number_bits
            if blm_type not in ['reg-ondisk']:
                self._bloom = [0] * self.bloom_length
        else:
            raise InitializationError(msg)

    def __contains__(self, key):
        ''' setup the `in` keyword '''
        return self.check(key)

    def clear(self):
        ''' Clear or reset the Counting Bloom Filter '''
        self._els_added = 0
        for idx in range(self.bloom_length):
            self._bloom[idx] = self._get_set_element(0)

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
        ''' int: The number of hashes required for the Bloom Filter hashing
            strategy

            Note:
                Not settable '''
        return self.__number_hashes

    @property
    def number_bits(self):
        ''' int: Number of bits in the Bloom Filter

            Note:
                Not settable '''
        return self.__num_bits

    @property
    def elements_added(self):
        ''' int: Number of elements added to the Bloom Filter

        Note:
            Changing this can cause the current false positive rate to \
            be reported incorrectly '''
        return self._els_added

    @elements_added.setter
    def elements_added(self, val):
        ''' set the els added '''
        self._els_added = val

    @property
    def is_on_disk(self):
        ''' bool: Is the Bloom Filter on Disk or not

        Note:
            Not settable '''
        return self._on_disk

    @property
    def bloom_length(self):
        ''' int: Length of the Bloom Filter array

        Note:
            Not settable '''
        return self.__bloom_length

    @property
    def bloom(self):
        ''' list(int): The bit/int array '''
        return self._bloom

    @property
    def hash_function(self):
        ''' function: The hash function used

        Note:
            Not settable '''
        return self.__hash_func

    def hashes(self, key, depth=None):
        ''' Return the hashes based on the provided key

            Args:
                key (str): Description of arg1
                depth (int): Number of permutations of the hash to generate; \
                if None, generate `number_hashes`
            Returns:
                List(int): A list of the hashes for the key in int form '''
        tmp = depth if depth is not None else self.number_hashes
        return self.__hash_func(key, tmp)

    @staticmethod
    def _set_optimized_params(estimated_elements, false_positive_rate,
                              hash_function):
        ''' set the parameters to the optimal sizes '''
        if hash_function is None:
            tmp_hash = default_fnv_1a
        else:
            tmp_hash = hash_function

        valid_prms = (isinstance(estimated_elements, Number) and
                      estimated_elements > 0)
        if not valid_prms:
            msg = 'Bloom: estimated elements must be greater than 0'
            raise InitializationError(msg)
        valid_prms = (isinstance(false_positive_rate, Number) and
                      0.0 <= false_positive_rate < 1.0)
        if not valid_prms:
            msg = 'Bloom: false positive rate must be between 0.0 and 1.0'
            raise InitializationError(msg)

        fpr = pack('f', float(false_positive_rate))
        t_fpr = unpack('f', fpr)[0]  # to mimic the c version!
        # optimal caluclations
        n_els = estimated_elements
        fpr = float(false_positive_rate)
        m_bt = math.ceil((-n_els * math.log(fpr)) / 0.4804530139182)  # ln(2)^2
        number_hashes = int(round(math.log(2.0) * m_bt / n_els))

        if number_hashes <= 0:  # this should never happen...
            msg = 'Bloom: Number hashes is zero; unusable parameters provided'
            raise InitializationError(msg)

        return tmp_hash, t_fpr, number_hashes, int(m_bt)

    def __load(self, blm_type, filename, hash_function=None):
        ''' load the Bloom Filter from file '''
        # read in the needed information, and then call _set_optimized_params
        # to set everything correctly
        with open(filename, 'rb') as filepointer:
            offset = calcsize('QQf')
            filepointer.seek(offset * -1, os.SEEK_END)
            mybytes = unpack('QQf', filepointer.read(offset))
            vals = self._set_optimized_params(mybytes[0], mybytes[2],
                                              hash_function)
            self.__hash_func = vals[0]
            self.__fpr = vals[1]
            self.__number_hashes = vals[2]
            self.__num_bits = vals[3]
            if blm_type in ['regular', 'reg-ondisk']:
                self.__bloom_length = int(math.ceil(self.__num_bits / 8.0))
            else:
                self.__bloom_length = self.number_bits
            # now read in the bit array!
            filepointer.seek(0, os.SEEK_SET)
            offset = calcsize(self.__impt_type) * self.bloom_length
            rep = self.__impt_type * self.bloom_length
            self._bloom = list(unpack(rep, filepointer.read(offset)))

    def _load_hex(self, hex_string, hash_function=None):
        ''' placeholder for loading from hex string '''
        offset = calcsize('>QQf') * 2
        stct = Struct('>QQf')
        tmp_data = stct.unpack_from(unhexlify(hex_string[-offset:]))
        vals = self._set_optimized_params(tmp_data[0], tmp_data[2],
                                          hash_function)
        self.__hash_func = vals[0]
        self.__fpr = vals[1]
        self.__number_hashes = vals[2]
        self.__num_bits = vals[3]
        if self.__blm_type in ['regular', 'reg-ondisk']:
            self.__bloom_length = int(math.ceil(self.__num_bits / 8.0))
        else:
            self.__bloom_length = self.number_bits

        tmp_bloom = unhexlify(hex_string[:-offset])
        rep = self.__impt_type * self.bloom_length
        self._bloom = list(unpack(rep, tmp_bloom))

    def export_hex(self):
        ''' Export the Bloom Filter as a hex string

            Return:
                str: Hex representation of the Bloom Filter '''
        mybytes = pack('>QQf', self.estimated_elements,
                       self.elements_added, self.false_positive_rate)
        if self.__blm_type in ['regular', 'reg-ondisk']:
            bytes_string = hexlify(bytearray(self.bloom)) + hexlify(mybytes)
        else:
            bytes_string = b''
            for val in self.bloom:
                bytes_string += hexlify(pack(self.__impt_type, val))
            bytes_string += hexlify(mybytes)
        if sys.version_info > (3, 0):  # python 3 gives us bytes
            return str(bytes_string, 'utf-8')
        return bytes_string

    def export(self, filename):
        ''' Export the Bloom Filter to disk

            Args:
                filename (str): The filename to which the Bloom Filter will \
                be written. '''
        with open(filename, 'wb') as filepointer:
            rep = self.__impt_type * self.bloom_length
            filepointer.write(pack(rep, *self.bloom))
            filepointer.write(pack('QQf', self.estimated_elements,
                                   self.elements_added,
                                   self.false_positive_rate))

    def export_size(self):
        ''' Calculate the size of the bloom on disk

            Returns:
                int: Size of the Bloom Filter when exported to disk '''
        tmp_b = calcsize(self.__impt_type)
        return (self.bloom_length * tmp_b) + calcsize('QQf')

    def current_false_positive_rate(self):
        ''' Calculate the current false positive rate based on elements added

            Return:
                float: The current false positive rate '''
        num = self.number_hashes * -1 * self.elements_added
        dbl = num / float(self.number_bits)
        exp = math.exp(dbl)
        return math.pow((1 - exp), self.number_hashes)

    def estimate_elements(self):
        ''' Estimate the number of unique elements added

            Returns:
                int: Number of elements estimated to be inserted '''
        setbits = self._cnt_number_bits_set()
        log_n = math.log(1 - (float(setbits) / float(self.number_bits)))
        tmp = float(self.number_bits) / float(self.number_hashes)
        return int(-1 * tmp * log_n)

    @staticmethod
    def __cnt_set_bits(i):
        ''' count number of bits set in this int '''
        return bin(i).count("1")

    def _cnt_number_bits_set(self):
        ''' calculate the total number of set bits in the bloom '''
        setbits = 0
        for i in list(range(0, self.bloom_length)):
            setbits += self.__cnt_set_bits(self._get_element(i))
        return setbits

    def _get_element(self, idx):
        ''' wrappper for getting an element from the Bloom Filter! '''
        return self._bloom[idx]

    @staticmethod
    def _get_set_element(tmp_bit):
        ''' wrappper to use similar functions always! '''
        return tmp_bit

    def add(self, key):
        ''' Add the key to the Bloom Filter

            Args:
                key (str): The element to be inserted '''
        hashes = self.hashes(key)
        self.add_alt(hashes)

    def add_alt(self, hashes):
        ''' Add the element represented by hashes into the Bloom Filter

            Args:
                hashes (list): A list of integers representing the key to \
                insert '''
        for i in list(range(0, self.number_hashes)):
            k = int(hashes[i]) % self.number_bits
            idx = k // 8
            j = self._get_element(idx)
            tmp_bit = int(j) | int((1 << (k % 8)))
            self._bloom[idx] = self._get_set_element(tmp_bit)
        self._els_added += 1

    def check(self, key):
        ''' Check if the key is likely in the Bloom Filter

            Args:
                key (str): The element to be checked
            Returns:
                bool: True if likely encountered, False if definately not '''
        hashes = self.hashes(key)
        return self.check_alt(hashes)

    def check_alt(self, hashes):
        ''' Check if the element represented by hashes is in the Bloom Filter

            Args:
                hashes (list): A list of integers representing the key to \
                check
            Returns:
                bool: True if likely encountered, False if definately not '''
        for i in list(range(0, self.number_hashes)):
            k = int(hashes[i]) % self.number_bits
            if (int(self._get_element(k // 8)) & int((1 << (k % 8)))) == 0:
                return False
        return True

    @abstractmethod
    def union(self, second):
        ''' Return a new Bloom Filter that contains the union of the two '''
        pass

    @abstractmethod
    def intersection(self, second):
        ''' Return a new Bloom Filter that contains the intersection of the
            two '''
        pass

    @abstractmethod
    def jaccard_index(self, second):
        ''' Return a the Jaccard Similarity score between two bloom filters '''
        pass

    def _verify_bloom_similarity(self, second):
        ''' can the blooms be used in intersection, union, or jaccard index '''
        hash_match = self.number_hashes != second.number_hashes
        same_bits = self.number_bits != second.number_bits
        next_hash = self.hashes("test") != second.hashes("test")
        if hash_match or same_bits or next_hash:
            return False
        return True
