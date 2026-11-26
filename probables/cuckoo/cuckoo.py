"""Cuckoo Filter, python implementation
License: MIT
Author: Tyler Barrus (barrust@gmail.com)
"""

import math
from collections.abc import ByteString, Callable, Sequence
from io import BytesIO, IOBase
from mmap import mmap
from numbers import Number
from pathlib import Path
from struct import Struct
from struct import error as StructError
from typing import Any

from probables.cuckoo._layer import MAX_FINGERPRINT_BITS, CuckooLayer, index_hash
from probables.exceptions import CuckooFilterFullError, InitializationError
from probables.hashes import KeyT, SimpleHashT, fnv_1a
from probables.utilities import is_valid_file, resolve_path


class CuckooFilter:
    """Simple Cuckoo Filter implementation

    Fingerprints are stored in compact arrays and placed with partial-key cuckoo hashing as
    described by Fan et al. (2014). When the filter is full it can expand by adding a larger table
    with a one bit longer fingerprint, so that `error_rate` bounds the false positive rate of the
    whole filter.

    Args:
        capacity (int): The number of bins
        bucket_size (int): The number of buckets per bin
        max_swaps (int): The number of cuckoo swaps before stopping
        expansion_rate (int): The rate at which to expand; an integer greater than 1
        auto_expand (bool): If the filter should automatically expand
        finger_size (int): The size of the fingerprint to use in bytes (between 1 and 4)
        filepath (str): The path to the file to load or None if no file
        hash_function (function): Hashing strategy function to use `hf(key)`; a 64 bit hash, like \
            the default, keeps the buckets independent of the fingerprint
    Returns:
        CuckooFilter: A Cuckoo Filter object
    Note:
        Adding a key whose fingerprint is already stored in one of its buckets does nothing, so two
        different keys can share an entry (as often as a false positive) and removing one of them
        removes the other. Only remove keys that were added."""

    __slots__ = (
        "_bucket_size",
        "__max_cuckoo_swaps",
        "__expansion_rate",
        "__auto_expand",
        "__hash_func",
        "_layers",
        "_error_rate",
        "_inserted_elements",
        "_unique_elements",
    )

    # header: magic, format version, counting, bucket_size, max_swaps, error_rate, number of layers
    _HEADER = Struct("<4sBBIIdI")
    _LAYER_HEADER = Struct("<QB")  # capacity, fingerprint bits
    _MAGIC = b"PCKF"
    _VERSION = 1

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
        self._configure(capacity, bucket_size, max_swaps, expansion_rate, auto_expand, hash_function)
        if not isinstance(finger_size, int) or not 1 <= finger_size <= 4:
            msg = f"{self.__class__.__name__}: fingerprint size must be between 1 and 4"
            raise ValueError(msg)
        if filepath is not None:
            if not is_valid_file(filepath):
                msg = f"{self.__class__.__name__}: failed to load provided file"
                raise InitializationError(msg)
            self._load(resolve_path(filepath))
            return
        self._layers = [self._new_layer(int(capacity), finger_size * 8)]
        self._error_rate = self._calc_error_rate(finger_size * 8)

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
            error_rate (float): The upper bound on the false positive rate of the whole filter, \
                including any expansions
            capacity (int): The number of bins
            bucket_size (int): The number of buckets per bin
            max_swaps (int): The number of cuckoo swaps before stopping
            expansion_rate (int): The rate at which to expand
            auto_expand (bool): If the filter should automatically expand
            hash_function (function): Hashing strategy function to use `hf(key)`
        Returns:
            CuckooFilter: A Cuckoo Filter object
        Raises:
            InitializationError: If the error rate is not between 0 and 1 or needs a fingerprint \
                longer than 32 bits"""
        cku = cls.__new__(cls)
        cku._configure(capacity, bucket_size, max_swaps, expansion_rate, auto_expand, hash_function)
        cku._layers = [cku._new_layer(int(capacity), cku._fingerprint_bits_for(error_rate))]
        cku._error_rate = float(error_rate)
        return cku

    @classmethod
    def load_error_rate(cls, error_rate: float, filepath: str | Path, hash_function: SimpleHashT | None = None):
        """Initialize a previously exported Cuckoo Filter based on error rate

        Args:
            error_rate (float): The error rate the filter was created with
            filepath (str): The path to the file to load
            hash_function (function): Hashing strategy function to use `hf(key)`
        Returns:
            CuckooFilter: A Cuckoo Filter object
        Raises:
            InitializationError: If `error_rate` is not the error rate stored in the file"""
        cku = cls(filepath=resolve_path(filepath), hash_function=hash_function)
        cku._check_error_rate(error_rate)
        return cku

    @classmethod
    def frombytes(cls, b: ByteString, error_rate: float | None = None, hash_function: SimpleHashT | None = None):
        """
        Args:
            b (ByteString): The bytes to load as a Cuckoo Filter
            error_rate (float): The error rate of the cuckoo filter, if used to generate the original filter
            hash_function (function): Hashing strategy function to use `hf(key)`
        Returns:
            CuckooFilter: A Cuckoo Filter object
        Raises:
            InitializationError: If the bytes are not an exported filter of this type, or \
                `error_rate` is not the error rate stored in it"""
        cku = cls.__new__(cls)
        cku._configure(hash_function=hash_function)
        cku._load(b)
        if error_rate is not None:
            cku._check_error_rate(error_rate)
        return cku

    def __contains__(self, key: KeyT) -> bool:
        """setup the `in` keyword"""
        return bool(self.check(key))

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
    def _counting(self) -> bool:
        """bool: if the layers keep a count with each fingerprint"""
        return False

    @property
    def elements_added(self) -> int:
        """int: The number of elements added

        Note:
            Not settable"""
        return self._inserted_elements

    @property
    def capacity(self) -> int:
        """int: The number of bins, across all layers

        Note:
            Not settable"""
        return sum(layer.capacity for layer in self._layers)

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
    def buckets(self) -> Sequence[list[int]]:
        """Sequence(list): A read-only view of the fingerprints in each bin, layer by layer

        Note:
            Not settable; each bin is built when it is accessed, and changing it does not change the filter"""
        return BucketsView(self._layers, lambda fingerprint, _: fingerprint)

    @property
    def layers(self) -> int:
        """int: The number of tables; 1 plus the number of expansions

        Note:
            Not settable"""
        return len(self._layers)

    @property
    def expansion_rate(self) -> int:
        """int: The rate at expansion when the filter grows"""
        return self.__expansion_rate

    @expansion_rate.setter
    def expansion_rate(self, val: int):
        """set the self expand value"""
        self.__expansion_rate = self._valid_expansion_rate(val, ValueError)

    @property
    def error_rate(self) -> float:
        """float: The upper bound on the false positive rate of the filter, including expansions

        Note:
            Each table has a bound of `2b / 2^f` (Fan et al. 2014) for bucket size `b` and
            fingerprint size `f` bits. Every expansion adds a table with a one bit longer
            fingerprint, so the bounds sum to less than `4b / 2^f` of the first table. Fingerprints
            stop growing at 32 bits; past that each table adds `2b / 2^32`, and this is the larger
            of the rate the filter was created with and the sum of the tables' bounds."""
        bound = sum(2 * self.bucket_size / 2**layer.fingerprint_bits for layer in self._layers)
        return min(1.0, max(self._error_rate, bound))

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
        """int: The size in bits of the fingerprint in the first table; each expansion adds a bit"""
        return self._layers[0].fingerprint_bits

    @property
    def fingerprint_size(self) -> int:
        """int: The size in bytes of the fingerprint in the first table

        Raises:
            ValueError: If the size is not between 1 and 4, or the filter is not empty
        Note:
            The size of the fingerprint must be between 1 and 4"""
        return math.ceil(self.fingerprint_size_bits / 8)

    @fingerprint_size.setter
    def fingerprint_size(self, val: int):
        """set the fingerprint size"""
        if not isinstance(val, int) or not 1 <= val <= 4:
            msg = f"{self.__class__.__name__}: fingerprint size must be between 1 and 4"
            raise ValueError(msg)
        if len(self._layers) != 1 or self._unique_elements:
            msg = f"{self.__class__.__name__}: the fingerprint size can only be changed on an empty filter"
            raise ValueError(msg)
        self._layers = [self._new_layer(self._layers[0].capacity, val * 8)]
        self._error_rate = self._calc_error_rate(val * 8)

    def load_factor(self) -> float:
        """float: How full the Cuckoo Filter is currently"""
        return self._unique_elements / (self.capacity * self.bucket_size)

    def add(self, key: KeyT):
        """Add element key to the filter

        Args:
            key (str): The element to add
        Raises:
            CuckooFilterFullError: When element not inserted after maximum number of swaps or 'kicks'"""
        hash_val = self._key_hash(key)
        mixed = index_hash(hash_val)
        if self._find(hash_val, mixed) is not None:  # already there, nothing to do
            return
        self._insert(hash_val, mixed, 1)
        self._unique_elements += 1
        self._inserted_elements += 1

    def check(self, key: KeyT) -> bool:
        """Check if an element is in the filter

        Args:
            key (str): Element to check
        Returns:
            bool: True if likely present, False if definately not"""
        hash_val = self._key_hash(key)
        return self._find(hash_val, index_hash(hash_val)) is not None

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
        layer.clear(slot)
        self._unique_elements -= 1
        self._inserted_elements -= 1
        return True

    def expand(self):
        """Expand the cuckoo filter by adding a table; existing elements are kept where they are"""
        self._layers.append(self._next_layer())

    def export(self, file: Path | str | IOBase | mmap) -> None:
        """Export cuckoo filter to file

        Args:
            file: Path to file to export"""
        if not isinstance(file, IOBase | mmap):
            with open(resolve_path(file), "wb") as filepointer:
                self.export(filepointer)  # type: ignore
            return
        file.write(
            self._HEADER.pack(
                self._MAGIC,
                self._VERSION,
                int(self._counting),
                self.bucket_size,
                self.max_swaps,
                self._error_rate,
                len(self._layers),
            )
        )
        for layer in self._layers:
            file.write(self._LAYER_HEADER.pack(layer.capacity, layer.fingerprint_bits))
            file.write(layer.to_bytes())

    def __bytes__(self) -> bytes:
        """Export cuckoo filter to `bytes`"""
        with BytesIO() as f:
            self.export(f)
            return f.getvalue()

    def _configure(
        self,
        capacity: int = 10000,
        bucket_size: int = 4,
        max_swaps: int = 500,
        expansion_rate: int = 2,
        auto_expand: bool = True,
        hash_function: SimpleHashT | None = None,
    ) -> None:
        """validate and set everything but the tables"""
        valid_prms = (
            isinstance(capacity, Number)
            and capacity >= 1  # type: ignore
            and isinstance(bucket_size, Number)
            and bucket_size >= 1  # type: ignore
            and isinstance(max_swaps, Number)
            and max_swaps >= 1  # type: ignore
        )
        if not valid_prms:
            msg = f"{self.__class__.__name__}: capacity, bucket_size, and max_swaps must be an integer greater than 0"
            raise InitializationError(msg)
        self._bucket_size = int(bucket_size)
        self.__max_cuckoo_swaps = int(max_swaps)
        self.__expansion_rate = self._valid_expansion_rate(expansion_rate, InitializationError)
        self.__auto_expand = bool(auto_expand)
        self.__hash_func = fnv_1a if hash_function is None else hash_function
        self._inserted_elements = 0
        self._unique_elements = 0

    def _valid_expansion_rate(self, val: Any, error: type[Exception]) -> int:
        """int: `val` as an integer expansion rate, raising `error` if it is not a whole number above 1"""
        if (
            isinstance(val, bool)
            or not isinstance(val, int | float)
            or not math.isfinite(val)
            or val != int(val)
            or val < 2
        ):
            msg = f"{self.__class__.__name__}: expansion rate must be an integer greater than 1"
            raise error(msg)
        return int(val)

    def _key_hash(self, key: KeyT) -> int:
        """int: the hash of the key"""
        return self.__hash_func(key)  # type: ignore

    def _find(self, hash_val: int, mixed: int) -> tuple[CuckooLayer, int] | None:
        """Find the layer and slot holding the key's fingerprint, or None"""
        for layer in self._layers:
            fingerprint, idx_1, idx_2 = layer.locate(hash_val, mixed)
            slot = layer.find(fingerprint, idx_1, idx_2)
            if slot != -1:
                return layer, slot
        return None

    def _insert(self, hash_val: int, mixed: int, count: int) -> None:
        """Insert a key's fingerprint into the first table with room for it, expanding if allowed"""
        # reuse space freed by removals in older tables before kicking in the newest one
        for layer in self._layers[:-1]:
            if layer.place(*layer.locate(hash_val, mixed), count=count):
                return
        newest = self._layers[-1]
        if newest.insert(*newest.locate(hash_val, mixed), self.max_swaps, count):
            return
        if not self.auto_expand:
            msg = f"The {self.__class__.__name__} is currently full"
            raise CuckooFilterFullError(msg)
        layer = self._next_layer()
        if not layer.insert(*layer.locate(hash_val, mixed), self.max_swaps, count):  # pragma: no cover
            # an empty table always has room; kept so a failure can never lose the key silently
            msg = f"The {self.__class__.__name__} failed to expand"
            raise CuckooFilterFullError(msg)
        self._layers.append(layer)

    def _new_layer(self, capacity: int, fingerprint_bits: int) -> CuckooLayer:
        return CuckooLayer(capacity, self.bucket_size, fingerprint_bits, self._counting)

    def _next_layer(self) -> CuckooLayer:
        """CuckooLayer: an empty table that grows the total capacity by `expansion_rate`"""
        bits = min(self._layers[-1].fingerprint_bits + 1, MAX_FINGERPRINT_BITS)
        return self._new_layer(self.capacity * (self.expansion_rate - 1), bits)

    def _calc_error_rate(self, bits: int) -> float:
        """float: the bound on the false positive rate of all tables for a first table of `bits` bits"""
        return min(1.0, 4 * self.bucket_size / 2**bits)

    def _fingerprint_bits_for(self, error_rate: float) -> int:
        """int: the fingerprint bits of the first table needed for `error_rate`"""
        if not isinstance(error_rate, Number) or not 0 < error_rate < 1:  # type: ignore
            msg = f"{self.__class__.__name__}: error_rate must be between 0 and 1"
            raise InitializationError(msg)
        bits = max(1, math.ceil(math.log2(4 * self.bucket_size / error_rate)))
        if bits > MAX_FINGERPRINT_BITS:
            min_rate = self._calc_error_rate(MAX_FINGERPRINT_BITS)
            msg = (
                f"{self.__class__.__name__}: error_rate {error_rate} needs a {bits} bit fingerprint; the "
                f"maximum is {MAX_FINGERPRINT_BITS} bits (error_rate >= {min_rate:.3g} for bucket_size "
                f"{self.bucket_size})"
            )
            raise InitializationError(msg)
        return bits

    def _check_error_rate(self, error_rate: float) -> None:
        """verify that a loaded filter was created with `error_rate`"""
        if error_rate != self._error_rate:
            msg = (
                f"{self.__class__.__name__}: error_rate {error_rate} does not match the error rate "
                f"{self._error_rate} the filter was created with"
            )
            raise InitializationError(msg)

    def _load(self, file: Path | str | IOBase | mmap | ByteString) -> None:
        """load a cuckoo filter from file or bytes"""
        if not isinstance(file, IOBase | mmap | bytes | bytearray | memoryview):
            # read the file rather than memory-map it: the tables are copied into arrays anyway,
            # and a view into a mapping would keep it open if loading raises
            with open(resolve_path(file), "rb") as filepointer:  # type: ignore
                self._load(filepointer.read())
            return
        data = memoryview(file.read() if isinstance(file, IOBase) else file)  # type: ignore
        name = self.__class__.__name__
        try:
            header = self._HEADER.unpack_from(data)
        except StructError:
            header = None
        if header is None or header[0] != self._MAGIC:
            msg = (
                f"{name}: the data is not an exported cuckoo filter; filters exported before pyprobables "
                "0.8.0 use an incompatible layout and must be rebuilt from the original elements"
            )
            raise InitializationError(msg)
        _, version, counting, bucket_size, max_swaps, error_rate, num_layers = header
        try:
            if version != self._VERSION:
                raise ValueError(f"unsupported format version {version}")
            if counting != int(self._counting):
                kind = "a counting" if counting else "a non-counting"
                raise ValueError(f"the data is {kind} cuckoo filter")
            if bucket_size < 1 or max_swaps < 1 or num_layers < 1 or not 0 < error_rate <= 1:
                raise ValueError("invalid header")
            self._bucket_size = bucket_size
            offset = self._HEADER.size
            layers: list[CuckooLayer] = []
            for _ in range(num_layers):
                capacity, bits = self._LAYER_HEADER.unpack_from(data, offset)
                offset += self._LAYER_HEADER.size
                end = offset + CuckooLayer.size_in_bytes(capacity, bucket_size, bits, self._counting)
                if end > len(data):  # check before allocating the table
                    raise ValueError("the data is truncated")
                layer = self._new_layer(capacity, bits)
                layer.load_bytes(data[offset:end])
                layers.append(layer)
                offset = end
            if offset != len(data):
                raise ValueError("unexpected data after the last table")
        except (StructError, ValueError) as ex:
            msg = f"{name}: invalid cuckoo filter data: {ex}"
            raise InitializationError(msg) from ex
        self.__max_cuckoo_swaps = max_swaps
        self._error_rate = error_rate
        self._layers = layers
        self._unique_elements = sum(layer.occupied() for layer in layers)
        self._inserted_elements = sum(layer.total_count() for layer in layers)


class BucketsView(Sequence):
    """A read-only view of a cuckoo filter's bins, layer by layer; each bin is built when accessed

    Args:
        layers (list): The filter's tables
        entry (function): Builds the item for a `(fingerprint, count)` pair"""

    __slots__ = ("_layers", "_entry")

    def __init__(self, layers: list[CuckooLayer], entry: Callable[[int, int], Any]) -> None:
        self._layers = layers
        self._entry = entry

    def __len__(self) -> int:
        return sum(layer.capacity for layer in self._layers)

    def __getitem__(self, idx):  # type: ignore[override]
        if isinstance(idx, slice):
            return [self[i] for i in range(*idx.indices(len(self)))]
        if idx < 0:
            idx += len(self)
        if idx >= 0:
            for layer in self._layers:
                if idx < layer.capacity:
                    return [self._entry(fingerprint, count) for fingerprint, count in layer.bucket(idx)]
                idx -= layer.capacity
        raise IndexError("bucket index out of range")

    def __repr__(self) -> str:
        return repr(list(self))
