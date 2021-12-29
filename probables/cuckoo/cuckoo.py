""" Cuckoo Filter, python implementation
    License: MIT
    Author: Tyler Barrus (barrust@gmail.com)
"""

import array
import os
import random
import typing
from collections.abc import ByteString
from io import BytesIO, IOBase
from mmap import mmap
from numbers import Number
from pathlib import Path
from struct import Struct, calcsize, pack

from ..exceptions import CuckooFilterFullError, InitializationError
from ..hashes import KeyT, SimpleHashT, fnv_1a
from ..utilities import MMap, convert_to_typed, get_x_bits, is_valid_file


class CuckooFilter(object):
    """ Simple Cuckoo Filter implementation

        Args:
            capacity (int): The number of bins
            bucket_size (int): The number of buckets per bin
            max_swaps (int): The number of cuckoo swaps before stopping
            expansion_rate (int): The rate at which to expand
            auto_expand (bool): If the filter should automatically expand
            finger_size (int): The size of the fingerprint to use in bytes \
            (between 1 and 4); exported as 4 bytes; up to the user to reset \
            the size correctly on import
            filename (str): The path to the file to load or None if no file
            hash_function (function): Hashing strategy function to use \
            `hf(key)`
        Returns:
            CuckooFilter: A Cuckoo Filter object """

    __slots__ = [
        "_bucket_size",
        "_cuckoo_capacity",
        "__max_cuckoo_swaps",
        "__expansion_rate",
        "__auto_expand",
        "__fingerprint_size",
        "__hash_func",
        "_inserted_elements",
        "_buckets",
    ]

    def __init__(
        self,
        capacity: int = 10000,
        bucket_size: int = 4,
        max_swaps: int = 500,
        expansion_rate: int = 2,
        auto_expand: bool = True,
        finger_size: int = 4,
        filepath: typing.Optional[str] = None,
        hash_function: typing.Optional[SimpleHashT] = None,  # this is incorrect
    ):
        """setup the data structure"""
        valid_prms = (
            isinstance(capacity, Number)
            and capacity >= 1
            and isinstance(bucket_size, Number)
            and bucket_size >= 1
            and isinstance(max_swaps, Number)
            and max_swaps >= 1
        )
        if not valid_prms:
            msg = "CuckooFilter: capacity, bucket_size, and max_swaps must be an integer greater than 0"
            raise InitializationError(msg)
        self._bucket_size = int(bucket_size)
        self._cuckoo_capacity = int(capacity)
        self.__max_cuckoo_swaps = int(max_swaps)
        self.__expansion_rate = None
        self.expansion_rate = expansion_rate
        self.__auto_expand = True
        self.auto_expand = auto_expand
        self.__fingerprint_size = None
        self.fingerprint_size = finger_size

        if hash_function is None:
            self.__hash_func = fnv_1a
        else:
            self.__hash_func = hash_function  # type: ignore
        self._inserted_elements = 0
        if filepath is None:
            self._buckets = list()  # type: ignore
            for _ in range(self.capacity):
                self.buckets.append(list())
        elif is_valid_file(filepath):
            self._load(filepath)
        else:
            msg = "CuckooFilter: failed to load provided file"
            raise InitializationError(msg)

    def __contains__(self, key: KeyT) -> bool:
        """setup the `in` keyword"""
        return self.check(key)

    def __str__(self):
        """setup what it will print"""
        msg = (
            "{0}:\n"
            "\tCapacity: {1}\n"
            "\tTotal Bins: {2}\n"
            "\tLoad Factor: {3}%\n"
            "\tInserted Elements: {4}\n"
            "\tMax Swaps: {5}\n"
            "\tExpansion Rate: {6}\n"
            "\tAuto Expand: {7}"
        )
        return msg.format(
            self.__class__.__name__,
            self.capacity,
            self.capacity * self.bucket_size,
            self.load_factor() * 100,
            self.elements_added,
            self.max_swaps,
            self.expansion_rate,
            self.auto_expand,
        )

    @property
    def elements_added(self) -> int:
        """int: The number of elements added

        Note:
            Not settable"""
        return self._inserted_elements

    @property
    def capacity(self) -> int:
        """int: The number of bins

        Note:
            Not settable"""
        return self._cuckoo_capacity

    @property
    def max_swaps(self) -> int:
        """int: The maximum number of swaps to perform

        Note:
            Not settable"""
        return self.__max_cuckoo_swaps

    @property
    def bucket_size(self) -> int:
        """int: The number of buckets per bin

        Note:
            Not settable"""
        return self._bucket_size

    @property
    def buckets(self) -> typing.List[typing.List[int]]:  # TODO: not sure this is correct
        """list(list): The buckets holding the fingerprints

        Note:
            Not settable"""
        return self._buckets

    @property
    def expansion_rate(self) -> int:
        """int: The rate at expansion when the filter grows"""
        return self.__expansion_rate

    @expansion_rate.setter
    def expansion_rate(self, val: int):
        """set the self expand value"""
        self.__expansion_rate = int(val)

    @property
    def auto_expand(self) -> bool:
        """bool: True if the cuckoo filter will expand automatically"""
        return self.__auto_expand

    @auto_expand.setter
    def auto_expand(self, val: bool):
        """set the self expand value"""
        self.__auto_expand = bool(val)

    @property
    def fingerprint_size(self) -> int:
        """int: The size in bytes of the fingerprint

        Raises:
            ValueError: If the size is not between 1 and 4
        Note:
            The size of the fingerprint must be between 1 and 4"""
        return self.__fingerprint_size // 8

    @fingerprint_size.setter
    def fingerprint_size(self, val: int):
        """set the fingerprint size"""
        tmp = int(val)
        if not 1 <= tmp <= 4:
            msg = ("{}: fingerprint size must be between 1 and 4").format(self.__class__.__name__)
            raise ValueError(msg)
        # bytes to bits
        self.__fingerprint_size = tmp * 8  # type: ignore

    def load_factor(self) -> float:
        """float: How full the Cuckoo Filter is currently"""
        return self.elements_added / (self.capacity * self.bucket_size)

    def add(self, key: KeyT):
        """ Add element key to the filter

            Args:
                key (str): The element to add
            Raises:
                CuckooFilterFullError: When element not inserted after \
                maximum number of swaps or 'kicks' """
        idx_1, idx_2, fingerprint = self._generate_fingerprint_info(key)

        is_present = self._check_if_present(idx_1, idx_2, fingerprint)
        if is_present is not None:  # already there, nothing to do
            return
        finger = self._insert_fingerprint(fingerprint, idx_1, idx_2)
        self._deal_with_insertion(finger)

    def check(self, key: KeyT) -> bool:
        """Check if an element is in the filter

        Args:
            key (str): Element to check
        Returns:
            bool: True if likely present, False if definately not"""
        idx_1, idx_2, fingerprint = self._generate_fingerprint_info(key)
        is_present = self._check_if_present(idx_1, idx_2, fingerprint)
        if is_present is not None:
            return True
        return False

    def remove(self, key: KeyT) -> bool:
        """Remove an element from the filter

        Args:
            key (str): Element to remove
        Returns:
            bool: True if removed, False if not present"""
        idx_1, idx_2, fingerprint = self._generate_fingerprint_info(key)
        idx = self._check_if_present(idx_1, idx_2, fingerprint)
        if idx is None:
            return False
        self.buckets[idx].remove(fingerprint)
        self._inserted_elements -= 1
        return True

    def export(self, file: typing.Union[Path, str, IOBase, mmap]) -> None:
        """Export cuckoo filter to file

        Args:
            file: Path to file to export"""

        if not isinstance(file, (IOBase, mmap)):
            with open(file, "wb") as filepointer:
                self.export(filepointer)  # type:ignore
        else:
            filepointer = file  # type:ignore

            for i in range(len(self.buckets)):
                bucket = self.buckets[i]
                # do something for each...
                if isinstance(bucket, list):
                    self.buckets[i] = bucket = convert_to_typed(self.__class__.SINGLE_INT_C, bucket)  # type: ignore
                filepointer.write(bucket.tobytes())  # type: ignore
                leftover = self.bucket_size - len(bucket)
                rep = leftover * "I"
                filepointer.write(pack(rep, *([0] * leftover)))
            # now put out the required information at the end
            filepointer.write(self.__class__.HEADER_STRUCT.pack(self.bucket_size, self.max_swaps))

    def __bytes__(self) -> bytes:
        """Export cuckoo filter to `bytes`"""
        with BytesIO() as f:
            self.export(f)
            return f.getvalue()

    def expand(self):
        """Expand the cuckoo filter"""
        self._expand_logic(None)

    def _insert_fingerprint(self, fingerprint, idx_1, idx_2):
        """insert a fingerprint"""
        if self.__insert_element(fingerprint, idx_1):
            self._inserted_elements += 1
            return None
        elif self.__insert_element(fingerprint, idx_2):
            self._inserted_elements += 1
            return None

        # we didn't insert, so now we need to randomly select one index to use
        # and move things around to the other index, if possible, until we
        # either move everything around or hit the maximum number of swaps
        idx = random.choice([idx_1, idx_2])

        for _ in range(self.max_swaps):
            # select one element to be swapped out...
            swap_elm = random.randint(0, self.bucket_size - 1)

            swb = self.buckets[idx][swap_elm]
            fingerprint, self.buckets[idx][swap_elm] = swb, fingerprint

            # now find another place to put this fingerprint
            index_1, index_2 = self._indicies_from_fingerprint(fingerprint)

            idx = index_2 if idx == index_1 else index_1

            if self.__insert_element(fingerprint, idx):
                self._inserted_elements += 1
                return None

        # if we got here we have an error... we might need to know what is left
        return fingerprint

    def _load(self, file: typing.Union[Path, str, IOBase, mmap]) -> None:
        """load a cuckoo filter from file"""
        if not isinstance(file, (IOBase, mmap)):
            file = Path(file)
            with MMap(file) as filepointer:
                self._load(filepointer)
        else:
            self._parse_footer(file)  # type: ignore
            self._inserted_elements = 0
            # now pull everything in!
            self._parse_buckets(file)  # type: ignore

    SINGLE_INT_C = "I"
    SINGLE_INT_SIZE = calcsize(SINGLE_INT_C)
    HEADER_STRUCT = Struct("II")

    def _parse_footer(self, d: ByteString) -> None:
        list_size = len(d) - self.__class__.HEADER_STRUCT.size
        self._bucket_size, self.__max_cuckoo_swaps = self.__class__.HEADER_STRUCT.unpack(d[list_size:])  # type:ignore
        self._cuckoo_capacity = list_size // self.__class__.SINGLE_INT_SIZE // self.bucket_size

    def _parse_buckets(self, d: ByteString) -> None:
        self._buckets = list()
        bucket_byte_size = self.bucket_size * self.__class__.SINGLE_INT_SIZE
        offs = 0
        for _ in range(self.capacity):
            next_offs = offs + bucket_byte_size
            self.buckets.append(self._parse_bucket(d[offs:next_offs]))  # type: ignore
            offs = next_offs

    def _parse_bucket(self, d: ByteString) -> array.array:
        bucket = array.ArrayType(self.__class__.SINGLE_INT_C)
        bucket.frombytes(bytes(d))
        bucket = convert_to_typed(self.__class__.SINGLE_INT_C, [el for el in bucket if el])
        self._inserted_elements += len(bucket)
        return bucket

    def _check_if_present(self, idx_1, idx_2, fingerprint):
        """wrapper for checking if fingerprint is already inserted"""
        if fingerprint in self.buckets[idx_1]:
            return idx_1
        elif fingerprint in self.buckets[idx_2]:
            return idx_2
        return None

    def __insert_element(self, fingerprint, idx) -> bool:
        """insert element wrapper"""
        if len(self.buckets[idx]) < self.bucket_size:
            self.buckets[idx].append(fingerprint)
            return True
        return False

    def _expand_logic(self, extra_fingerprint):
        """the logic to acutally expand the cuckoo filter"""
        # get all the fingerprints
        fingerprints = self._setup_expand(extra_fingerprint)

        for finger in fingerprints:
            idx_1, idx_2 = self._indicies_from_fingerprint(finger)
            res = self._insert_fingerprint(finger, idx_1, idx_2)
            if res is not None:  # again, this *shouldn't* happen
                msg = "The CuckooFilter failed to expand"
                raise CuckooFilterFullError(msg)

    def _setup_expand(self, extra_fingerprint):
        """setup this thing"""
        fingerprints = list()
        if extra_fingerprint is not None:
            fingerprints.append(extra_fingerprint)
        for idx in range(self.capacity):
            fingerprints.extend(self.buckets[idx])

        self._cuckoo_capacity = self.capacity * self.expansion_rate
        self._buckets = list()
        self._inserted_elements = 0
        for _ in range(self.capacity):
            self.buckets.append(list())

        return fingerprints

    def _indicies_from_fingerprint(self, fingerprint):
        """ Generate the possible insertion indicies from a fingerprint

            Args:
                fingerprint (int): The fingerprint to use for generating \
                indicies """
        idx_1 = fingerprint % self.capacity
        idx_2 = self.__hash_func(str(fingerprint)) % self.capacity
        return idx_1, idx_2

    def _generate_fingerprint_info(self, key: KeyT) -> typing.Tuple[int, int, int]:
        """Generate the fingerprint and indicies using the provided key

        Args:
            key (str): The element for which information is to be generated
        """
        # generate the fingerprint along with the two possible indecies
        hash_val = self.__hash_func(key)
        fingerprint = get_x_bits(hash_val, 64, self.__fingerprint_size, True)
        idx_1, idx_2 = self._indicies_from_fingerprint(fingerprint)

        # NOTE: This should never happen...
        if idx_1 > self.capacity or idx_2 > self.capacity:
            msg = "Either idx_1 {0} or idx_2 {1} is greater than {2}"
            raise ValueError(msg.format(idx_1, idx_2, self.capacity))
        return idx_1, idx_2, fingerprint

    def _deal_with_insertion(self, finger):
        """some code to handle the insertion the same"""
        if finger is None:
            return
        elif self.auto_expand:
            self._expand_logic(finger)
        else:
            msg = "The {} is currently full".format(self.__class__.__name__)
            raise CuckooFilterFullError(msg)
