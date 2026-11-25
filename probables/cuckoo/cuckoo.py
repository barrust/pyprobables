"""Cuckoo Filter, python implementation
License: MIT
Author: Tyler Barrus (barrust@gmail.com)
"""

import math
import random
from array import array
from collections.abc import ByteString
from io import BytesIO, IOBase
from mmap import mmap
from numbers import Number
from pathlib import Path
from struct import Struct, error as StructError

from probables.exceptions import CuckooFilterFullError, InitializationError
from probables.hashes import KeyT, SimpleHashT, fnv_1a
from probables.utilities import MMap, get_x_bits, is_valid_file, resolve_path


class CuckooFilter:
    """Simple Cuckoo Filter implementation

    Args:
        capacity (int): The number of bins
        bucket_size (int): The number of buckets per bin
        max_swaps (int): The number of cuckoo swaps before stopping
        expansion_rate (int): The rate at which to expand
        auto_expand (bool): If the filter should automatically expand
        finger_size (int): The size of the fingerprint to use in bytes \
            (between 1 and 4). Legacy exports require this value on import.
        filepath (str): The path to the file to load or None if no file
        hash_function (function): Hashing strategy function to use `hf(key)`
    Returns:
        CuckooFilter: A Cuckoo Filter object"""

    __slots__ = (
        "_bucket_size",
        "_cuckoo_capacity",
        "__max_cuckoo_swaps",
        "__expansion_rate",
        "__auto_expand",
        "_fingerprint_size",
        "__hash_func",
        "_inserted_elements",
        "_buckets",
        "_error_rate",
        "_hash_buckets",
        "_legacy_layout",
    )

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
        self.__expansion_rate = 2
        self.expansion_rate = expansion_rate
        self.__auto_expand = True
        self.auto_expand = auto_expand
        self._fingerprint_size = 32
        self.fingerprint_size = finger_size

        if hash_function is None:
            self.__hash_func = fnv_1a
        else:
            self.__hash_func = hash_function  # type: ignore
        self._inserted_elements = 0
        self._legacy_layout = False
        self._hash_buckets: list[list[int]] = []
        self._error_rate = float(self._calc_error_rate())
        if filepath is None:
            self._buckets = []  # type: ignore
            for _ in range(self.capacity):
                self.buckets.append([])
                self._hash_buckets.append([])
        elif is_valid_file(filepath):
            filepath = resolve_path(filepath)
            self._load(filepath)
            if self._legacy_layout:
                self._error_rate = self._calc_error_rate()
        else:
            msg = "CuckooFilter: failed to load provided file"
            raise InitializationError(msg)

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
            hash_function (function): Hashing strategy function to use \
            `hf(key)`
        Returns:
            CuckooFilter: A Cuckoo Filter object"""
        cku = CuckooFilter(
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
    def load_error_rate(
        cls,
        error_rate: float,
        filepath: str | Path,
        hash_function: SimpleHashT | None = None,
    ):
        """Initialize a previously exported Cuckoo Filter based on error rate

        Args:
            error_rate (float):
            filepath (str): The path to the file to load or None if no file
            hash_function (function): Hashing strategy function to use `hf(key)`
        Returns:
            CuckooFilter: A Cuckoo Filter object"""
        filepath = resolve_path(filepath)
        cku = CuckooFilter(filepath=filepath, hash_function=hash_function)
        cku._set_error_rate(error_rate)
        return cku

    @classmethod
    def frombytes(
        cls,
        b: ByteString,
        error_rate: float | None = None,
        hash_function: SimpleHashT | None = None,
    ) -> "CuckooFilter":
        """
        Args:
            b (ByteString): The exported cuckoo filter
            error_rate (float): Original error rate, required for legacy error-rate-based exports
            hash_function (function): Original hashing strategy function `hf(key)`
        Returns:
            CuckooFilter: A Cuckoo Filter object
        """
        cku = CuckooFilter(hash_function=hash_function)
        cku._load(b)  # type: ignore

        # if error rate is provided, use it
        cku._set_error_rate(error_rate)
        return cku

    def __contains__(self, key: KeyT) -> bool:
        """setup the `in` keyword"""
        return self.check(key)

    def __str__(self):
        """setup what it will print"""
        return (
            f"{self.__class__.__name__}:\n"
            f"\tCapacity: {self.capacity}\n"
            f"\tTotal Bins: {self.capacity * self.bucket_size}\n"
            f"\tLoad Factor: {self.load_factor() * 100}%\n"
            f"\tInserted Elements: {self.elements_added}\n"
            f"\tMax Swaps: {self.max_swaps}\n"
            f"\tExpansion Rate: {self.expansion_rate}\n"
            f"\tAuto Expand: {self.auto_expand}"
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
    def buckets(self) -> list[list[int]]:
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
        self.__expansion_rate = val

    @property
    def error_rate(self) -> float:
        """float: Target error rate, or theoretical estimate for the fingerprint size.

        The estimate assumes suitably distributed hashes and does not apply to
        legacy filters loaded from the old fingerprint-only layout.
        """
        return self._error_rate

    @property
    def auto_expand(self) -> bool:
        """bool: True if the cuckoo filter will expand automatically"""
        return self.__auto_expand

    @auto_expand.setter
    def auto_expand(self, val: bool):
        """set the self expand value"""
        self.__auto_expand = bool(val)

    @property
    def fingerprint_size_bits(self) -> int:
        """int: The size in bits of the fingerprint"""
        return self._fingerprint_size

    @property
    def fingerprint_size(self) -> int:
        """int: The size in bytes of the fingerprint

        Raises:
            ValueError: If the size is not between 1 and 4
        Note:
            The size of the fingerprint must be between 1 and 4 and cannot
            be changed on a non-empty filter."""
        return math.ceil(self.fingerprint_size_bits / 8)

    @fingerprint_size.setter
    def fingerprint_size(self, val: int):
        """set the fingerprint size"""
        tmp = val
        if not 1 <= tmp <= 4:
            msg = f"{self.__class__.__name__}: fingerprint size must be between 1 and 4"
            raise ValueError(msg)
        if getattr(self, "_inserted_elements", 0) and tmp * 8 != self._fingerprint_size:
            raise ValueError("Cannot change fingerprint size on a non-empty cuckoo filter")
        # bytes to bits
        self._fingerprint_size = tmp * 8
        self._error_rate = self._calc_error_rate()

    def load_factor(self) -> float:
        """float: How full the Cuckoo Filter is currently"""
        return self.elements_added / (self.capacity * self.bucket_size)

    def add(self, key: KeyT):
        """Add element key to the filter

        Args:
            key (str): The element to add
        Raises:
            CuckooFilterFullError: When element not inserted after maximum number of swaps or 'kicks'"""
        if not self._legacy_layout:
            key_hash = self._key_hash(key)
            if self._find_hash(key_hash) is not None:
                return
            fingerprint = self._fingerprint_from_hash(key_hash)
            self._add_modern(fingerprint, key_hash)
            self._inserted_elements += 1
            return
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
        return is_present is not None

    def remove(self, key: KeyT) -> bool:
        """Remove an element from the filter

        Args:
            key (str): Element to remove
        Returns:
            bool: True if removed, False if not present"""
        if not self._legacy_layout:
            location = self._find_hash(self._key_hash(key))
            if location is None:
                return False
            idx, pos = location
            del self.buckets[idx][pos]
            del self._hash_buckets[idx][pos]
            self._inserted_elements -= 1
            return True
        idx_1, idx_2, fingerprint = self._generate_fingerprint_info(key)
        idx = self._check_if_present(idx_1, idx_2, fingerprint)
        if idx is None:
            return False
        self.buckets[idx].remove(fingerprint)
        self._inserted_elements -= 1
        return True

    def export(self, file: Path | str | IOBase | mmap) -> None:
        """Export cuckoo filter to file

        Args:
            file: Path to file to export"""

        if not isinstance(file, IOBase | mmap):
            file = resolve_path(file)
            with open(file, "wb") as filepointer:
                self.export(filepointer)  # type:ignore
        else:
            filepointer = file  # type:ignore
            if not self._legacy_layout:
                self._export_modern(filepointer)
                return
            for _, val in enumerate(self.buckets):
                bucket = array(self._CUCKOO_SINGLE_INT_C, val)
                bucket.extend([0] * (self.bucket_size - len(bucket)))
                bucket.tofile(filepointer)
            # now put out the required information at the end
            filepointer.write(self._CUCKOO_FOOTER_STRUCT.pack(self.bucket_size, self.max_swaps))

    def __bytes__(self) -> bytes:
        """Export cuckoo filter to `bytes`"""
        with BytesIO() as f:
            self.export(f)
            return f.getvalue()

    def expand(self):
        """Expand the cuckoo filter"""
        if self._legacy_layout:
            self._expand_logic(None)
        else:
            self._expand_modern()

    def _insert_fingerprint(self, fingerprint, idx_1, idx_2):
        """insert a fingerprint"""
        if self.__insert_element(fingerprint, idx_1):
            self._inserted_elements += 1
            return None
        if self.__insert_element(fingerprint, idx_2):
            self._inserted_elements += 1
            return None

        # we didn't insert, so now we need to randomly select one index to use
        # and move things around to the other index, if possible, until we
        # either move everything around or hit the maximum number of swaps
        idx = random.choice([idx_1, idx_2])
        orig_fingerprint = fingerprint
        swaps = []

        for _ in range(self.max_swaps):
            # select one element to be swapped out...
            swap_elm = random.randint(0, self.bucket_size - 1)

            swb = self.buckets[idx][swap_elm]
            swaps.append((idx, swap_elm, swb))
            fingerprint, self.buckets[idx][swap_elm] = swb, fingerprint

            # now find another place to put this fingerprint
            index_1, index_2 = self._indicies_from_fingerprint(fingerprint)

            idx = index_2 if idx == index_1 else index_1

            if self.__insert_element(fingerprint, idx):
                self._inserted_elements += 1
                return None

        # unable to place the new fingerprint; undo the swaps so that the
        # failed insertion leaves the filter unchanged
        for idx, swap_elm, elm in reversed(swaps):
            self.buckets[idx][swap_elm] = elm

        # if we got here we have an error... we might need to know what is left
        return orig_fingerprint

    def _load(self, file: Path | str | IOBase | mmap | bytes | ByteString) -> None:
        """load a cuckoo filter from file"""
        if not isinstance(file, IOBase | mmap | bytes | bytearray | memoryview):
            file = resolve_path(file)
            with MMap(file) as filepointer:
                self._load(filepointer)
        else:
            if isinstance(file, IOBase):
                file = file.read()
            if bytes(file[:6]) == self._MODERN_MAGIC[:6]:
                if bytes(file[:8]) != self._MODERN_MAGIC:
                    raise InitializationError("Unsupported cuckoo filter format")
                self._load_modern(file)
                return
            self._legacy_layout = True
            self._hash_buckets = []
            self._parse_footer(file, self._CUCKOO_FOOTER_STRUCT)  # type: ignore
            self._inserted_elements = 0
            # now pull everything in!
            self._parse_buckets(file)  # type: ignore
            self._error_rate = self._calc_error_rate()

    _CUCKOO_SINGLE_INT_C = "I"
    _CUCKOO_SINGLE_INT_SIZE = Struct(_CUCKOO_SINGLE_INT_C).size
    _CUCKOO_FOOTER_STRUCT = Struct("II")

    def _parse_footer(self, d: ByteString, stct: Struct) -> None:
        """parse bytes and set footer information"""
        list_size = len(d) - stct.size
        self._bucket_size, self.__max_cuckoo_swaps = stct.unpack(d[list_size:])  # type:ignore
        self._cuckoo_capacity = list_size // self._CUCKOO_SINGLE_INT_SIZE // self.bucket_size

    def _parse_buckets(self, d: ByteString) -> None:
        """parse bytes and set buckets"""
        self._buckets = []
        bucket_byte_size = self.bucket_size * self._CUCKOO_SINGLE_INT_SIZE
        offs = 0
        for _ in range(self.capacity):
            next_offs = offs + bucket_byte_size
            self.buckets.append(self._parse_bucket(d[offs:next_offs]))  # type: ignore
            offs = next_offs

    def _parse_bucket(self, d: ByteString) -> array:
        """parse a single bucket"""
        bucket = array(self._CUCKOO_SINGLE_INT_C, bytes(d))
        bucket = array(self._CUCKOO_SINGLE_INT_C, [el for el in bucket if el])
        self._inserted_elements += len(bucket)
        return bucket

    def _set_error_rate(self, error_rate: float | None) -> None:
        """set error rate correctly"""
        # if error rate is provided, use it
        if error_rate is not None:
            if not 0 < error_rate < 1:
                raise ValueError("Cuckoo filter error rate must be between 0 and 1")
            bits = math.ceil(-math.log2(error_rate) + math.log2(self.bucket_size) + 1)
            if not 1 <= bits <= 32:
                raise ValueError("Cuckoo filter error rate requires a fingerprint outside 1 to 32 bits")
            if self._inserted_elements and not self._legacy_layout and bits != self.fingerprint_size_bits:
                raise ValueError("Cannot change fingerprint size on a non-empty cuckoo filter")
            self._error_rate = error_rate
            self._fingerprint_size = bits

    def _check_if_present(self, idx_1, idx_2, fingerprint):
        """wrapper for checking if fingerprint is already inserted"""
        if fingerprint in self.buckets[idx_1]:
            return idx_1
        if fingerprint in self.buckets[idx_2]:
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
        # snapshot the current state so that a failed expansion leaves the
        # filter unchanged
        old_capacity = self._cuckoo_capacity
        old_buckets = self._buckets
        old_inserted = self._inserted_elements

        try:
            # get all the fingerprints
            fingerprints = self._setup_expand(extra_fingerprint)

            for finger in fingerprints:
                idx_1, idx_2 = self._indicies_from_fingerprint(finger)
                res = self._insert_fingerprint(finger, idx_1, idx_2)
                if res is not None:  # again, this *shouldn't* happen
                    msg = "The CuckooFilter failed to expand"
                    raise CuckooFilterFullError(msg)
        except Exception:
            self._cuckoo_capacity = old_capacity
            self._buckets = old_buckets
            self._inserted_elements = old_inserted
            raise

    def _setup_expand(self, extra_fingerprint):
        """setup this thing"""
        fingerprints = []
        if extra_fingerprint is not None:
            fingerprints.append(extra_fingerprint)
        for idx in range(self.capacity):
            fingerprints.extend(self.buckets[idx])

        self._cuckoo_capacity = self.capacity * self.expansion_rate
        self._buckets = []
        self._inserted_elements = 0
        for _ in range(self.capacity):
            self.buckets.append([])

        return fingerprints

    def _indicies_from_fingerprint(self, fingerprint):
        """Generate the possible insertion indicies from a fingerprint

        Args:
            fingerprint (int): The fingerprint to use for generating indicies"""
        idx_1 = fingerprint % self.capacity
        idx_2 = self.__hash_func(str(fingerprint)) % self.capacity  # type: ignore
        return idx_1, idx_2

    def _generate_fingerprint_info(self, key: KeyT) -> tuple[int, int, int]:
        """Generate the fingerprint and indicies using the provided key

        Args:
            key (str): The element for which information is to be generated
        """
        # generate the fingerprint along with the two possible indecies
        hash_val = self._key_hash(key)
        fingerprint = get_x_bits(hash_val, 64, self.fingerprint_size_bits, True)
        if self._legacy_layout:
            idx_1, idx_2 = self._indicies_from_fingerprint(fingerprint)
        else:
            idx_1, idx_2 = self._modern_indices(hash_val)

        # NOTE: This should never happen...
        if idx_1 > self.capacity or idx_2 > self.capacity:
            raise ValueError(f"Either idx_1 {idx_1} or idx_2 {idx_2} is greater than {self.capacity}")
        return idx_1, idx_2, fingerprint

    _MODERN_MAGIC = b"PYCKOO\x01\x00"
    _MODERN_HEADER = Struct("<8sBIIIId")
    _MODERN_BUCKET_SIZE = Struct("<I")
    _MODERN_HASH = Struct("<Q")
    _MODERN_COUNT = Struct("<I")

    def _key_hash(self, key: KeyT) -> int:
        return self.__hash_func(key) & ((1 << 64) - 1)  # type: ignore

    def _fingerprint_from_hash(self, key_hash: int) -> int:
        return get_x_bits(key_hash, 64, self.fingerprint_size_bits, True)

    def _modern_indices(self, key_hash: int) -> tuple[int, int]:
        idx = (key_hash >> 32) % self.capacity
        return idx, self._alternate_index(idx, self._fingerprint_from_hash(key_hash))

    def _alternate_index(self, idx: int, fingerprint: int) -> int:
        return (self.__hash_func(str(fingerprint)) - idx) % self.capacity  # type: ignore

    def _find_hash(self, key_hash: int) -> tuple[int, int] | None:
        for idx in set(self._modern_indices(key_hash)):
            try:
                return idx, self._hash_buckets[idx].index(key_hash)
            except ValueError:
                pass
        return None

    def _add_modern(self, entry, key_hash: int) -> None:
        if self._insert_modern(entry, key_hash):
            return
        if not self.auto_expand:
            raise CuckooFilterFullError(f"The {self.__class__.__name__} is currently full")
        self._expand_modern((entry, key_hash))

    def _insert_modern(self, entry, key_hash: int) -> bool:
        idx_1, idx_2 = self._modern_indices(key_hash)
        for idx in (idx_1, idx_2):
            if len(self.buckets[idx]) < self.bucket_size:
                self.buckets[idx].append(entry)
                self._hash_buckets[idx].append(key_hash)
                return True
        idx = random.choice((idx_1, idx_2))
        swaps = []
        for _ in range(self.max_swaps):
            pos = random.randrange(self.bucket_size)
            swaps.append((idx, pos, self.buckets[idx][pos], self._hash_buckets[idx][pos]))
            entry, self.buckets[idx][pos] = self.buckets[idx][pos], entry
            key_hash, self._hash_buckets[idx][pos] = self._hash_buckets[idx][pos], key_hash
            idx = self._alternate_index(idx, self._fingerprint_from_hash(key_hash))
            if len(self.buckets[idx]) < self.bucket_size:
                self.buckets[idx].append(entry)
                self._hash_buckets[idx].append(key_hash)
                return True
        for idx, pos, old_entry, old_hash in reversed(swaps):
            self.buckets[idx][pos] = old_entry
            self._hash_buckets[idx][pos] = old_hash
        return False

    def _expand_modern(self, extra=None) -> None:
        self._validate_modern_buckets()
        old_capacity, old_buckets, old_hashes = self.capacity, self._buckets, self._hash_buckets
        entries = [(entry, h) for bucket, hashes in zip(old_buckets, old_hashes) for entry, h in zip(bucket, hashes)]
        if extra is not None:
            entries.append(extra)
        if not isinstance(self.expansion_rate, int) or self.expansion_rate <= 1:
            raise ValueError("Cuckoo filter expansion rate must be an integer greater than 1")
        try:
            self._cuckoo_capacity *= self.expansion_rate
            self._buckets = [[] for _ in range(self.capacity)]
            self._hash_buckets = [[] for _ in range(self.capacity)]
            for entry, key_hash in entries:
                if not self._insert_modern(entry, key_hash):
                    raise CuckooFilterFullError(f"The {self.__class__.__name__} failed to expand")
        except Exception:
            self._cuckoo_capacity, self._buckets, self._hash_buckets = old_capacity, old_buckets, old_hashes
            raise

    def _modern_kind(self) -> int:
        return 0

    def _modern_entry(self, key_hash: int, _count: int):
        return self._fingerprint_from_hash(key_hash)

    def _modern_count(self, _entry) -> int:
        return 1

    def _modern_fingerprint(self, entry) -> int:
        return entry

    def _validate_modern_buckets(self) -> None:
        if len(self.buckets) != self.capacity or len(self._hash_buckets) != self.capacity:
            raise ValueError("Cuckoo filter buckets do not match capacity")
        seen = set()
        for idx, (bucket, hashes) in enumerate(zip(self.buckets, self._hash_buckets)):
            if len(bucket) != len(hashes) or len(bucket) > self.bucket_size:
                raise ValueError("Cuckoo filter bucket hashes do not match entries")
            for entry, key_hash in zip(bucket, hashes):
                if (key_hash in seen or idx not in self._modern_indices(key_hash)
                        or self._modern_fingerprint(entry) != self._fingerprint_from_hash(key_hash)):
                    raise ValueError("Cuckoo filter entry does not match hash")
                seen.add(key_hash)

    def _export_modern(self, file) -> None:
        self._validate_modern_buckets()
        file.write(self._MODERN_HEADER.pack(
            self._MODERN_MAGIC, self._modern_kind(), self.capacity, self.bucket_size,
            self.max_swaps, self.fingerprint_size_bits, self.error_rate,
        ))
        for bucket, hashes in zip(self.buckets, self._hash_buckets):
            file.write(self._MODERN_BUCKET_SIZE.pack(len(bucket)))
            for entry, key_hash in zip(bucket, hashes):
                file.write(self._MODERN_HASH.pack(key_hash))
                if self._modern_kind():
                    file.write(self._MODERN_COUNT.pack(self._modern_count(entry)))

    def _load_modern(self, data) -> None:
        try:
            magic, kind, capacity, bucket_size, max_swaps, bits, error_rate = self._MODERN_HEADER.unpack_from(data)
            if (magic != self._MODERN_MAGIC or kind != self._modern_kind() or not capacity or not bucket_size
                    or not max_swaps or not 1 <= bits <= 32 or not math.isfinite(error_rate) or not 0 < error_rate):
                raise ValueError("invalid cuckoo filter header")
            if capacity > (len(data) - self._MODERN_HEADER.size) // self._MODERN_BUCKET_SIZE.size:
                raise ValueError("invalid cuckoo filter capacity")
            self._cuckoo_capacity = capacity
            self._bucket_size = bucket_size
            self.__max_cuckoo_swaps = max_swaps
            self._fingerprint_size = bits
            self._error_rate = error_rate
            self._buckets = []
            self._hash_buckets = []
            self._inserted_elements = 0
            offset = self._MODERN_HEADER.size
            seen = set()
            for idx in range(capacity):
                size = self._MODERN_BUCKET_SIZE.unpack_from(data, offset)[0]
                offset += self._MODERN_BUCKET_SIZE.size
                if size > bucket_size:
                    raise ValueError("invalid cuckoo bucket size")
                bucket, hashes = [], []
                for _ in range(size):
                    key_hash = self._MODERN_HASH.unpack_from(data, offset)[0]
                    offset += self._MODERN_HASH.size
                    if key_hash in seen or idx not in self._modern_indices(key_hash):
                        raise ValueError("invalid cuckoo entry")
                    seen.add(key_hash)
                    count = 1
                    if kind:
                        count = self._MODERN_COUNT.unpack_from(data, offset)[0]
                        offset += self._MODERN_COUNT.size
                        if not count:
                            raise ValueError("invalid cuckoo count")
                    bucket.append(self._modern_entry(key_hash, count))
                    hashes.append(key_hash)
                    self._inserted_elements += count
                self._buckets.append(bucket)
                self._hash_buckets.append(hashes)
            if offset != len(data):
                raise ValueError("invalid cuckoo filter length")
            self._legacy_layout = False
        except (ValueError, OverflowError, StructError) as exc:
            raise InitializationError(f"Invalid cuckoo filter data: {exc}") from exc

    def _deal_with_insertion(self, finger):
        """some code to handle the insertion the same"""
        if finger is None:
            return
        if self.auto_expand:
            self._expand_logic(finger)
        else:
            msg = f"The {self.__class__.__name__} is currently full"
            raise CuckooFilterFullError(msg)

    def _calc_error_rate(self):
        """calculate error rate based on fingerprint size (bits) and bucket size"""
        return float(1 / (2 ** (self.fingerprint_size_bits - (math.log2(self.bucket_size) + 1))))

    def _calc_fingerprint_size(self) -> int:
        """calculate fingerprint size (bits) based on error rate and bucket size"""
        return int(math.ceil(-math.log2(self.error_rate) + math.log2(self.bucket_size) + 1))
