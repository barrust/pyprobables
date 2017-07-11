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


class BloomFilter(object):
    ''' Simple Bloom Filter implementation for use in python;
    It can read and write the same format as the c version

    NOTE: Does *not* support the 'on disk' opperations!'''

    def __init__(self):
        ''' setup the basic values needed '''
        self._bloom = None
        self.__num_bits = 0  # number of bits
        self._est_elements = 0
        self._fpr = 0.0
        self.__number_hashes = 0
        self.__bloom_length = self.number_bits // 8
        self.__hash_func = self._default_hash
        self.__els_added = 0
        self._on_disk = False  # not on disk

    @property
    def bloom_array(self):
        ''' access to the bloom array itself '''
        return self._bloom

    @property
    def false_positive_rate(self):
        ''' desired max false positive rate '''
        return self._fpr

    @property
    def estimated_elements(self):
        ''' the number of elements estimated to be added when setup '''
        return self._est_elements

    @property
    def number_hashes(self):
        ''' the number of hashes for the bloom filter '''
        return self.__number_hashes

    @number_hashes.setter
    def number_hashes(self, value):
        self.__number_hashes = value

    @property
    def number_bits(self):
        ''' number of bits used '''
        return self.__num_bits

    @property
    def elements_added(self):
        ''' get the number of elements added '''
        return self.__els_added

    @elements_added.setter
    def elements_added(self, value):
        ''' set the number of elements added '''
        self.__els_added = value

    @property
    def is_on_disk(self):
        ''' get the number of elements added '''
        return self._on_disk

    @property
    def bloom_length(self):
        ''' get the length of the bloom filter in bytes '''
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

    def init(self, est_elements, false_positive_rate, hash_function=None):
        ''' initialize the bloom filter '''
        self._set_optimized_params(est_elements, false_positive_rate, 0,
                                   hash_function)
        self._bloom = [0] * self.bloom_length

    def clear(self):
        ''' clear the bloom filter '''
        self.elements_added = 0
        for idx in range(self.bloom_length):
            self.bloom_array[idx] = 0

    def hashes(self, key, depth=None):
        ''' calculate the hashes for the passed in key '''
        tmp = depth if depth is not None else self.number_hashes
        return self.__hash_func(key, tmp)

    def add(self, key):
        ''' add the key to the bloom filter '''
        hashes = self.hashes(key)
        self.add_alt(hashes)

    def add_alt(self, hashes):
        ''' add the element represented by hashes into the bloom filter '''
        for i in list(range(0, self.number_hashes)):
            k = int(hashes[i]) % self.number_bits
            idx = k // 8
            j = self.get_element(idx)
            tmp_bit = int(j) | int((1 << (k % 8)))
            self.bloom_array[idx] = self.get_set_element(tmp_bit)
        self.elements_added += 1

    def check(self, key):
        ''' check if the key is likely in the bloom filter '''
        hashes = self.hashes(key)
        return self.check_alt(hashes)

    def check_alt(self, hashes):
        ''' check if the element represented by hashes is in the bloom filter
        '''
        for i in list(range(0, self.number_hashes)):
            k = int(hashes[i]) % self.number_bits
            if (int(self.get_element(k // 8)) & int((1 << (k % 8)))) == 0:
                return False
        return True

    def intersection(self, second):
        ''' return a new Bloom Filter that contains the intersection of the
            two '''
        if self.__verify_bloom_similarity(second) is False:
            return None
        res = BloomFilter()
        res.init(self.estimated_elements, self.false_positive_rate,
                 self.__hash_func)

        for i in list(range(0, self.bloom_length)):
            res.bloom_array[i] = self.get_element(i) & second.get_element(i)
        res.elements_added = res.estimate_elements()
        return res

    def union(self, second):
        ''' return a new Bloom Filter that contains the union of the two '''
        if self.__verify_bloom_similarity(second) is False:
            return None
        res = BloomFilter()
        res.init(self.estimated_elements, self.false_positive_rate,
                 self.__hash_func)

        for i in list(range(0, self.bloom_length)):
            res.bloom_array[i] = self.get_element(i) | second.get_element(i)
        res.elements_added = res.estimate_elements()
        return res

    def jaccard_index(self, second):
        ''' calculate the jaccard similarity score '''
        if self.__verify_bloom_similarity(second) is False:
            return None
        count_union = 0
        count_int = 0
        for i in list(range(0, self.bloom_length)):
            t_union = self.get_element(i) | second.get_element(i)
            t_intersection = self.get_element(i) & second.get_element(i)
            count_union += self.__cnt_set_bits(t_union)
            count_int += self.__cnt_set_bits(t_intersection)
        if count_union == 0:
            return 1.0
        return count_int / count_union

    def export(self, filename):
        ''' export the bloom filter to disk '''
        with open(filename, 'wb') as filepointer:
            rep = 'B' * self.bloom_length
            filepointer.write(pack(rep, *self.bloom_array))
            filepointer.write(pack('QQf', self.estimated_elements,
                                   self.elements_added,
                                   self.false_positive_rate))

    def load(self, filename, hash_function=None):
        ''' load the bloom filter from file '''
        # read in the needed information, and then call _set_optimized_params
        # to set everything correctly
        with open(filename, 'rb') as filepointer:
            offset = calcsize('QQf')
            filepointer.seek(offset * -1, os.SEEK_END)
            mybytes = unpack('QQf', filepointer.read(offset))
            self._est_elements = mybytes[0]
            self.elements_added = mybytes[1]
            self._fpr = mybytes[2]

            self._set_optimized_params(self.estimated_elements,
                                       self.false_positive_rate,
                                       self.elements_added, hash_function)

            # now read in the bit array!
            filepointer.seek(0, os.SEEK_SET)
            offset = calcsize('B') * self.bloom_length
            rep = 'B' * self.bloom_length
            self._bloom = list(unpack(rep, filepointer.read(offset)))

    def export_hex(self):
        ''' export Bloom Filter to hex string '''
        mybytes = pack('>QQf', self.estimated_elements,
                       self.elements_added, self.false_positive_rate)
        bytes_string = hexlify(bytearray(self.bloom_array)) + hexlify(mybytes)
        if sys.version_info > (3, 0):  # python 3 gives us bytes
            return str(bytes_string, 'utf-8')
        return bytes_string

    def load_hex(self, hex_string, hash_function=None):
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
        ''' calculate the size of the bloom on disk '''
        tmp_b = calcsize('B')
        return (self.bloom_length * tmp_b) + calcsize('QQf')

    def estimate_elements(self):
        ''' estimate the number of elements added '''
        setbits = self.__cnt_number_bits_set()
        log_n = math.log(1 - (float(setbits) / float(self.number_bits)))
        tmp = float(self.number_bits) / float(self.number_hashes)
        return int(-1 * tmp * log_n)

    def current_false_positive_rate(self):
        ''' calculate the current false positive rate '''
        num = self.number_hashes * -1 * self.elements_added
        dbl = num / float(self.number_bits)
        exp = math.exp(dbl)
        return math.pow((1 - exp), self.number_hashes)

    def _set_optimized_params(self, estimated_elements, false_positive_rate,
                              elements_added, hash_function):
        ''' set the parameters to the optimal sizes '''
        if hash_function is None:
            self.__hash_func = self._default_hash
        else:
            self.__hash_func = hash_function
        self._est_elements = estimated_elements
        fpr = pack('f', float(false_positive_rate))
        self._fpr = unpack('f', fpr)[0]  # to mimic the c version!
        self.elements_added = elements_added
        # optimal caluclations
        n_els = self.estimated_elements
        fpr = float(self._fpr)
        m_bt = math.ceil((-n_els * math.log(fpr)) / 0.4804530139182)  # ln(2)^2
        self.number_hashes = int(round(math.log(2.0) * m_bt / n_els))
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

    def get_element(self, idx):
        ''' wrappper '''
        return self.bloom_array[idx]

    @staticmethod
    def __cnt_set_bits(i):
        ''' count number of bits set '''
        return bin(i).count("1")

    def __cnt_number_bits_set(self):
        ''' calculate the total number of set bits in the bloom '''
        setbits = 0
        for i in list(range(0, self.bloom_length)):
            setbits += self.__cnt_set_bits(self.get_element(i))
        return setbits

    def _default_hash(self, key, depth):
        ''' the default fnv-1a hashing routine '''
        res = list()
        tmp = key
        for _ in list(range(0, depth)):
            if tmp != key:
                tmp = self.__fnv_1a("{0:x}".format(tmp))
            else:
                tmp = self.__fnv_1a(key)
            res.append(tmp)
        return res

    @staticmethod
    def __fnv_1a(key):
        ''' 64 bit fnv-1a hash '''
        hval = 14695981039346656073
        fnv_64_prime = 1099511628211
        uint64_max = 2 ** 64
        for tmp_s in key:
            hval = hval ^ ord(tmp_s)
            hval = (hval * fnv_64_prime) % uint64_max
        return hval

    @staticmethod
    def get_set_element(tmp_bit):
        ''' wrappper to use similar functions always! '''
        return tmp_bit


class BloomFilterOnDisk(BloomFilter):
    ''' Bloom Filter on disk implementation '''
    def __init__(self):
        super(BloomFilterOnDisk, self).__init__()
        self.__file_pointer = None
        self.__filename = None
        self.__export_offset = calcsize('Qf')
        self._on_disk = True

    def __del__(self):
        ''' handle if user doesn't close the on disk bloom filter '''
        self.close()

    def init(self, filepath, est_elements, false_positive_rate,
             hash_function=None):
        ''' initialize the Bloom Filter on disk '''
        fpr = false_positive_rate
        super(BloomFilterOnDisk,
              self)._set_optimized_params(est_elements, fpr, 0, hash_function)
        # do the on disk things
        with open(filepath, 'wb') as filepointer:
            for _ in range(self.bloom_length):
                filepointer.write(pack('B', int(0)))
            filepointer.write(pack('QQf', est_elements, 0,
                                   false_positive_rate))
            filepointer.flush()
        self.load(filepath, hash_function)

    def close(self):
        ''' clean up the memory '''
        if self.__file_pointer is not None:
            self.__update()
            self._bloom.close()  # close the mmap
            self.__file_pointer.close()
            self.__file_pointer = None

    def load(self, filepath, hash_function=None):
        ''' load the bloom filter on disk '''
        # read the file, set the optimal params
        # mmap everything
        with open(filepath, 'r+b') as filepointer:
            offset = calcsize('QQf')
            filepointer.seek(offset * -1, os.SEEK_END)
            mybytes = unpack('QQf', filepointer.read(offset))
            self._est_elements = mybytes[0]
            self.elements_added = mybytes[1]
            self._fpr = mybytes[2]
            self._set_optimized_params(mybytes[0], mybytes[2], mybytes[1],
                                       hash_function)
        self.__file_pointer = open(filepath, 'r+b')
        self._bloom = mmap.mmap(self.__file_pointer.fileno(), 0)
        self._on_disk = True
        self.__filename = filepath

    def export(self, filename):
        ''' export to disk if a different location '''
        self.__update()
        if filename != self.__filename:
            # setup the new bloom filter
            copyfile(self.__filename, filename)
        # otherwise, nothing to do!

    def add_alt(self, hashes):
        ''' add the element represented by the hashes to the Bloom Filter
            on disk '''
        super(BloomFilterOnDisk, self).add_alt(hashes)
        self.__update()

    def union(self, second):
        ''' union using an on disk bloom filter '''
        res = super(BloomFilterOnDisk, self).union(second)
        self.__update()
        return res

    def intersection(self, second):
        ''' intersection using an on disk bloom filter '''
        res = super(BloomFilterOnDisk, self).intersection(second)
        self.__update()
        return res

    def export_hex(self):
        ''' export to a hex string '''
        msg = "Currently not supported by the on disk Bloom Filter!"
        raise NotImplementedError(msg)

    def load_hex(self, hex_string, hash_function=None):
        ''' load from hex ... '''
        msg = "Unable to load a hex string into an on disk Bloom Filter!"
        raise NotImplementedError(msg)

    def get_element(self, idx):
        ''' wrappper to use similar functions always! '''
        if sys.version_info > (3, 0):  # python 3 wants a byte
            return unpack('B', bytes([self.bloom_array[idx]]))[0]
        # python 2 wants a string
        return unpack('B', self.bloom_array[idx])[0]

    @staticmethod
    def get_set_element(tmp_bit):
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
