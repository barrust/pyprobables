""" CountingBloomFilter, python implementation
    License: MIT
    Author: Tyler Barrus (barrust@gmail.com)
    URL: https://github.com/barrust/counting_bloom
"""
from array import array
from collections.abc import ByteString
from pathlib import Path
from struct import Struct
from typing import Union

from ..constants import UINT32_T_MAX, UINT64_T_MAX
from ..exceptions import InitializationError
from ..hashes import HashFuncT, HashResultsT, KeyT
from ..utilities import is_hex_string, is_valid_file
from .bloom import BloomFilter

MISMATCH_MSG = "The parameter second must be of type CountingBloomFilter"


def _verify_not_type_mismatch(second: "CountingBloomFilter") -> bool:
    """verify that there is not a type mismatch"""
    return isinstance(second, (CountingBloomFilter))


class CountingBloomFilter(BloomFilter):
    """ Simple Counting Bloom Filter implementation for use in python;
        It can read and write the same format as the c version
        (https://github.com/barrust/counting_bloom)

        Args:
            est_elements (int): The number of estimated elements to be added
            false_positive_rate (float): The desired false positive rate
            filepath (str): Path to file to load
            hex_string (str): Hex based representation to be loaded
            hash_function (function): Hashing strategy function to use \
            `hf(key, number)`
        Returns:
            CountingBloomFilter: A Counting Bloom Filter object

        Note:
            Initialization order of operations:
                1) From file
                2) From Hex String
                3) From params """

    __slots__ = BloomFilter.__slots__

    def __init__(
        self,
        est_elements: Union[int, None] = None,
        false_positive_rate: Union[float, None] = None,
        filepath: Union[str, Path, None] = None,
        hex_string: Union[str, None] = None,
        hash_function: Union[HashFuncT, None] = None,
    ) -> None:
        """setup the basic values needed"""
        self._bits_per_elm = 1.0
        self._on_disk = False
        self._type = "counting"
        self._typecode = "I"
        if is_valid_file(filepath):
            self._load(filepath, hash_function)
        elif is_hex_string(hex_string):
            self._load_hex(hex_string, hash_function)
        else:
            if est_elements is None or false_positive_rate is None:
                raise InitializationError("Insufecient parameters to set up the Counting Bloom Filter")
            # calc values
            fpr, n_hashes, n_bits = self._get_optimized_params(est_elements, false_positive_rate)
            self._set_values(est_elements, fpr, n_hashes, n_bits, hash_function)
            self._bloom_length = n_bits
            self._bloom = array(self._typecode, [0]) * self._bloom_length

    _IMPT_STRUCT = Struct("I")

    @classmethod
    def frombytes(cls, b: ByteString, hash_function: Union[HashFuncT, None] = None) -> "CountingBloomFilter":
        """
        Args:
            b (ByteString): the bytes to load as a Counting Bloom Filter
            hash_function (function): Hashing strategy function to use `hf(key, number)`
        Returns:
            CountingBloomFilter: A Counting Bloom Filter object
        """
        offset = cls._FOOTER_STRUCT.size
        est_els, els_added, fpr, n_hashes, n_bits = cls._parse_footer(cls._FOOTER_STRUCT, bytes(b[-offset:]))
        blm = CountingBloomFilter(est_elements=est_els, false_positive_rate=fpr, hash_function=hash_function)
        blm._set_values(est_els, fpr, n_hashes, n_bits, hash_function)
        blm._els_added = els_added
        blm._parse_bloom_array(b, cls._IMPT_STRUCT.size * blm.bloom_length)
        return blm

    def __str__(self) -> str:
        """string representation of the counting bloom filter"""
        on_disk = "no" if self.is_on_disk is False else "yes"

        cnt = sum([x for x in self._bloom if x > 0])
        total = sum(self._bloom)
        largest = max(self._bloom)
        largest_idx = (self._bloom).index(largest)
        fullness = cnt / self.number_bits
        els_added = total // self.number_hashes

        stats = (
            "CountingBloom:\n"
            "\tbits: {0}\n"
            "\testimated elements: {1}\n"
            "\tnumber hashes: {2}\n"
            "\tmax false positive rate: {3:.6f}\n"
            "\telements added: {4}\n"
            "\tcurrent false positive rate: {5:.6f}\n"
            "\tis on disk: {6}\n"
            "\tindex fullness: {7:.6}\n"
            "\tmax index usage: {8}\n"
            "\tmax index id: {9}\n"
            "\tcalculated elements: {10}\n"
        )
        return stats.format(
            self.number_bits,
            self.estimated_elements,
            self.number_hashes,
            self.false_positive_rate,
            self.elements_added,
            self.current_false_positive_rate(),
            on_disk,
            fullness,
            largest,
            largest_idx,
            els_added,
        )

    def add(self, key: KeyT, num_els: int = 1) -> int:  # type: ignore
        """Add the key to the Counting Bloom Filter

        Args:
            key (str): The element to be inserted
            num_els (int): Number of times to insert the element
        Returns:
            int: Maximum number of insertions"""
        hashes = self.hashes(key)
        return self.add_alt(hashes, num_els)

    def add_alt(self, hashes: HashResultsT, num_els: int = 1) -> int:  # type: ignore
        """ Add the element represented by hashes into the Counting Bloom
            Filter

            Args:
                hashes (list): A list of integers representing the key to \
                insert
                num_els (int): Number of times to insert the element
            Returns:
                int: Maximum number of insertions """
        res = UINT32_T_MAX
        for i in list(range(0, self.number_hashes)):
            k = hashes[i] % self.number_bits
            j = self._bloom[k]
            tmp = j + num_els
            if tmp <= UINT32_T_MAX:
                self._bloom[k] = j + num_els
            else:
                self._bloom[k] = UINT32_T_MAX
            if self._bloom[k] < res:
                res = self._bloom[k]
        self.elements_added += num_els
        if self.elements_added > UINT64_T_MAX:
            self.elements_added = UINT64_T_MAX
        return res

    def check(self, key: KeyT) -> int:  # type: ignore
        """Check if the key is likely in the Counting Bloom Filter

        Args:
            key (str): The element to be checked
        Returns:
            int: Maximum number of insertions"""
        return self.check_alt(self.hashes(key))

    def check_alt(self, hashes: HashResultsT) -> int:  # type: ignore
        """ Check if the element represented by hashes is in the Counting
            Bloom Filter

            Args:
                hashes (list): A list of integers representing the key to \
                check
            Returns:
                int: Maximum number of insertions """
        return min([self._bloom[x % self.number_bits] for x in hashes])

    def remove(self, key: KeyT, num_els: int = 1) -> int:
        """Remove the element from the counting bloom

        Args:
            key (str): The element to be removed
            num_els (int): Number of times to remove the element
        Returns:
            int: Maximum number of insertions after the removal"""
        return self.remove_alt(self.hashes(key), num_els)

    def remove_alt(self, hashes: HashResultsT, num_els: int = 1) -> int:
        """ Remvoe the element represented by hashes from the Counting Bloom \
            Filter

            Args:
                hashes (list): A list of integers representing the key to \
                remove
                num_els (int): Number of times to remove the element
            Returns:
                int: Maximum number of insertions after the removal """
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
            self._bloom[k] -= t_num_els
        self.elements_added -= t_num_els
        return tmp - t_num_els

    def intersection(self, second: "CountingBloomFilter") -> "CountingBloomFilter":
        """ Take the intersection of two Counting Bloom Filters

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
                estimate_elements()
            Note:
                If `second` is not of the same size (false_positive_rate and \
                est_elements) then this will return `None` """
        if not _verify_not_type_mismatch(second):
            raise TypeError(MISMATCH_MSG)

        if self._verify_bloom_similarity(second) is False:
            return None
        res = CountingBloomFilter(
            est_elements=self.estimated_elements,
            false_positive_rate=self.false_positive_rate,
            hash_function=self.hash_function,
        )

        for i in list(range(self.bloom_length)):
            if self._bloom[i] > 0 and second._bloom[i] > 0:
                tmp = self._bloom[i] + second._bloom[i]
                res.bloom[i] = tmp
        res.elements_added = res.estimate_elements()
        return res

    def jaccard_index(self, second: "CountingBloomFilter") -> Union[float, None]:  # type:ignore
        """ Take the Jaccard Index of two Counting Bloom Filters

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
                added and not the number of each element added
            Note:
                If `second` is not of the same size (false_positive_rate and \
                est_elements) then this will return `None` """
        if not _verify_not_type_mismatch(second):
            raise TypeError(MISMATCH_MSG)

        if self._verify_bloom_similarity(second) is False:
            return None

        count_union = 0
        count_inter = 0
        for i in list(range(self.bloom_length)):
            if self._bloom[i] > 0 or second._bloom[i] > 0:
                count_union += 1
            if self._bloom[i] > 0 and second._bloom[i] > 0:
                count_inter += 1
        if count_union == 0:
            return 1.0
        return count_inter / count_union

    def union(self, second: "CountingBloomFilter") -> Union["CountingBloomFilter", None]:  # type:ignore
        """ Return a new Countiong Bloom Filter that contains the union of
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
                estimate_elements()
            Note:
                If `second` is not of the same size (false_positive_rate and \
                est_elements) then this will return `None` """
        if not _verify_not_type_mismatch(second):
            raise TypeError(MISMATCH_MSG)

        if self._verify_bloom_similarity(second) is False:
            return None
        res = CountingBloomFilter(
            est_elements=self.estimated_elements,
            false_positive_rate=self.false_positive_rate,
            hash_function=self.hash_function,
        )
        for i in list(range(self.bloom_length)):
            tmp = self._bloom[i] + second._bloom[i]
            res._bloom[i] = tmp
        res.elements_added = res.estimate_elements()
        return res

    def _cnt_number_bits_set(self) -> int:
        """calculate the total number of set bits in the bloom"""
        return sum([1 for x in self._bloom if x > 0])
