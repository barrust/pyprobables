''' BloomFilter, python implementation
    License: MIT
    Author: Tyler Barrus (barrust@gmail.com)
'''
from __future__ import (unicode_literals, absolute_import, print_function,
                        division)
import sys
import math
import os
from struct import (pack, unpack, calcsize, Struct)
from binascii import (hexlify, unhexlify)
from .. exceptions import (InitializationError, NotSupportedError)
from .. hashes import (default_fnv_1a)
from .. utilities import (is_hex_string, is_valid_file)


class BaseBloom(object):
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

        if blm_type in ['regular', 'reg-ondisk']:
            msg = ('Insufecient parameters to set up the Bloom Filter')
        else:
            msg = ('Insufecient parameters to set up the Counting Bloom '
                   'Filter')

        if is_valid_file(filepath):
            self.__load(blm_type, filepath, hash_function)
        elif is_hex_string(hex_string):
            self._load_hex(blm_type, hex_string, hash_function)
        elif est_elements is not None and false_positive_rate is not None:
            vals = self._set_optimized_params(est_elements,
                                              false_positive_rate, 0,
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
            Not settable '''
        return self._els_added

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
    def hash_function(self):
        return self.__hash_func

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


    def _set_optimized_params(self, estimated_elements, false_positive_rate,
                              elements_added, hash_function):
        ''' set the parameters to the optimal sizes '''
        if hash_function is None:
            tmp_hash = default_fnv_1a
        else:
            tmp_hash = hash_function

        fpr = pack('f', float(false_positive_rate))
        t_fpr = unpack('f', fpr)[0]  # to mimic the c version!
        # optimal caluclations
        n_els = estimated_elements
        fpr = float(false_positive_rate)
        m_bt = math.ceil((-n_els * math.log(fpr)) / 0.4804530139182)  # ln(2)^2
        number_hashes = int(round(math.log(2.0) * m_bt / n_els))

        return tmp_hash, t_fpr, number_hashes, int(m_bt)

    def __load(self, blm_type, filename, hash_function=None):
        ''' load the Bloom Filter from file '''
        # read in the needed information, and then call _set_optimized_params
        # to set everything correctly
        with open(filename, 'rb') as filepointer:
            offset = calcsize('QQf')
            filepointer.seek(offset * -1, os.SEEK_END)
            mybytes = unpack('QQf', filepointer.read(offset))
            vals =  self._set_optimized_params(mybytes[0], mybytes[2],
                                               mybytes[1], hash_function)
            self.__hash_func = vals[0]
            self.__fpr = vals[1]
            self.__number_hashes = vals[2]
            self.__num_bits = vals[3]
            if blm_type in ['regular', 'reg-ondisk']:
                impt_type = 'B'
                self.__bloom_length = int(math.ceil(self.__num_bits / 8.0))
            else:
                impt_type = 'I'
                self.__bloom_length = self.number_bits
            # now read in the bit array!
            filepointer.seek(0, os.SEEK_SET)
            offset = calcsize(impt_type) * self.bloom_length
            rep = impt_type * self.bloom_length
            self._bloom = list(unpack(rep, filepointer.read(offset)))

    def _load_hex(self, blm_type, hex_string, hash_function=None):
        ''' placeholder for loading from hex string '''
        offset = calcsize('>QQf') * 2
        stct = Struct('>QQf')
        tmp_data = stct.unpack_from(unhexlify(hex_string[-offset:]))
        vals = self._set_optimized_params(tmp_data[0], tmp_data[2],
                                          tmp_data[1], hash_function)
        self.__hash_func = vals[0]
        self.__fpr = vals[1]
        self.__number_hashes = vals[2]
        self.__num_bits = vals[3]
        if blm_type in ['regular', 'reg-ondisk']:
            impt_type = 'B'
            self.__bloom_length = int(math.ceil(self.__num_bits / 8.0))
        else:
            impt_type = 'B'
            self.__bloom_length = self.number_bits

        tmp_bloom = unhexlify(hex_string[:-offset])
        rep = impt_type * self.bloom_length
        self._bloom = list(unpack(rep, tmp_bloom))

    def export_hex(self):
        ''' Export the Bloom Filter as a hex string

            Return:
                str: Hex representation of the Bloom Filter
        '''
        mybytes = pack('>QQf', self.estimated_elements,
                       self.elements_added, self.false_positive_rate)
        bytes_string = hexlify(bytearray(self._bloom)) + hexlify(mybytes)
        if sys.version_info > (3, 0):  # python 3 gives us bytes
            return str(bytes_string, 'utf-8')
        return bytes_string

    def export(self, filename):
        ''' Export the Bloom Filter to disk

            Args:
                filename (str): The filename to which the Bloom Filter will \
                be written.
        '''
        with open(filename, 'wb') as filepointer:
            if self.__blm_type == 'regular' or self.__blm_type is 'regular':
                impt_type = 'B'
            else:
                impt_type = 'I'
            rep = impt_type * self.bloom_length
            filepointer.write(pack(rep, *self._bloom))
            filepointer.write(pack('QQf', self.estimated_elements,
                                   self.elements_added,
                                   self.false_positive_rate))

    def export_size(self):
        ''' Calculate the size of the bloom on disk

            Returns:
                int: Size of the Bloom Filter when exported to disk
        '''
        if self.__blm_type == 'regular' or self.__blm_type is 'regular':
            impt_type = 'B'
        else:
            impt_type = 'I'
        tmp_b = calcsize(impt_type)
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
