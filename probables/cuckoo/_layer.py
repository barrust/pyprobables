"""A single, fixed size cuckoo filter table

License: MIT
Author: Tyler Barrus (barrust@gmail.com)
"""

import random
import sys
from array import array

# 0 marks an empty slot, so fingerprints are always between 1 and 2^bits - 1
EMPTY = 0
MAX_FINGERPRINT_BITS = 32
_GOLDEN_64 = 0x9E3779B97F4A7C15
_MASK_64 = (1 << 64) - 1
_NEEDS_BYTESWAP = sys.byteorder != "little"


def _unsigned_typecode(size: int) -> str:
    """str: the array typecode for an unsigned integer of `size` bytes"""
    for code in ("B", "H", "I", "L", "Q"):
        if array(code).itemsize == size:
            return code
    raise RuntimeError(f"No unsigned {size} byte array type on this platform")  # pragma: no cover


_TYPECODES = {size: _unsigned_typecode(size) for size in (1, 2, 4)}
COUNT_TYPECODE = _TYPECODES[4]


def fingerprint_bytes(bits: int) -> int:
    """int: bytes used to store a fingerprint of `bits` bits"""
    return 1 if bits <= 8 else 2 if bits <= 16 else 4


def fingerprint_hash(fingerprint: int) -> int:
    """int: a 32 bit hash of a fingerprint, used for the alternate bucket (Fibonacci hashing)"""
    return ((fingerprint * _GOLDEN_64) & _MASK_64) >> 32


def index_hash(hash_val: int) -> int:
    """int: the low 64 bits of a key's hash, mixed (splitmix64 finalizer), used for the first bucket

    Mixing every bit means the first bucket uses all of the hash: with a 64 bit hash it is independent
    of the fingerprint, and a shorter hash still spreads keys over every bucket."""
    z = hash_val & _MASK_64
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & _MASK_64
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & _MASK_64
    return z ^ (z >> 31)


class CuckooLayer:
    """A fixed size cuckoo table using partial-key cuckoo hashing (Fan et al. 2014)

    The fingerprint is the low `fingerprint_bits` bits of the key's hash, the first bucket comes from
    a mix of the whole hash (`index_hash`), and the second bucket is `(H(fp) - i1) % capacity`. The
    second bucket can be computed from either bucket and the fingerprint, which is what lets entries
    be kicked between buckets without the original key.

    Args:
        capacity (int): The number of buckets
        bucket_size (int): The number of slots per bucket
        fingerprint_bits (int): The size of the fingerprint in bits, between 1 and 32
        counting (bool): Keep a count with each fingerprint"""

    __slots__ = ("capacity", "bucket_size", "fingerprint_bits", "_mask", "slots", "counts")

    def __init__(self, capacity: int, bucket_size: int, fingerprint_bits: int, counting: bool = False) -> None:
        if capacity < 1 or bucket_size < 1 or not 1 <= fingerprint_bits <= MAX_FINGERPRINT_BITS:
            raise ValueError("Invalid cuckoo layer parameters")
        self.capacity = capacity
        self.bucket_size = bucket_size
        self.fingerprint_bits = fingerprint_bits
        self._mask = (1 << fingerprint_bits) - 1
        num_slots = capacity * bucket_size
        self.slots = array(_TYPECODES[fingerprint_bytes(fingerprint_bits)], [EMPTY]) * num_slots
        self.counts = array(COUNT_TYPECODE, [0]) * num_slots if counting else None

    @property
    def num_slots(self) -> int:
        """int: the total number of slots"""
        return self.capacity * self.bucket_size

    def locate(self, hash_val: int, mixed: int | None = None) -> tuple[int, int, int]:
        """Get the fingerprint and both buckets for a key's hash

        Args:
            hash_val (int): The hash of the key
            mixed (int): `index_hash(hash_val)`, if already computed
        Returns:
            tuple(int, int, int): The fingerprint, the first bucket, and the second bucket"""
        fingerprint = (hash_val & self._mask) or 1
        idx_1 = (index_hash(hash_val) if mixed is None else mixed) % self.capacity
        return fingerprint, idx_1, (fingerprint_hash(fingerprint) - idx_1) % self.capacity

    def alternate(self, idx: int, fingerprint: int) -> int:
        """int: the other bucket for a fingerprint in bucket `idx`"""
        return (fingerprint_hash(fingerprint) - idx) % self.capacity

    def find(self, fingerprint: int, idx_1: int, idx_2: int) -> int:
        """int: the slot holding `fingerprint` in either bucket, or -1"""
        # most lookups miss, and `in` on a slice is faster than catching index()'s ValueError
        slots, size = self.slots, self.bucket_size
        for start in (idx_1 * size, idx_2 * size):
            end = start + size
            if fingerprint in slots[start:end]:
                return slots.index(fingerprint, start, end)
        return -1

    def _empty_slot(self, idx: int) -> int:
        """int: an empty slot in bucket `idx`, or -1"""
        # most buckets have room, and index() alone is faster when it finds one
        start = idx * self.bucket_size
        try:
            return self.slots.index(EMPTY, start, start + self.bucket_size)
        except ValueError:
            return -1

    def _put(self, slot: int, fingerprint: int, count: int) -> None:
        self.slots[slot] = fingerprint
        if self.counts is not None:
            self.counts[slot] = count

    def place(self, fingerprint: int, idx_1: int, idx_2: int, count: int = 1) -> bool:
        """Put the fingerprint in an empty slot of either bucket, without moving others

        Returns:
            bool: True if placed"""
        for idx in (idx_1, idx_2):
            slot = self._empty_slot(idx)
            if slot != -1:
                self._put(slot, fingerprint, count)
                return True
        return False

    def insert(self, fingerprint: int, idx_1: int, idx_2: int, max_swaps: int, count: int = 1) -> bool:
        """Insert the fingerprint, kicking other fingerprints to their alternate buckets if needed

        If it cannot be placed within `max_swaps` kicks, every kick is undone and the layer is
        unchanged.

        Returns:
            bool: True if inserted"""
        if self.place(fingerprint, idx_1, idx_2, count):
            return True
        slots, counts, size = self.slots, self.counts, self.bucket_size
        idx = random.choice((idx_1, idx_2))
        kicks = []
        for _ in range(max_swaps):
            slot = idx * size + random.randrange(size)
            old_count = counts[slot] if counts is not None else 1
            kicks.append((slot, slots[slot], old_count))
            fingerprint, slots[slot] = slots[slot], fingerprint
            if counts is not None:
                count, counts[slot] = old_count, count
            idx = self.alternate(idx, fingerprint)
            empty = self._empty_slot(idx)
            if empty != -1:
                self._put(empty, fingerprint, count)
                return True
        for slot, old_fingerprint, old_count in reversed(kicks):
            self._put(slot, old_fingerprint, old_count)
        return False

    def clear(self, slot: int) -> None:
        """Empty a slot"""
        self._put(slot, EMPTY, 0)

    def bucket(self, idx: int) -> list[tuple[int, int]]:
        """list(tuple(int, int)): the (fingerprint, count) pairs stored in bucket `idx`"""
        start = idx * self.bucket_size
        end = start + self.bucket_size
        fingerprints = self.slots[start:end]
        counts = self.counts[start:end] if self.counts is not None else [1] * self.bucket_size
        return [(fp, count) for fp, count in zip(fingerprints, counts, strict=True) if fp != EMPTY]

    def occupied(self) -> int:
        """int: the number of non-empty slots"""
        return self.num_slots - self.slots.count(EMPTY)

    def total_count(self) -> int:
        """int: the sum of the counts (or the number of entries if not counting)"""
        if self.counts is None:
            return self.occupied()
        return sum(self.counts)

    def to_bytes(self) -> bytes:
        """bytes: the slots, then the counts if counting, as little-endian unsigned integers"""
        out = [_little_endian(self.slots)]
        if self.counts is not None:
            out.append(_little_endian(self.counts))
        return b"".join(out)

    @staticmethod
    def size_in_bytes(capacity: int, bucket_size: int, fingerprint_bits: int, counting: bool) -> int:
        """int: the size of `to_bytes()` for a layer with these parameters"""
        per_slot = fingerprint_bytes(fingerprint_bits) + (array(COUNT_TYPECODE).itemsize if counting else 0)
        return capacity * bucket_size * per_slot

    def byte_size(self) -> int:
        """int: the size of `to_bytes()`"""
        return self.size_in_bytes(self.capacity, self.bucket_size, self.fingerprint_bits, self.counts is not None)

    def load_bytes(self, data) -> None:
        """Load slots (and counts) from the output of `to_bytes()`

        Raises:
            ValueError: If the data is invalid"""
        if len(data) != self.byte_size():
            raise ValueError("cuckoo layer data has the wrong size")
        split = self.num_slots * self.slots.itemsize
        self.slots = _from_little_endian(self.slots.typecode, data[:split])
        if any(fp > self._mask for fp in self.slots):
            raise ValueError("cuckoo layer holds a fingerprint wider than the layer")
        if self.counts is not None:
            self.counts = _from_little_endian(self.counts.typecode, data[split:])
            for fp, count in zip(self.slots, self.counts, strict=True):
                if (fp == EMPTY) != (count == 0):
                    raise ValueError("cuckoo layer counts do not match its slots")


def _little_endian(values: array) -> bytes:
    if _NEEDS_BYTESWAP:  # pragma: no cover
        values = array(values.typecode, values)
        values.byteswap()
    return values.tobytes()


def _from_little_endian(typecode: str, data) -> array:
    values = array(typecode)
    values.frombytes(data)
    if _NEEDS_BYTESWAP:  # pragma: no cover
        values.byteswap()
    return values
