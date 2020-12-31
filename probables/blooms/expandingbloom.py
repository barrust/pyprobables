""" BloomFilter, python implementation
    License: MIT
    Author: Tyler Barrus (barrust@gmail.com)
    URL: https://github.com/barrust/pyprobables
"""

import os
from struct import calcsize, pack, unpack

from ..exceptions import RotatingBloomFilterError
from ..utilities import is_valid_file
from .bloom import BloomFilter


class ExpandingBloomFilter(object):
    """ Simple expanding Bloom Filter implementation for use in python; the
        Bloom Fiter will automatically expand, or grow, if the false
        positive rate is about to become greater than the desired false
        positive rate.

        Args:
            est_elements (int): The number of estimated elements to be added
            false_positive_rate (float): The desired false positive rate
            filepath (str): Path to file to load
            hash_function (function): Hashing strategy function to use \
            `hf(key, number)`
        Returns:
            ExpandingBloomFilter: An expanding Bloom Filter object
        Note:
            Initialization order of operations:
                1) Filepath
                2) est_elements and false_positive_rate"""

    __slots__ = [
        "_blooms",
        "__fpr",
        "__est_elements",
        "__hash_func",
        "__added_elements",
    ]

    def __init__(
        self,
        est_elements=None,
        false_positive_rate=None,
        filepath=None,
        hash_function=None,
    ):
        """ initialize """
        self._blooms = list()
        self.__fpr = false_positive_rate
        self.__est_elements = est_elements
        self.__hash_func = hash_function
        self.__added_elements = 0  # total added...

        if is_valid_file(filepath):
            self.__load(filepath)
        else:
            # add in the initial bloom filter!
            self.__add_bloom_filter()

    def __contains__(self, key):
        """ setup the `in` functionality """
        return self.check(key)

    @property
    def expansions(self):
        """ int: The number of expansions """
        return len(self._blooms) - 1

    @property
    def false_positive_rate(self):
        """ float: The desired false positive rate of the expanding Bloom \
                   Filter """
        return self.__fpr

    @property
    def estimated_elements(self):
        """int: The original number of elements estimated to be in the Bloom \
                Filter """
        return self.__est_elements

    @property
    def elements_added(self):
        """ int: The total number of elements added """
        return self.__added_elements

    def push(self):
        """ Push a new expansion onto the Bloom Filter """
        self.__add_bloom_filter()

    def check(self, key):
        """ Check to see if the key is in the Bloom Filter

            Args:
                key (str): The key to check for in the Bloom Filter
            Returns:
                bool: `True` if the element is likely present; `False` if \
                      definately not present """
        hashes = self._blooms[0].hashes(key)
        return self.check_alt(hashes)

    def check_alt(self, hashes):
        """ Check to see if the hashes are in the Bloom Filter

            Args:
                hashes (list): The hash representation to check for in the \
                               Bloom Filter
            Returns:
                bool: `True` if the element is likely present; `False` if \
                      definately not present """
        for blm in self._blooms:
            if blm.check_alt(hashes):
                return True
        return False

    def add(self, key, force=False):
        """ Add the key to the Bloom Filter

            Args:
                key (str): The element to be inserted
                force (bool): `True` will force it to be inserted, even if it \
                              likely has been inserted before `False` will \
                              only insert if not found in the Bloom Filter """
        hashes = self._blooms[0].hashes(key)
        self.add_alt(hashes, force)

    def add_alt(self, hashes, force=False):
        """ Add the element represented by hashes into the Bloom Filter

            Args:
                hashes (list): A list of integers representing the key to insert
                force (bool): `True` will force it to be inserted, even if \
                              it likely has been inserted before \
                              `False` will only insert if not found in the \
                              Bloom Filter """
        self.__added_elements += 1
        if force or not self.check_alt(hashes):
            self.__check_for_growth()
            self._blooms[-1].add_alt(hashes)

    def __add_bloom_filter(self):
        """ build a new bloom and add it on! """
        blm = BloomFilter(
            est_elements=self.__est_elements,
            false_positive_rate=self.__fpr,
            hash_function=self.__hash_func,
        )
        self._blooms.append(blm)

    def __check_for_growth(self):
        """ detereming if the bloom filter should automatically grow """
        if self._blooms[-1].elements_added >= self.__est_elements:
            self.__add_bloom_filter()

    def export(self, filepath):
        """Export an expanding Bloom Filter, or subclass, to disk

        Args:
            filepath (str): The path to the file to import"""
        with open(filepath, "wb") as fileobj:
            # add all the different Bloom bit arrays...
            for blm in self._blooms:
                rep = "Q" + "B" * blm.bloom_length
                fileobj.write(pack(rep, blm.elements_added, *blm.bloom))
            fileobj.write(
                pack(
                    "QQQf",
                    len(self._blooms),
                    self.estimated_elements,
                    self.elements_added,
                    self.false_positive_rate,
                )
            )

    def __load(self, filename):
        """ load a file """
        with open(filename, "rb") as fileobj:
            offset = calcsize("QQQf")
            fileobj.seek(offset * -1, os.SEEK_END)
            size, est_els, els_added, fpr = unpack("QQQf", fileobj.read(offset))

            fileobj.seek(0, os.SEEK_SET)
            # set the basic defaults
            self._blooms = list()
            self.__added_elements = els_added
            self.__fpr = fpr
            self.__est_elements = est_els
            for _ in range(size):
                blm = BloomFilter(
                    est_elements=self.__est_elements,
                    false_positive_rate=self.__fpr,
                    hash_function=self.__hash_func,
                )
                # now we need to read in the correct number of bytes...
                offset = calcsize("Q") + calcsize("B") * blm.bloom_length
                rep = "Q" + "B" * blm.bloom_length
                unpacked = list(unpack(rep, fileobj.read(offset)))
                blm._bloom = unpacked[1:]
                blm.elements_added = unpacked[0]
                self._blooms.append(blm)


class RotatingBloomFilter(ExpandingBloomFilter):
    """ Simple Rotating Bloom Filter implementation that allows for the "older"
        elements added to be removed, in chunks. As the queue fills up, those
        elements inserted earlier will be bulk removed. This also provides the
        user with the oportunity to force the removal instead of it being time
        based.

        Args:
            est_elements (int): The number of estimated elements to be added
            false_positive_rate (float): The desired false positive rate
            max_queue_size (int): This is the number is used to determine the \
            maximum number of Bloom Filters. Total elements added is based on \
            `max_queue_size * est_elements`
            filepath (str): Path to file to load
            hash_function (function): Hashing strategy function to use \
            `hf(key, number)`
        Note:
            Initialization order of operations:
                1) Filepath
                2) est_elements and false_positive_rate
    """

    __slots__ = [
        "_blooms",
        "__fpr",
        "__est_elements",
        "__hash_func",
        "__added_elements",
        "_queue_size",
    ]

    def __init__(
        self,
        est_elements=None,
        false_positive_rate=None,
        max_queue_size=10,
        filepath=None,
        hash_function=None,
    ):
        """ initialize """
        super(RotatingBloomFilter, self).__init__(
            est_elements=est_elements,
            false_positive_rate=false_positive_rate,
            filepath=filepath,
            hash_function=hash_function,
        )
        self._queue_size = max_queue_size
        self.__added_elements = self.elements_added
        self.__est_elements = self.estimated_elements
        self.__fpr = self.false_positive_rate
        self.__hash_func = hash_function

    @property
    def max_queue_size(self):
        """ int: The maximum size for the queue """
        return self._queue_size

    @property
    def current_queue_size(self):
        """ int: The current size of the queue """
        return len(self._blooms)

    def add_alt(self, hashes, force=False):
        """ Add the element represented by hashes into the Bloom Filter

            Args:
                hashes (list): A list of integers representing the key to insert
                force (bool): `True` will force it to be inserted, even if \
                              it likely has been inserted before \
                              `False` will only insert if not found in the \
                              Bloom Filter """
        self.__added_elements += 1
        if force or not self.check_alt(hashes):
            self.__rotate_bloom_filter()
            self._blooms[-1].add_alt(hashes)

    def pop(self):
        """Pop the oldest Bloom Filter off of the queue without pushing a new
        Bloom Filter onto the queue

        Raises:
            RotatingBloomFilterError: Unable to rotate the Bloom Filter"""
        if self.current_queue_size == 1:
            msg = "Popping a Bloom Filter will result in an unusable system!"
            raise RotatingBloomFilterError(msg)
        self._blooms.pop(0)

    def push(self):
        """ Push a new bloom filter onto the queue and rotate if necessary """
        self.__rotate_bloom_filter(force=True)

    def __rotate_bloom_filter(self, force=False):
        """handle determining if/when the Bloom Filter queue needs to be
        rotated"""
        blm = self._blooms[-1]
        ready_to_rotate = blm.elements_added == blm.estimated_elements
        no_need_to_pop = self.current_queue_size < self._queue_size
        if force and no_need_to_pop:
            self.__add_bloom_filter()
        elif force:  # must need to be pop'd first!
            blm = self._blooms.pop(0)
            self.__add_bloom_filter()
        elif ready_to_rotate and no_need_to_pop:
            self.__add_bloom_filter()
        elif ready_to_rotate:
            blm = self._blooms.pop(0)
            self.__add_bloom_filter()

    def __add_bloom_filter(self):
        """ build a new bloom and add it on! """
        blm = BloomFilter(
            est_elements=self.__est_elements,
            false_positive_rate=self.__fpr,
            hash_function=self.__hash_func,
        )
        self._blooms.append(blm)
