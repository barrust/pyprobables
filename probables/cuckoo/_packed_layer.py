"""Packed storage and cuckoo insertion for a single filter layer."""

import random


class PackedCuckooLayer:
    """A fixed-size table with packed fingerprints and an occupancy bitmap."""

    __slots__ = ("capacity", "bucket_size", "fingerprint_bits", "width", "fingerprints", "occupied", "counts")

    def __init__(self, capacity: int, bucket_size: int, fingerprint_bits: int, counting: bool = False):
        if capacity < 1 or bucket_size < 1 or not 1 <= fingerprint_bits <= 64:
            raise ValueError("Invalid cuckoo layer parameters")
        self.capacity = capacity
        self.bucket_size = bucket_size
        self.fingerprint_bits = fingerprint_bits
        self.width = (fingerprint_bits + 7) // 8
        slots = capacity * bucket_size
        self.fingerprints = bytearray(slots * self.width)
        self.occupied = bytearray((slots + 7) // 8)
        self.counts = bytearray(slots * 4) if counting else None

    def is_occupied(self, slot: int) -> bool:
        return bool(self.occupied[slot // 8] & (1 << (slot % 8)))

    def fingerprint(self, slot: int) -> int:
        start = slot * self.width
        return int.from_bytes(self.fingerprints[start : start + self.width], "little")

    def count(self, slot: int) -> int:
        if self.counts is None:
            return 1
        start = slot * 4
        return int.from_bytes(self.counts[start : start + 4], "little")

    def put(self, slot: int, fingerprint: int, count: int = 1) -> None:
        if not 0 <= fingerprint < 1 << self.fingerprint_bits:
            raise ValueError("Fingerprint does not fit in the layer")
        if not 1 <= count <= 0xFFFFFFFF:
            raise OverflowError("Cuckoo filter count must fit in an unsigned 32-bit integer")
        start = slot * self.width
        self.fingerprints[start : start + self.width] = fingerprint.to_bytes(self.width, "little")
        if self.counts is not None:
            start = slot * 4
            self.counts[start : start + 4] = count.to_bytes(4, "little")
        self.occupied[slot // 8] |= 1 << (slot % 8)

    def clear(self, slot: int) -> None:
        self.occupied[slot // 8] &= ~(1 << (slot % 8))
        start = slot * self.width
        self.fingerprints[start : start + self.width] = bytes(self.width)
        if self.counts is not None:
            start = slot * 4
            self.counts[start : start + 4] = bytes(4)

    def find(self, fingerprint: int, first: int, second: int) -> int | None:
        for bucket in (first, second):
            for slot in range(bucket * self.bucket_size, (bucket + 1) * self.bucket_size):
                if self.is_occupied(slot) and self.fingerprint(slot) == fingerprint:
                    return slot
        return None

    def insert(self, fingerprint: int, first: int, second: int, alternate, max_swaps: int, count: int = 1) -> bool:
        for bucket in (first, second):
            for slot in range(bucket * self.bucket_size, (bucket + 1) * self.bucket_size):
                if not self.is_occupied(slot):
                    self.put(slot, fingerprint, count)
                    return True
        bucket = random.choice((first, second))
        swaps = []
        try:
            for _ in range(max_swaps):
                slot = bucket * self.bucket_size + random.randrange(self.bucket_size)
                old_fingerprint, old_count = self.fingerprint(slot), self.count(slot)
                swaps.append((slot, old_fingerprint, old_count))
                self.put(slot, fingerprint, count)
                fingerprint, count = old_fingerprint, old_count
                bucket = alternate(bucket, fingerprint)
                for slot in range(bucket * self.bucket_size, (bucket + 1) * self.bucket_size):
                    if not self.is_occupied(slot):
                        self.put(slot, fingerprint, count)
                        return True
        except Exception:
            for slot, old_fingerprint, old_count in reversed(swaps):
                self.put(slot, old_fingerprint, old_count)
            raise
        for slot, old_fingerprint, old_count in reversed(swaps):
            self.put(slot, old_fingerprint, old_count)
        return False
