""" BloomFilter and BloomFiter on Disk, python implementation
    License: MIT
    Author: Tyler Barrus (barrust@gmail.com)
"""

from array import array

from probables.hashes import HashFuncT, KeyT, fnv_1a_32
from probables.utilities import Bitarray


class QuotientFilter:
    """Simple Quotient Filter implementation

    Args:
        quotient (int): The size of the quotient to use
        hash_function (function): Hashing strategy function to use `hf(key, number)`
    Returns:
        QuotientFilter: The initialized filter
    Raises:
        ValueError:
    Note:
        The size of the QuotientFilter will be 2**q"""

    __slots__ = (
        "_q",
        "_r",
        "_size",
        "_elements_added",
        "_hash_func",
        "_int_type_code",
        "_bits_per_elm",
        "_is_occupied",
        "_is_continuation",
        "_is_shifted",
        "_filter",
    )

    def __init__(self, quotient: int = 20, hash_function: HashFuncT = None):  # needs to be parameterized
        if quotient < 3 or quotient > 31:
            raise ValueError(
                f"Quotient filter: Invalid quotient setting; quotient must be between 3 and 31; {quotient} was provided"
            )
        self._q = quotient
        self._r = 32 - quotient
        self._size = 1 << self._q  # same as 2**q
        self._elements_added = 0
        self._hash_func = fnv_1a_32 if hash_function is None else hash_function

        # ensure we use the smallest type possible to reduce memory wastage
        if self._r <= 8:
            self._int_type_code = "B"
            self._bits_per_elm = 8
        elif self._r <= 16:
            self._int_type_code = "I"
            self._bits_per_elm = 16
        else:
            self._int_type_code = "L"
            self._bits_per_elm = 32

        self._is_occupied = Bitarray(self._size)
        self._is_continuation = Bitarray(self._size)
        self._is_shifted = Bitarray(self._size)
        self._filter = array(self._int_type_code, [0]) * self._size

    def __contains__(self, val: KeyT) -> bool:
        """setup the `in` keyword"""
        return self.contains(val)

    @property
    def quotient(self) -> int:
        """int: The size of the quotient, in bits"""
        return self._q

    @property
    def remainder(self) -> int:
        """int: The size of the remainder, in bits"""
        return self._r

    @property
    def num_elements(self) -> int:
        """int: The total size of the filter"""
        return self._size

    @property
    def elements_added(self) -> int:
        """int: The number of elements added to the filter"""
        return self._elements_added

    @property
    def bits_per_elm(self):
        """int: The number of bits used per element"""
        return self._bits_per_elm

    def add(self, key: KeyT) -> None:
        """Add key to the quotient filter

        Args:
            key (str|bytes): The element to add"""
        _hash = self._hash_func(key)
        key_quotient = _hash >> self._r
        key_remainder = _hash & ((1 << self._r) - 1)

        if not self._contains(key_quotient, key_remainder):
            # TODO, add it here
            self._add(key_quotient, key_remainder)

    def contains(self, key: KeyT) -> bool:
        """Check to see if key is likely in the quotient filter

        Args:
            key (str|bytes): The element to add
        Return:
            bool: True if likely encountered, False if definately not"""
        _hash = self._hash_func(key)
        key_quotient = _hash >> self._r
        key_remainder = _hash & ((1 << self._r) - 1)
        return self._contains(key_quotient, key_remainder)

    def _shift_insert(self, k, v, start, j, flag):
        if self._is_occupied[j] == 0 and self._is_continuation[j] == 0 and self._is_shifted[j] == 0:
            self._filter[j] = v
            self._is_occupied[k] = 1
            self._is_continuation[j] = 1 if j != start else 0
            self._is_shifted[j] = 1 if j != k else 0

        else:
            i = (j + 1) & (self._size - 1)

            while True:
                f = self._is_occupied[i] + self._is_continuation[i] + self._is_shifted[i]

                temp = self._is_continuation[i]
                self._is_continuation[i] = self._is_continuation[j]
                self._is_continuation[j] = temp

                self._is_shifted[i] = 1

                temp = self._filter[i]
                self._filter[i] = self._filter[j]
                self._filter[j] = temp

                if f == 0:
                    break

                i = (i + 1) & (self._size - 1)

            self._filter[j] = v
            self._is_occupied[k] = 1
            self._is_continuation[j] = 1 if j != start else 0
            self._is_shifted[j] = 1 if j != k else 0

            if flag == 1:
                self._is_continuation[(j + 1) & (self._size - 1)] = 1

    def _get_start_index(self, k):
        j = k
        cnts = 0

        while True:
            if j == k or self._is_occupied[j] == 1:
                cnts += 1

            if self._is_shifted[j] == 1:
                j = (j - 1) & (self._size - 1)
            else:
                break

        while True:
            if self._is_continuation[j] == 0:
                if cnts == 1:
                    break
                cnts -= 1

            j = (j + 1) & (self._size - 1)

        return j

    def _add(self, q: int, r: int):
        if self._is_occupied[q] == 0 and self._is_continuation[q] == 0 and self._is_shifted[q] == 0:
            self._filter[q] = r
            self._is_occupied[q] = 1

        else:
            start_idx = self._get_start_index(q)

            if self._is_occupied[q] == 0:
                self._shift_insert(q, r, start_idx, start_idx, 0)

            else:
                orig_start_idx = start_idx
                starts = 0
                f = self._is_occupied[start_idx] + self._is_continuation[start_idx] + self._is_shifted[start_idx]

                while starts == 0 and f != 0 and r > self._filter[start_idx]:
                    start_idx = (start_idx + 1) & (self._size - 1)

                    if self._is_continuation[start_idx] == 0:
                        starts += 1

                    f = self._is_occupied[start_idx] + self._is_continuation[start_idx] + self._is_shifted[start_idx]

                if starts == 1:
                    self._shift_insert(q, r, orig_start_idx, start_idx, 0)
                else:
                    self._shift_insert(q, r, orig_start_idx, start_idx, 1)
        self._elements_added += 1

    def _contains(self, q: int, r: int) -> bool:
        if self._is_occupied[q] == 0:
            return False

        start_idx = self._get_start_index(q)

        starts = 0
        meta_bits = self._is_occupied[start_idx] + self._is_continuation[start_idx] + self._is_shifted[start_idx]

        while meta_bits != 0:
            if self._is_continuation[start_idx] == 0:
                starts += 1

            if starts == 2 or self._filter[start_idx] > r:
                break

            if self._filter[start_idx] == r:
                return True

            start_idx = (start_idx + 1) & (self._size - 1)
            meta_bits = self._is_occupied[start_idx] + self._is_continuation[start_idx] + self._is_shifted[start_idx]

        return False
