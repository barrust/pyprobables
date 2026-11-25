"""Counting cuckoo filter with packed fingerprints and counts."""

from array import array

from probables.cuckoo._packed_layer import PackedCuckooLayer
from probables.cuckoo.cuckoo import CuckooFilter
from probables.hashes import KeyT


class CountingCuckooFilter(CuckooFilter):
    """Cuckoo filter tracking counts of matching fingerprints.

    Colliding keys share a count, and removing a false positive can modify
    another key. Only remove keys known to have been inserted.
    """

    __slots__ = ()

    @property
    def _counting(self) -> bool:
        return True

    @property
    def unique_elements(self) -> int:
        """Number of stored fingerprints, not necessarily distinct keys."""
        return self._unique_elements

    def _display_entry(self, layer: PackedCuckooLayer, slot: int):
        return CountingCuckooBin(layer.fingerprint(slot), layer.count(slot))

    def add(self, key: KeyT) -> None:
        key_hash = self._key_hash(key)
        location = self._find(key_hash, self._index_hash(key))
        if location is not None:
            layer, slot = location
            layer.put(slot, layer.fingerprint(slot), layer.count(slot) + 1)
            self._inserted_elements += 1
            return
        super().add(key)

    def check(self, key: KeyT) -> int:  # type: ignore[override]
        location = self._find(self._key_hash(key), self._index_hash(key))
        if location is None:
            return 0
        layer, slot = location
        return layer.count(slot)

    def remove(self, key: KeyT) -> bool:
        location = self._find(self._key_hash(key), self._index_hash(key))
        if location is None:
            return False
        layer, slot = location
        count = layer.count(slot)
        if count == 1:
            layer.clear(slot)
            self._unique_elements -= 1
        else:
            layer.put(slot, layer.fingerprint(slot), count - 1)
        self._inserted_elements -= 1
        return True


class CountingCuckooBin:
    """Snapshot of a counting cuckoo bucket entry."""

    __slots__ = ("__bin",)

    def __init__(self, fingerprint: int, count: int) -> None:
        self.__bin = array("Q", [fingerprint, count])

    def __contains__(self, val: int) -> bool:
        return self.finger == val

    def get_array(self):
        return self.__bin

    @property
    def finger(self) -> int:
        return self.__bin[0]

    @property
    def count(self) -> int:
        return self.__bin[1]

    def __repr__(self):
        return str(self)

    def __str__(self):
        return f"(fingerprint:{self.finger} count:{self.count})"

    def increment(self) -> int:
        self.__bin[1] += 1
        return self.__bin[1]

    def decrement(self) -> int:
        self.__bin[1] -= 1
        return self.__bin[1]
