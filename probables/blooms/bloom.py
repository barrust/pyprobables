''' BloomFilter, python implementation
    License: MIT
    Author: Tyler Barrus (barrust@gmail.com)
    URL: https://github.com/barrust/bloom
'''
from __future__ import (unicode_literals, absolute_import, print_function,
                        division)
import sys
import os
import mmap
from struct import (pack, unpack, calcsize)
from shutil import (copyfile)
from . basebloom import (BaseBloom)
from .. exceptions import (InitializationError, NotSupportedError)
from .. utilities import (is_hex_string, is_valid_file)


class BloomFilter(BaseBloom):
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
        super(BloomFilter, self).__init__('regular', est_elements,
                                          false_positive_rate, filepath,
                                          hex_string, hash_function)

    def __str__(self):
        ''' correctly handle python 3 vs python2 encoding if necessary '''
        return self.__unicode__()

    def __unicode__(self):
        ''' string / unicode representation of the Bloom Filter '''
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
                            self.export_size(),
                            super(BloomFilter, self)._cnt_number_bits_set(),
                            on_disk)

    def intersection(self, second):
        ''' Return a new Bloom Filter that contains the intersection of the
            two

            Args:
                second (BloomFilter): The Bloom Filter with which to take \
                the intersection

            Returns:
                BloomFilter: The new Bloom Filter containing the intersection

            Note:
                `second` may be a BloomFilterOnDisk object
        '''
        super(BloomFilter, self)._verify_not_type_mismatch(second)

        if super(BloomFilter, self)._verify_bloom_similarity(second) is False:
            return None
        res = BloomFilter(self.estimated_elements, self.false_positive_rate,
                          hash_function=self.hash_function)

        for i in list(range(0, self.bloom_length)):
            res._bloom[i] = self._get_element(i) & second._get_element(i)
        res._els_added = res.estimate_elements()
        return res

    def union(self, second):
        ''' Return a new Bloom Filter that contains the union of the two

            Args:
                second (BloomFilter): The Bloom Filter with which to \
                calculate the union

            Returns:
                BloomFilter: The new Bloom Filter containing the union

            Note:
                `second` may be a BloomFilterOnDisk object
        '''
        super(BloomFilter, self)._verify_not_type_mismatch(second)

        if super(BloomFilter, self)._verify_bloom_similarity(second) is False:
            return None
        res = BloomFilter(self.estimated_elements, self.false_positive_rate,
                          hash_function=self.hash_function)

        for i in list(range(0, self.bloom_length)):
            res._bloom[i] = self._get_element(i) | second._get_element(i)
        res._els_added = res.estimate_elements()
        return res


class BloomFilterOnDisk(BaseBloom):
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
                  self).__init__('reg-ondisk', est_elements,
                                 false_positive_rate, hash_function)
        except InitializationError:
            pass

        self.__file_pointer = None
        self.__filename = None
        self.__export_offset = calcsize('Qf')
        self._on_disk = True

        if est_elements is not None and false_positive_rate is not None:
            # no need to check the file since this will over write it
            fpr = false_positive_rate
            vals = super(BloomFilterOnDisk,
                         self)._set_optimized_params(est_elements, fpr,
                                                     hash_function)
            super(BloomFilterOnDisk,
                  self).__init__('reg-ondisk', est_elements, vals[1],
                                 hash_function=vals[0])
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
            msg = ('Insufecient parameters to set up the On Disk Bloom Filter')
            raise InitializationError(msg)

    def __del__(self):
        ''' handle if user doesn't close the on disk Bloom Filter '''
        self.close()

    def close(self):
        ''' Clean up the BloomFilterOnDisk object '''
        if self.__file_pointer is not None:
            self.__update()
            self._bloom.close()  # close the mmap
            self.__file_pointer.close()
            self.__file_pointer = None

    def __load(self, filepath, hash_function=None):
        ''' load the Bloom Filter on disk '''
        # read the file, set the optimal params
        # mmap everything
        with open(filepath, 'r+b') as filepointer:
            offset = calcsize('QQf')
            filepointer.seek(offset * -1, os.SEEK_END)
            mybytes = unpack('QQf', filepointer.read(offset))
            vals = super(BloomFilterOnDisk,
                         self)._set_optimized_params(mybytes[0], mybytes[2],
                                                     hash_function)
        super(BloomFilterOnDisk,
              self).__init__('reg-ondisk', mybytes[0], vals[1],
                             hash_function=vals[0])
        self.__file_pointer = open(filepath, 'r+b')
        self._bloom = mmap.mmap(self.__file_pointer.fileno(), 0)
        self._on_disk = True
        self.__filename = filepath

    def export(self, filename):
        ''' Export to disk if a different location

            Args:
                filename (str): The filename to which the Bloom Filter will \
                be exported
            Note:
                Only exported if the filename is not the original filename
            Note:
                Override function '''
        self.__update()
        if filename != self.__filename:
            # setup the new bloom filter
            copyfile(self.__filename, filename)
        # otherwise, nothing to do!

    def add_alt(self, hashes):
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
                `second` may be a BloomFilterOnDisk object
            Note:
                Override function
        '''
        res = BloomFilter(self.estimated_elements, self.false_positive_rate,
                          hash_function=self.hash_function)
        for i in list(range(0, self.bloom_length)):
            res._bloom[i] = self._get_element(i) | second._get_element(i)
        res._els_added = res.estimate_elements()
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
                `second` may be a BloomFilterOnDisk object
            Note:
                Override function
        '''
        res = BloomFilter(self.estimated_elements, self.false_positive_rate,
                          hash_function=self.hash_function)
        for i in list(range(0, self.bloom_length)):
            res._bloom[i] = self._get_element(i) & second._get_element(i)
        res._els_added = res.estimate_elements()
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
        ''' update the on disk Bloom Filter and ensure everything is out
            to disk '''
        self._bloom.flush()
        self.__file_pointer.seek(-self.__export_offset, os.SEEK_END)
        self.__file_pointer.write(pack('Q', self.elements_added))
        self.__file_pointer.flush()
