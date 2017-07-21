''' BloomFilter, python implementation
    License: MIT
    Author: Tyler Barrus (barrust@gmail.com)
    URL: https://github.com/barrust/bloom
'''
from __future__ import (unicode_literals, absolute_import, print_function,
                        division)
import sys
import math
import os
import mmap
from struct import (pack, unpack, calcsize, Struct)
from shutil import (copyfile)
from binascii import (hexlify, unhexlify)
from .. exceptions import (InitializationError, NotSupportedError)
from .. hashes import (default_fnv_1a)
from .. utilities import (is_hex_string, is_valid_file)


class BloomFilter(object):
    ''' Simple Bloom Filter implementation for use in python;
        It can read and write the same format as the c version
        (https://github.com/barrust/bloom)

        Args:
            est_elements (int): The number of estimated elements to be added
            false_positive_rate (float): The desired false positive rate
            filepath (string): Path to file to load
            hex_string (string): Hex based representation to be loaded
            hash_function (function): Hashing strategy function to use \
            `hf(key, number)`
        Returns:
            BloomFilter: A Bloom Filter object

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
        self.__bloom_length = self.number_bits // 8
        self.__hash_func = default_fnv_1a
        self.__els_added = 0
        self._on_disk = False  # not on disk

        if is_valid_file(filepath):
            self.__load(filepath, hash_function)
        elif is_hex_string(hex_string):
            self._load_hex(hex_string, hash_function)
        elif est_elements is not None and false_positive_rate is not None:
            self._set_optimized_params(est_elements, false_positive_rate, 0,
                                       hash_function)
            self._bloom = [0] * self.bloom_length
        else:
            msg = ('Insufecient parameters to set up the Bloom Filter')
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
        ''' int: The number of hashes required for the Bloom Filterr hashing
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
        return self.__els_added

    @property
    def is_on_disk(self):
        ''' bool: Is the Bloom Filter on Disk or not

        Note:
            Not settable '''
        return self._on_disk

    @property
    def bloom_length(self):
        ''' int: Length of the bloom filter array

        Note:
            Not settable '''
        return self.__bloom_length

    def __str__(self):
        ''' correctly handle python 3 vs python2 encoding if necessary '''
        return self.__unicode__()

    def __unicode__(self):
        ''' string / unicode representation of the bloom filter '''
        on_disk = "no" if self.is_on_disk is False else "yes"
        stats = ('BloomFilter:\n'
                 '\tbits: {0}\n'
                 '\testimated elements: {1}\n'
                 '\tnumber hashes: {2}\n'
                 '\tmax false positive rate: {3:.6f}\n'
                 '\tbloom length (8 bits): {4}\n'
                 '\telements added: {5}\n'
                 '\testimated elements added: {6}\n'
                 '\tcurrent false positive rate: {7:.6f}\n'
                 '\texport size (bytes): {8}\n'
                 '\tnumber bits set: {9}\n'
                 '\tis on disk: {10}\n')
        return stats.format(self.number_bits, self.estimated_elements,
                            self.number_hashes, self.false_positive_rate,
                            self.bloom_length, self.elements_added,
                            self.estimate_elements(),
                            self.current_false_positive_rate(),
                            self.export_size(), self.__cnt_number_bits_set(),
                            on_disk)

    def __contains__(self, key):
        ''' setup the `in` keyword '''
        return self.check(key)

    def clear(self):
        ''' Clear or reset the Bloom Filter '''
        self.__els_added = 0
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

    def add(self, key):
        ''' Add the key to the Bloom Filter

            Args:
                key (str): the element to be inserted
        '''
        hashes = self.hashes(key)
        self.add_alt(hashes)

    def add_alt(self, hashes):
        ''' Add the element represented by hashes into the Bloom Filter

            Args:
                hashes (list): a list of integers representing the key to \
                insert
        '''
        for i in list(range(0, self.number_hashes)):
            k = int(hashes[i]) % self.number_bits
            idx = k // 8
            j = self._get_element(idx)
            tmp_bit = int(j) | int((1 << (k % 8)))
            self._bloom[idx] = self._get_set_element(tmp_bit)
        self.__els_added += 1

    def check(self, key):
        ''' Check if the key is likely in the Bloom Filter

            Args:
                key (str): the element to be checked

            Returns:
                bool: True if likely encountered, False if definately not
        '''
        hashes = self.hashes(key)
        return self.check_alt(hashes)

    def check_alt(self, hashes):
        ''' Check if the element represented by hashes is in the Bloom Filter

            Args:
                hashes (list): a list of integers representing the key to \
                check

            Returns:
                bool: True if likely encountered, False if definately not
        '''
        for i in list(range(0, self.number_hashes)):
            k = int(hashes[i]) % self.number_bits
            if (int(self._get_element(k // 8)) & int((1 << (k % 8)))) == 0:
                return False
        return True

    def intersection(self, second):
        ''' Return a new Bloom Filter that contains the intersection of the
            two

            Args:
                second (BloomFilter): The Bloom Filter with which to take \
                the intersection

            Returns:
                BloomFilter: The new Bloom Filter containing the intersection

            Note:
                second may be a BloomFilterOnDisk object
        '''
        if self.__verify_bloom_similarity(second) is False:
            return None
        res = BloomFilter(self.estimated_elements, self.false_positive_rate,
                          hash_function=self.__hash_func)

        for i in list(range(0, self.bloom_length)):
            res._bloom[i] = self._get_element(i) & second._get_element(i)
        res.__els_added = res.estimate_elements()
        return res

    def union(self, second):
        ''' Return a new Bloom Filter that contains the union of the two

            Args:
                second (BloomFilter): The Bloom Filter with which to \
                calculate the union

            Returns:
                BloomFilter: The new Bloom Filter containing the union

            Note:
                second may be a BloomFilterOnDisk object
        '''
        if self.__verify_bloom_similarity(second) is False:
            return None
        res = BloomFilter(self.estimated_elements, self.false_positive_rate,
                          hash_function=self.__hash_func)

        for i in list(range(0, self.bloom_length)):
            res._bloom[i] = self._get_element(i) | second._get_element(i)
        res.__els_added = res.estimate_elements()
        return res

    def jaccard_index(self, second):
        ''' Calculate the jaccard similarity score between two Bloom Filters

            Args:
                second (BloomFilter): the Bloom Filter to compare with

            Note:
                second may be a BloomFilterOnDisk object
        '''
        if self.__verify_bloom_similarity(second) is False:
            return None
        count_union = 0
        count_int = 0
        for i in list(range(0, self.bloom_length)):
            t_union = self._get_element(i) | second._get_element(i)
            t_intersection = self._get_element(i) & second._get_element(i)
            count_union += self.__cnt_set_bits(t_union)
            count_int += self.__cnt_set_bits(t_intersection)
        if count_union == 0:
            return 1.0
        return count_int / count_union

    def export(self, filename):
        ''' Export the Bloom Filter to disk

            Args:
                filename (str): The filename to which the Bloom Filter will \
                be written.
        '''
        with open(filename, 'wb') as filepointer:
            rep = 'B' * self.bloom_length
            filepointer.write(pack(rep, *self._bloom))
            filepointer.write(pack('QQf', self.estimated_elements,
                                   self.elements_added,
                                   self.false_positive_rate))

    def __load(self, filename, hash_function=None):
        ''' load the Bloom Filter from file '''
        # read in the needed information, and then call _set_optimized_params
        # to set everything correctly
        with open(filename, 'rb') as filepointer:
            offset = calcsize('QQf')
            filepointer.seek(offset * -1, os.SEEK_END)
            mybytes = unpack('QQf', filepointer.read(offset))
            self.__est_elements = mybytes[0]
            self.__els_added = mybytes[1]
            self.__fpr = mybytes[2]

            self._set_optimized_params(self.estimated_elements,
                                       self.false_positive_rate,
                                       self.elements_added, hash_function)

            # now read in the bit array!
            filepointer.seek(0, os.SEEK_SET)
            offset = calcsize('B') * self.bloom_length
            rep = 'B' * self.bloom_length
            self._bloom = list(unpack(rep, filepointer.read(offset)))

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
        ''' Calculate the size of the bloom on disk

            Returns: int: size of the Bloom Filter when exported to disk
        '''
        tmp_b = calcsize('B')
        return (self.bloom_length * tmp_b) + calcsize('QQf')

    def estimate_elements(self):
        ''' Estimate the number of elements added

            Returns:
                int: Number of elements estimated to be inserted
        '''
        setbits = self.__cnt_number_bits_set()
        log_n = math.log(1 - (float(setbits) / float(self.number_bits)))
        tmp = float(self.number_bits) / float(self.number_hashes)
        return int(-1 * tmp * log_n)

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
        self.__els_added = elements_added
        # optimal caluclations
        n_els = self.estimated_elements
        fpr = float(self.__fpr)
        m_bt = math.ceil((-n_els * math.log(fpr)) / 0.4804530139182)  # ln(2)^2
        self.__number_hashes = int(round(math.log(2.0) * m_bt / n_els))
        self.__num_bits = int(m_bt)
        self.__bloom_length = int(math.ceil(m_bt / (8 * 1.0)))

    def __verify_bloom_similarity(self, second):
        ''' can the blooms be used in intersection, union, or jaccard index '''
        hash_match = self.number_hashes != second.number_hashes
        same_bits = self.number_bits != second.number_bits
        next_hash = self.hashes("test") != second.hashes("test")
        if hash_match or same_bits or next_hash:
            return False
        return True

    def _get_element(self, idx):
        ''' wrappper for getting an element from the bloom filter! '''
        return self._bloom[idx]

    @staticmethod
    def __cnt_set_bits(i):
        ''' count number of bits set in this int '''
        return bin(i).count("1")

    def __cnt_number_bits_set(self):
        ''' calculate the total number of set bits in the bloom '''
        setbits = 0
        for i in list(range(0, self.bloom_length)):
            setbits += self.__cnt_set_bits(self._get_element(i))
        return setbits

    @staticmethod
    def _get_set_element(tmp_bit):
        ''' wrappper to use similar functions always! '''
        return tmp_bit


class BloomFilterOnDisk(BloomFilter):
    ''' Simple Bloom Filter implementation directly on disk for use in python;
        It can read and write the same format as the c version
        (https://github.com/barrust/bloom)

        Args:
            filepath (string): Path to file to load
            est_elements (int): The number of estimated elements to be added
            false_positive_rate (float): The desired false positive rate
            hex_string (string): Hex based representation to be loaded
            hash_function (function): Hashing strategy function to use \
            `hf(key, number)`
        Returns:
            BloomFilterOnDisk: A Bloom Filter object
        Raises:
            NotSupportedError: Loading using a hex string is not supported

        Note:
            Initialization order of operations:
                1) Esimated elements and false positive rate
                2) From Hex String
                3) Only filepath provided '''

    def __init__(self, filepath, est_elements=None, false_positive_rate=None,
                 hex_string=None, hash_function=None):
        # since we cannot load from a file only (to memory), we can't pass
        # the file to the constructor; therefore, we will have to catch
        # any exception thrown
        try:
            super(BloomFilterOnDisk,
                  self).__init__(est_elements, false_positive_rate,
                                 hash_function)
        except InitializationError:
            pass

        self.__file_pointer = None
        self.__filename = None
        self.__export_offset = calcsize('Qf')
        self._on_disk = True

        if est_elements is not None and false_positive_rate is not None:
            # no need to check the file since this will over write it
            fpr = false_positive_rate
            super(BloomFilterOnDisk,
                  self)._set_optimized_params(est_elements, fpr, 0,
                                              hash_function)
            # do the on disk things
            with open(filepath, 'wb') as filepointer:
                for _ in range(self.bloom_length):
                    filepointer.write(pack('B', int(0)))
                filepointer.write(pack('QQf', est_elements, 0,
                                       false_positive_rate))
                filepointer.flush()
            self.__load(filepath, hash_function)
        elif hex_string is not None and is_hex_string(hex_string):
            self._load_hex(hex_string, hash_function)
        elif is_valid_file(filepath):
            self.__load(filepath, hash_function)
        else:
            msg = ('Insufecient parameters to set up the Bloom Filter')
            raise InitializationError(msg)

    def __del__(self):
        ''' handle if user doesn't close the on disk bloom filter '''
        self.close()

    def close(self):
        ''' Clean up the BloomFilterOnDisk object '''
        if self.__file_pointer is not None:
            self.__update()
            self._bloom.close()  # close the mmap
            self.__file_pointer.close()
            self.__file_pointer = None

    def __load(self, filepath, hash_function=None):
        ''' load the bloom filter on disk '''
        # read the file, set the optimal params
        # mmap everything
        with open(filepath, 'r+b') as filepointer:
            offset = calcsize('QQf')
            filepointer.seek(offset * -1, os.SEEK_END)
            mybytes = unpack('QQf', filepointer.read(offset))
            self.__est_elements = mybytes[0]
            self.__els_added = mybytes[1]
            self.__fpr = mybytes[2]
            self._set_optimized_params(mybytes[0], mybytes[2], mybytes[1],
                                       hash_function)
        self.__file_pointer = open(filepath, 'r+b')
        self._bloom = mmap.mmap(self.__file_pointer.fileno(), 0)
        self._on_disk = True
        self.__filename = filepath

    def export(self, filename):
        ''' Export to disk if a different location

            Args:
                filename (str): the filename to which the Bloom Filter will \
                be exported

            Note:
                Only exported if the filename is not the original filename

            Note:
                Override function
        '''
        self.__update()
        if filename != self.__filename:
            # setup the new bloom filter
            copyfile(self.__filename, filename)
        # otherwise, nothing to do!

    def add_alt(self, hashes):
        ''' Add the element represented by hashes into the Bloom Filter

            Args:
                hashes (list): a list of integers representing the key to \
                insert

            Note:
                Override function
        '''
        super(BloomFilterOnDisk, self).add_alt(hashes)
        self.__update()

    def union(self, second):
        ''' Return a new Bloom Filter that contains the union of the two

            Args:
                second (BloomFilter): The Bloom Filter with which to \
                calculate the union

            Returns:
                BloomFilter: The new Bloom Filter containing the union

            Note:
                second may be a BloomFilterOnDisk object

            Note:
                Override function
        '''
        res = super(BloomFilterOnDisk, self).union(second)
        self.__update()
        return res

    def intersection(self, second):
        ''' Return a new Bloom Filter that contains the intersection of the
            two

            Args:
                second (BloomFilter): The Bloom Filter with which to take \
                the intersection

            Returns:
                BloomFilter: The new Bloom Filter containing the intersection

            Note:
                second may be a BloomFilterOnDisk object

            Note:
                Override function
        '''
        res = super(BloomFilterOnDisk, self).intersection(second)
        self.__update()
        return res

    def export_hex(self):
        ''' Export to a hex string

            Raises:
                NotSupportedError: This functionality is currently not \
                supported
        '''
        msg = ('`export_hex` is currently not supported by the on disk '
               'Bloom Filter')
        raise NotSupportedError(msg)

    def _load_hex(self, hex_string, hash_function=None):
        ''' load from hex ... '''
        msg = ('Loading from hex_string is currently not supported by the '
               'on disk Bloom Filter')
        raise NotSupportedError(msg)

    def _get_element(self, idx):
        ''' wrappper to use similar functions always! '''
        if sys.version_info > (3, 0):  # python 3 wants a byte
            return unpack('B', bytes([self._bloom[idx]]))[0]
        # python 2 wants a string
        return unpack('B', self._bloom[idx])[0]

    @staticmethod
    def _get_set_element(tmp_bit):
        ''' wrappper to use similar functions always! '''
        if sys.version_info > (3, 0):  # python 3 wants a byte
            return tmp_bit
        return pack('B', tmp_bit)

    def __update(self):
        ''' update the on disk bloom filter and ensure everything is out
            to disk '''
        self._bloom.flush()
        self.__file_pointer.seek(-self.__export_offset, os.SEEK_END)
        self.__file_pointer.write(pack('Q', self.elements_added))
        self.__file_pointer.flush()
