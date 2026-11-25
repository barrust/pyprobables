"""Counting Cuckoo Filter, python implementation
License: MIT
Author: Tyler Barrus (barrust@gmail.com)
"""

from array import array
from collections.abc import ByteString
from pathlib import Path

from probables.cuckoo.cuckoo import CuckooFilter
from probables.hashes import KeyT, SimpleHashT
from probables.utilities import resolve_path


class CountingCuckooFilter(CuckooFilter):
    """Simple Counting Cuckoo Filter implementation.

    Filters exported by older pyprobables releases use an incompatible format.
    Use an older release to read them or rebuild from the original keys.

    Args:
        capacity (int): The number of bins
        bucket_size (int): The number of buckets per bin
        max_swaps (int): The number of cuckoo swaps before stopping
        expansion_rate (int): The rate at which to expand
        auto_expand (bool): If the filter should automatically expand
        finger_size (int): The size of the fingerprint to use in bytes \
            (between 1 and 4).
        filename (str): The path to the file to load or None if no file
    Returns:
        CountingCuckooFilter: A Cuckoo Filter object"""

    __slots__ = ("__unique_elements",)

    def __init__(
        self,
        capacity: int = 10000,
        bucket_size: int = 4,
        max_swaps: int = 500,
        expansion_rate: int = 2,
        auto_expand: bool = True,
        finger_size: int = 4,
        filepath: str | Path | None = None,
        hash_function: SimpleHashT | None = None,
    ) -> None:
        """setup the data structure"""
        self.__unique_elements = 0
        super().__init__(
            capacity,
            bucket_size,
            max_swaps,
            expansion_rate,
            auto_expand,
            finger_size,
            filepath,
            hash_function,
        )

    @classmethod
    def init_error_rate(
        cls,
        error_rate: float,
        capacity: int = 10000,
        bucket_size: int = 4,
        max_swaps: int = 500,
        expansion_rate: int = 2,
        auto_expand: bool = True,
        hash_function: SimpleHashT | None = None,
    ):
        """Initialize a simple Cuckoo Filter based on error rate

        Args:
            error_rate (float):
            capacity (int): The number of bins
            bucket_size (int): The number of buckets per bin
            max_swaps (int): The number of cuckoo swaps before stopping
            expansion_rate (int): The rate at which to expand
            auto_expand (bool): If the filter should automatically expand
            hash_function (function): Hashing strategy function to use `hf(key)`
        Returns:
            CuckooFilter: A Cuckoo Filter object"""
        cku = CountingCuckooFilter(
            capacity=capacity,
            bucket_size=bucket_size,
            auto_expand=auto_expand,
            max_swaps=max_swaps,
            expansion_rate=expansion_rate,
            hash_function=hash_function,
        )
        cku._set_error_rate(error_rate)
        return cku

    @classmethod
    def load_error_rate(cls, error_rate: float, filepath: str | Path, hash_function: SimpleHashT | None = None):
        """Initialize a previously exported Cuckoo Filter based on error rate

        Args:
            error_rate (float):
            filepath (str): The path to the file to load or None if no file
            hash_function (function): Hashing strategy function to use \
            `hf(key)`
        Returns:
            CuckooFilter: A Cuckoo Filter object
        """
        filepath = resolve_path(filepath)
        cku = CountingCuckooFilter(filepath=filepath, hash_function=hash_function)
        cku._set_error_rate(error_rate)
        return cku

    @classmethod
    def frombytes(
        cls, b: ByteString, error_rate: float | None = None, hash_function: SimpleHashT | None = None
    ) -> "CountingCuckooFilter":
        """
        Args:
            b (ByteString): The exported counting cuckoo filter
            error_rate (float): Optional original error rate; the fingerprint size must match the export
            hash_function (function): Original hashing strategy function `hf(key)`
        Returns:
            CountingCuckooFilter: A Counting Cuckoo Filter object"""
        cku = CountingCuckooFilter(hash_function=hash_function)
        cku._load(b)

        # if error rate is provided, use it
        cku._set_error_rate(error_rate)
        return cku

    def __contains__(self, val: KeyT) -> bool:
        """setup the `in` keyword"""
        return self.check(val) > 0

    @property
    def unique_elements(self) -> int:
        """int: unique number of elements inserted"""
        return self.__unique_elements

    @property
    def buckets(self) -> list[list["CountingCuckooBin"]]:  # type: ignore
        """list(list): The buckets holding the fingerprints

        Note:
            Not settable"""
        return self._buckets

    def load_factor(self) -> float:
        """float: How full the Cuckoo Filter is currently"""
        return self.unique_elements / (self.capacity * self.bucket_size)

    def add(self, key: KeyT) -> None:
        """Add element key to the filter

        Args:
            key (str): The element to add
        Raises:
            CuckooFilterFullError: When element not inserted after maximum number of swaps or 'kicks'"""
        key_hash = self._key_hash(key)
        location = self._find_hash(key_hash)
        if location is not None:
            idx, pos = location
            self.buckets[idx][pos].increment()
        else:
            self._add_entry(CountingCuckooBin(self._fingerprint_from_hash(key_hash), 1), key_hash)
            self.__unique_elements += 1
        self._inserted_elements += 1

    def check(self, key: KeyT) -> int:  # type: ignore
        """Check if an element is in the filter

        Args:
            key (str): Element to check
        Returns:
            int: The number of times inserted into the filter"""
        key_hash = self._key_hash(key)
        location = self._find_hash(key_hash)
        if location is not None:
            idx, pos = location
            return self.buckets[idx][pos].count
        idx_1, idx_2 = self._indices_from_hash(key_hash)
        fingerprint = self._fingerprint_from_hash(key_hash)
        is_present = self._check_if_present(idx_1, idx_2, fingerprint)
        val = 0
        if is_present is not None:
            # get the count out!
            for bucket in self.buckets[is_present]:
                if fingerprint in bucket:
                    val = bucket.count
                    break
        return val

    def remove(self, key: KeyT) -> bool:
        """Remove an element from the filter

        Args:
            key (str): Element to remove"""
        location = self._find_hash(self._key_hash(key))
        if location is None:
            return False
        idx, pos = location
        entry = self.buckets[idx][pos]
        entry.decrement()
        self._inserted_elements -= 1
        if entry.count == 0:
            del self.buckets[idx][pos]
            del self._hash_buckets[idx][pos]
            self.__unique_elements -= 1
        return True

    def _check_if_present(self, idx_1: int, idx_2: int, fingerprint: int) -> int | None:
        """wrapper for checking if fingerprint is already inserted"""
        if fingerprint in [x.finger for x in self.buckets[idx_1]]:
            return idx_1
        if fingerprint in [x.finger for x in self.buckets[idx_2]]:
            return idx_2
        return None

    def _load_data(self, data) -> None:
        self.__unique_elements = 0
        super()._load_data(data)

    def _format_kind(self) -> int:
        return 1

    def _entry_from_hash(self, key_hash: int, count: int) -> "CountingCuckooBin":
        self.__unique_elements += 1
        return CountingCuckooBin(self._fingerprint_from_hash(key_hash), count)

    def _entry_count(self, entry: "CountingCuckooBin") -> int:
        return entry.count

    def _entry_fingerprint(self, entry: "CountingCuckooBin") -> int:
        return entry.finger


class CountingCuckooBin:
    """A container class for the counting cuckoo filter"""

    # keep it lightweight
    __slots__ = ["__bin"]

    def __init__(self, fingerprint: int, count: int) -> None:
        """init"""
        self.__bin = array("I", [fingerprint, count])

    def __contains__(self, val: int) -> bool:
        """setup the `in` construct"""
        return self.__bin[0] == val

    def get_array(self):
        """return the array implementation"""
        return self.__bin

    @property
    def finger(self) -> int:
        """fingerprint property"""
        return self.__bin[0]

    @property
    def count(self) -> int:
        """count property"""
        return self.__bin[1]

    def __repr__(self) -> str:
        """how do we represent this?"""
        return self.__str__()

    def __str__(self) -> str:
        """convert it into a string"""
        return f"(fingerprint:{self.__bin[0]} count:{self.__bin[1]})"

    def increment(self) -> int:
        """increment"""
        self.__bin[1] += 1
        return self.__bin[1]

    def decrement(self) -> int:
        """decrement"""
        self.__bin[1] -= 1
        return self.__bin[1]
