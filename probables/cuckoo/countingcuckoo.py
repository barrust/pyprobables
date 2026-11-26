"""Counting Cuckoo Filter, python implementation
License: MIT
Author: Tyler Barrus (barrust@gmail.com)
"""

import warnings
from array import array
from collections.abc import Sequence

from probables.cuckoo._layer import COUNT_TYPECODE, index_hash
from probables.cuckoo.cuckoo import BucketsView, CuckooFilter
from probables.hashes import KeyT


class CountingCuckooFilter(CuckooFilter):
    """Simple Counting Cuckoo Filter implementation

    Args:
        capacity (int): The number of bins
        bucket_size (int): The number of buckets per bin
        max_swaps (int): The number of cuckoo swaps before stopping
        expansion_rate (int): The rate at which to expand; an integer greater than 1
        auto_expand (bool): If the filter should automatically expand
        finger_size (int): The size of the fingerprint to use in bytes (between 1 and 4)
        filepath (str): The path to the file to load or None if no file
        hash_function (function): Hashing strategy function to use `hf(key)`
    Returns:
        CountingCuckooFilter: A Cuckoo Filter object
    Note:
        Two different keys that share a fingerprint and a bucket (as often as a false positive)
        share a count."""

    __slots__ = ()

    @property
    def _counting(self) -> bool:
        return True

    @property
    def unique_elements(self) -> int:
        """int: unique number of elements inserted"""
        return self._unique_elements

    @property
    def buckets(self) -> Sequence[list["CountingCuckooBin"]]:  # type: ignore
        """Sequence(list): A read-only view of the fingerprints and counts in each bin, layer by layer

        Note:
            Not settable; each bin is built when it is accessed, and changing it does not change the filter"""
        return BucketsView(self._layers, CountingCuckooBin)

    def add(self, key: KeyT) -> None:
        """Add element key to the filter

        Args:
            key (str): The element to add
        Raises:
            CuckooFilterFullError: When element not inserted after maximum number of swaps or 'kicks'
            OverflowError: When the count of the element would not fit in 32 bits"""
        hash_val = self._key_hash(key)
        mixed = index_hash(hash_val)
        found = self._find(hash_val, mixed)
        if found is not None:
            layer, slot = found
            layer.counts[slot] += 1  # type: ignore
            self._inserted_elements += 1
            return
        self._insert(hash_val, mixed, 1)
        self._unique_elements += 1
        self._inserted_elements += 1

    def check(self, key: KeyT) -> int:  # type: ignore
        """Check if an element is in the filter

        Args:
            key (str): Element to check
        Returns:
            int: The number of times inserted into the filter"""
        hash_val = self._key_hash(key)
        found = self._find(hash_val, index_hash(hash_val))
        if found is None:
            return 0
        layer, slot = found
        return layer.counts[slot]  # type: ignore

    def remove(self, key: KeyT) -> bool:
        """Remove an element from the filter

        Args:
            key (str): Element to remove
        Returns:
            bool: True if removed, False if not present"""
        hash_val = self._key_hash(key)
        found = self._find(hash_val, index_hash(hash_val))
        if found is None:
            return False
        layer, slot = found
        layer.counts[slot] -= 1  # type: ignore
        self._inserted_elements -= 1
        if layer.counts[slot] == 0:  # type: ignore
            layer.clear(slot)
            self._unique_elements -= 1
        return True


class CountingCuckooBin:
    """A copy of a fingerprint and its count, as returned by `CountingCuckooFilter.buckets`

    Note:
        Changing a bin does not change the filter; use `CountingCuckooFilter.add()` and `remove()`"""

    # keep it lightweight
    __slots__ = ["__bin"]

    def __init__(self, fingerprint: int, count: int) -> None:
        """init"""
        self.__bin = array(COUNT_TYPECODE, [fingerprint, count])

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
        """increment the count of this copy

        Deprecated: it does not change the filter; use `CountingCuckooFilter.add()`"""
        warnings.warn(
            "CountingCuckooBin.increment() does not change the filter; use CountingCuckooFilter.add()",
            DeprecationWarning,
            stacklevel=2,
        )
        self.__bin[1] += 1
        return self.__bin[1]

    def decrement(self) -> int:
        """decrement the count of this copy

        Deprecated: it does not change the filter; use `CountingCuckooFilter.remove()`"""
        warnings.warn(
            "CountingCuckooBin.decrement() does not change the filter; use CountingCuckooFilter.remove()",
            DeprecationWarning,
            stacklevel=2,
        )
        self.__bin[1] -= 1
        return self.__bin[1]
