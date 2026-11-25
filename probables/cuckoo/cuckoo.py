"""Layered cuckoo filter with packed fingerprints."""

import math
from collections.abc import ByteString, Callable
from hashlib import blake2b
from io import BytesIO, IOBase
from mmap import mmap
from numbers import Number
from pathlib import Path
from struct import Struct, error as StructError

from probables.cuckoo._packed_layer import PackedCuckooLayer
from probables.exceptions import CuckooFilterFullError, InitializationError
from probables.hashes import KeyT, fnv_1a
from probables.utilities import MMap, is_valid_file, resolve_path


class CuckooFilter:
    """Set-like, probabilistic cuckoo filter with packed, expanding layers.

    Fingerprint collisions can cause an insertion to be treated as a duplicate
    and deletion to remove another key. Only remove keys known to be present.
    Filters exported by earlier releases must be rebuilt from original keys.

    Args:
        capacity (int): Initial number of buckets.
        bucket_size (int): Number of slots per bucket.
        max_swaps (int): Maximum kicks per insertion.
        expansion_rate (int): Multiplier for new layer capacity.
        auto_expand (bool): Add a layer when insertion fails.
        finger_size (int): Initial fingerprint size in bytes, from 1 to 4.
        filepath (str | Path | None): Path to a saved filter.
        hash_function: Stable, well-distributed 64-bit hash function.
    """

    __slots__ = (
        "_bucket_size",
        "__max_cuckoo_swaps",
        "__expansion_rate",
        "__auto_expand",
        "__hash_func",
        "_inserted_elements",
        "_unique_elements",
        "_layers",
        "_error_rate",
    )

    _FORMAT_MAGIC = b"PYCKOO\x02\x00"
    _FORMAT_HEADER = Struct("<8sBIIdI")
    _FORMAT_LAYER = Struct("<IB")
    _MAX_BITS = 64

    def __init__(
        self,
        capacity: int = 10000,
        bucket_size: int = 4,
        max_swaps: int = 500,
        expansion_rate: int = 2,
        auto_expand: bool = True,
        finger_size: int = 4,
        filepath: str | Path | None = None,
        hash_function: Callable[[KeyT], int] | None = None,
    ):
        valid = all(isinstance(v, Number) and v >= 1 for v in (capacity, bucket_size, max_swaps))
        if not valid:
            raise InitializationError(
                "CuckooFilter: capacity, bucket_size, and max_swaps must be an integer greater than 0"
            )
        if not isinstance(finger_size, int) or not 1 <= finger_size <= 4:
            raise ValueError(f"{self.__class__.__name__}: fingerprint size must be between 1 and 4")
        self._bucket_size = int(bucket_size)
        self.__max_cuckoo_swaps = int(max_swaps)
        self.expansion_rate = expansion_rate
        self.auto_expand = auto_expand
        self.__hash_func = hash_function if hash_function is not None else fnv_1a
        self._inserted_elements = 0
        self._unique_elements = 0
        self._layers = [PackedCuckooLayer(int(capacity), self.bucket_size, finger_size * 8, self._counting)]
        self._error_rate = self._budget_for_bits(finger_size * 8)
        if filepath is not None:
            if not is_valid_file(filepath):
                raise InitializationError("CuckooFilter: failed to load provided file")
            self._load(resolve_path(filepath))

    @classmethod
    def init_error_rate(
        cls,
        error_rate: float,
        capacity: int = 10000,
        bucket_size: int = 4,
        max_swaps: int = 500,
        expansion_rate: int = 2,
        auto_expand: bool = True,
        hash_function: Callable[[KeyT], int] | None = None,
    ):
        """Create a filter with a total theoretical false-positive budget."""
        instance = cls(capacity, bucket_size, max_swaps, expansion_rate, auto_expand, hash_function=hash_function)
        instance._set_error_rate(error_rate)
        return instance

    @classmethod
    def load_error_rate(
        cls, error_rate: float, filepath: str | Path, hash_function: Callable[[KeyT], int] | None = None
    ):
        """Load a filter, verifying its stored error-rate target."""
        instance = cls(filepath=filepath, hash_function=hash_function)
        instance._check_loaded_error_rate(error_rate)
        return instance

    @classmethod
    def frombytes(
        cls, b: ByteString, error_rate: float | None = None, hash_function: Callable[[KeyT], int] | None = None
    ):
        """Load an exported filter; the original hash function must be supplied."""
        instance = cls(hash_function=hash_function)
        instance._load(b)
        if error_rate is not None:
            instance._check_loaded_error_rate(error_rate)
        return instance

    def __contains__(self, key: KeyT) -> bool:
        return bool(self.check(key))

    def __str__(self):
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
        return False

    @property
    def elements_added(self) -> int:
        """Number of stored entries, or total additions for a counting filter."""
        return self._inserted_elements

    @property
    def capacity(self) -> int:
        """Total number of buckets across all layers."""
        return sum(layer.capacity for layer in self._layers)

    @property
    def bucket_size(self) -> int:
        return self._bucket_size

    @property
    def max_swaps(self) -> int:
        return self.__max_cuckoo_swaps

    @property
    def buckets(self) -> list:
        """Snapshot of buckets, ordered by layer; changing it does not change the filter."""
        return [
            [
                self._display_entry(layer, pos)
                for pos in range(i * self.bucket_size, (i + 1) * self.bucket_size)
                if layer.is_occupied(pos)
            ]
            for layer in self._layers
            for i in range(layer.capacity)
        ]

    def _display_entry(self, layer: PackedCuckooLayer, slot: int):
        return layer.fingerprint(slot)

    @property
    def expansion_rate(self) -> int:
        return self.__expansion_rate

    @expansion_rate.setter
    def expansion_rate(self, val: int):
        if not isinstance(val, int) or val <= 1:
            raise ValueError("Cuckoo filter expansion rate must be an integer greater than 1")
        self.__expansion_rate = val

    @property
    def auto_expand(self) -> bool:
        return self.__auto_expand

    @auto_expand.setter
    def auto_expand(self, val: bool):
        self.__auto_expand = bool(val)

    @property
    def error_rate(self) -> float:
        """The aggregate target under the uniform-hashing model."""
        return self._error_rate

    @property
    def fingerprint_size_bits(self) -> int:
        """Fingerprint width of the first layer; later layers use more bits."""
        return self._layers[0].fingerprint_bits

    @property
    def fingerprint_size(self) -> int:
        return math.ceil(self.fingerprint_size_bits / 8)

    @fingerprint_size.setter
    def fingerprint_size(self, val: int):
        if not isinstance(val, int) or not 1 <= val <= 4:
            raise ValueError(f"{self.__class__.__name__}: fingerprint size must be between 1 and 4")
        if self._inserted_elements or len(self._layers) != 1:
            raise ValueError("Cannot change fingerprint size on a non-empty or expanded cuckoo filter")
        self._layers = [PackedCuckooLayer(self.capacity, self.bucket_size, val * 8, self._counting)]
        self._error_rate = self._budget_for_bits(val * 8)

    def _budget_for_bits(self, bits: int) -> float:
        return math.ldexp(float(4 * self.bucket_size), -bits)

    def _set_error_rate(self, error_rate: float):
        if not 0 < error_rate < 1:
            raise ValueError("Cuckoo filter error rate must be between 0 and 1")
        bits = max(1, min(self._MAX_BITS, math.ceil(-math.log2(error_rate) + math.log2(self.bucket_size) + 2)))
        while bits > 1 and self._budget_for_bits(bits - 1) <= error_rate:
            bits -= 1
        while bits < self._MAX_BITS and self._budget_for_bits(bits) > error_rate:
            bits += 1
        if self._budget_for_bits(bits) > error_rate:
            raise ValueError("Cuckoo filter error rate requires more than 64 fingerprint bits")
        if self._inserted_elements or len(self._layers) != 1:
            if error_rate != self._error_rate:
                raise ValueError("Error rate does not match the stored cuckoo filter")
            return
        self._layers = [PackedCuckooLayer(self.capacity, self.bucket_size, bits, self._counting)]
        self._error_rate = error_rate

    def _check_loaded_error_rate(self, error_rate: float) -> None:
        if error_rate != self._error_rate:
            raise ValueError("Error rate does not match the stored cuckoo filter")

    def load_factor(self) -> float:
        return self._unique_elements / (self.capacity * self.bucket_size)

    def _key_hash(self, key: KeyT) -> int:
        return self.__hash_func(key) & ((1 << 64) - 1)

    def _alternate_index(self, idx: int, fingerprint: int, capacity: int | None = None) -> int:
        cap = self._layers[-1].capacity if capacity is None else capacity
        return (fnv_1a(str(fingerprint)) - idx) % cap

    def _fingerprint_info(self, layer: PackedCuckooLayer, key_hash: int, index_hash: int) -> tuple[int, int, int]:
        fingerprint = key_hash & ((1 << layer.fingerprint_bits) - 1)
        first = index_hash % layer.capacity
        return first, self._alternate_index(first, fingerprint, layer.capacity), fingerprint

    @staticmethod
    def _index_hash(key: KeyT) -> int:
        data = key.encode("utf-8", errors="surrogatepass") if isinstance(key, str) else key
        return int.from_bytes(blake2b(data, digest_size=8, person=b"pyprobables-idx").digest(), "little")

    def _generate_fingerprint_info(self, key: KeyT) -> tuple[int, int, int]:
        return self._fingerprint_info(self._layers[-1], self._key_hash(key), self._index_hash(key))

    def _find(self, key_hash: int, index_hash: int) -> tuple[PackedCuckooLayer, int] | None:
        for layer in self._layers:
            first, second, fingerprint = self._fingerprint_info(layer, key_hash, index_hash)
            slot = layer.find(fingerprint, first, second)
            if slot is not None:
                return layer, slot
        return None

    def _insert_entry(self, layer: PackedCuckooLayer, key_hash: int, index_hash: int) -> bool:
        first, second, fingerprint = self._fingerprint_info(layer, key_hash, index_hash)
        return layer.insert(
            fingerprint, first, second, lambda i, fp: self._alternate_index(i, fp, layer.capacity), self.max_swaps
        )

    def _new_layer(self) -> PackedCuckooLayer:
        last = self._layers[-1]
        bits = last.fingerprint_bits + 1
        if bits > self._MAX_BITS:
            raise CuckooFilterFullError("Cuckoo filter cannot expand beyond 64 fingerprint bits")
        return PackedCuckooLayer(last.capacity * self.expansion_rate, self.bucket_size, bits, self._counting)

    def expand(self):
        """Append an empty layer, preserving all existing entries."""
        self._layers.append(self._new_layer())

    def add(self, key: KeyT):
        """Add a key; an existing fingerprint match is treated as a duplicate."""
        key_hash = self._key_hash(key)
        index_hash = self._index_hash(key)
        if self._find(key_hash, index_hash) is not None:
            return
        if not self._insert_entry(self._layers[-1], key_hash, index_hash):
            if not self.auto_expand:
                raise CuckooFilterFullError(f"The {self.__class__.__name__} is currently full")
            layer = self._new_layer()
            if not self._insert_entry(layer, key_hash, index_hash):
                raise CuckooFilterFullError(f"The {self.__class__.__name__} failed to expand")
            self._layers.append(layer)
        self._unique_elements += 1
        self._inserted_elements += 1

    def check(self, key: KeyT) -> bool:
        return self._find(self._key_hash(key), self._index_hash(key)) is not None

    def remove(self, key: KeyT) -> bool:
        location = self._find(self._key_hash(key), self._index_hash(key))
        if location is None:
            return False
        layer, slot = location
        layer.clear(slot)
        self._unique_elements -= 1
        self._inserted_elements -= 1
        return True

    def export(self, file: Path | str | IOBase | mmap) -> None:
        """Write the versioned little-endian packed filter."""
        if not isinstance(file, IOBase | mmap):
            with open(resolve_path(file), "wb") as stream:
                self.export(stream)
            return
        file.write(
            self._FORMAT_HEADER.pack(
                self._FORMAT_MAGIC,
                int(self._counting),
                self.bucket_size,
                self.max_swaps,
                self.error_rate,
                len(self._layers),
            )
        )
        for layer in self._layers:
            file.write(self._FORMAT_LAYER.pack(layer.capacity, layer.fingerprint_bits))
            file.write(layer.occupied)
            file.write(layer.fingerprints)
            if layer.counts is not None:
                file.write(layer.counts)

    def __bytes__(self) -> bytes:
        with BytesIO() as stream:
            self.export(stream)
            return stream.getvalue()

    def _load(self, file: Path | str | IOBase | mmap | bytes | ByteString) -> None:
        if not isinstance(file, IOBase | mmap | bytes | bytearray | memoryview):
            with MMap(resolve_path(file)) as stream:
                self._load(stream)
            return
        data = file.read() if isinstance(file, IOBase) else file
        if bytes(data[:8]) != self._FORMAT_MAGIC:
            raise InitializationError(
                "Unsupported cuckoo filter format; filters exported by older pyprobables releases "
                "must be used with an older release or rebuilt from the original keys"
            )
        try:
            magic, kind, bucket_size, max_swaps, error_rate, layer_count = self._FORMAT_HEADER.unpack_from(data)
            if (
                magic != self._FORMAT_MAGIC
                or kind != int(self._counting)
                or not bucket_size
                or not max_swaps
                or not math.isfinite(error_rate)
                or error_rate <= 0
                or not layer_count
            ):
                raise ValueError("invalid cuckoo filter header")
            offset = self._FORMAT_HEADER.size
            layers = []
            total, unique = 0, 0
            for _ in range(layer_count):
                capacity, bits = self._FORMAT_LAYER.unpack_from(data, offset)
                offset += self._FORMAT_LAYER.size
                if not capacity or not 1 <= bits <= self._MAX_BITS:
                    raise ValueError("invalid cuckoo layer")
                if layers and bits != layers[-1].fingerprint_bits + 1:
                    raise ValueError("invalid cuckoo layer sequence")
                slots = capacity * bucket_size
                occ_size = (slots + 7) // 8
                fp_size = slots * ((bits + 7) // 8)
                count_size = slots * 4 if self._counting else 0
                end = offset + occ_size + fp_size + count_size
                if end > len(data):
                    raise ValueError("truncated cuckoo layer")
                layer = PackedCuckooLayer(capacity, bucket_size, bits, self._counting)
                layer.occupied[:] = data[offset : offset + occ_size]
                offset += occ_size
                layer.fingerprints[:] = data[offset : offset + fp_size]
                offset += fp_size
                if layer.counts is not None:
                    layer.counts[:] = data[offset:end]
                offset = end
                if slots % 8 and layer.occupied[-1] >> (slots % 8):
                    raise ValueError("invalid occupancy padding")
                for slot in range(slots):
                    if layer.is_occupied(slot):
                        if layer.fingerprint(slot) >= 1 << bits or not layer.count(slot):
                            raise ValueError("invalid cuckoo entry")
                        unique += 1
                        total += layer.count(slot)
                    elif layer.fingerprint(slot) or (layer.counts is not None and layer.count(slot)):
                        raise ValueError("nonempty vacant slot")
                layers.append(layer)
            if offset != len(data):
                raise ValueError("invalid cuckoo filter length")
            if self._budget_for_loaded_bits(bucket_size, layers[0].fingerprint_bits) > error_rate:
                raise ValueError("fingerprint width exceeds error budget")
        except (StructError, ValueError, OverflowError) as exc:
            raise InitializationError(f"Invalid cuckoo filter data: {exc}") from exc
        self._bucket_size = bucket_size
        self.__max_cuckoo_swaps = max_swaps
        self._error_rate = error_rate
        self._layers = layers
        self._unique_elements = unique
        self._inserted_elements = total

    @staticmethod
    def _budget_for_loaded_bits(bucket_size: int, bits: int) -> float:
        return math.ldexp(float(4 * bucket_size), -bits)
