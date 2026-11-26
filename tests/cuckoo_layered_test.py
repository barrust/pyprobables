#!/usr/bin/env python
"""Tests for the cuckoo filter bucket layout, layered expansion, and export format"""

import os
import random
import sys
import unittest
from pathlib import Path
from tempfile import NamedTemporaryFile

this_dir = Path(__file__).parent
sys.path.insert(0, str(this_dir))
sys.path.insert(0, str(this_dir.parent))

from probables import (  # noqa: E402
    CountingCuckooFilter,
    CuckooFilter,
    CuckooFilterFullError,
    InitializationError,
)
from probables.cuckoo._layer import CuckooLayer  # noqa: E402
from probables.hashes import fnv_1a, fnv_1a_32  # noqa: E402

DELETE_TEMP_FILES = True


def random_keys(seed: int, count: int, prefix: str = "k") -> list[str]:
    rng = random.Random(seed)
    return [f"{prefix}{rng.getrandbits(64):016x}" for _ in range(count)]


def locate(cko: CuckooFilter, key: str) -> tuple[int, int, int]:
    """the fingerprint and buckets of a key in the first table"""
    return cko._layers[0].locate(cko._key_hash(key))


def same_fingerprint_pair(cko: CuckooFilter) -> tuple[str, str]:
    """find two keys with the same fingerprint in the first table"""
    seen: dict[int, str] = {}
    i = 0
    while True:
        key = f"user-{i}"
        fingerprint, _, _ = locate(cko, key)
        if fingerprint in seen:
            return seen[fingerprint], key
        seen[fingerprint] = key
        i += 1


class TestCuckooRegression(unittest.TestCase):
    """Regression tests: the buckets depended only on the fingerprint"""

    def test_same_fingerprint_different_buckets(self):
        """keys sharing a fingerprint should not share buckets or entries"""
        cko = CuckooFilter.init_error_rate(0.001)
        key_1, key_2 = same_fingerprint_pair(cko)
        info_1 = locate(cko, key_1)
        info_2 = locate(cko, key_2)
        self.assertEqual(info_1[0], info_2[0])
        self.assertNotEqual(info_1[1:], info_2[1:])

        cko.add(key_1)
        self.assertFalse(cko.check(key_2))
        cko.add(key_2)
        self.assertEqual(2, cko.elements_added)
        self.assertTrue(cko.remove(key_2))
        self.assertTrue(cko.check(key_1))

    def test_counting_same_fingerprint_separate_counts(self):
        """keys sharing a fingerprint should not share counts"""
        cko = CountingCuckooFilter.init_error_rate(0.001)
        key_1, key_2 = same_fingerprint_pair(cko)
        for _ in range(3):
            cko.add(key_1)
        self.assertEqual(0, cko.check(key_2))
        self.assertEqual(3, cko.check(key_1))

    def test_false_positive_rate(self):
        """the measured false positive rate should be below error_rate (was 0.46 here)"""
        cko = CuckooFilter.init_error_rate(0.001)
        for key in random_keys(1, 5000):
            cko.add(key)
        queries = random_keys(2, 50000, "q")
        rate = sum(cko.check(key) for key in queries) / len(queries)
        self.assertLess(rate, cko.error_rate)

    def test_false_positive_rate_after_expanding(self):
        """error_rate should bound the false positive rate after several expansions"""
        cko = CuckooFilter.init_error_rate(0.001, capacity=1000)
        for key in random_keys(3, 12000):
            cko.add(key)
        self.assertGreaterEqual(cko.layers, 3)
        queries = random_keys(4, 50000, "q")
        rate = sum(cko.check(key) for key in queries) / len(queries)
        self.assertLess(rate, cko.error_rate)

    def test_remove_keeps_other_keys(self):
        """removing keys should not remove other keys that were added (5.6% were lost)"""
        keys = random_keys(0, 2000)
        cko = CuckooFilter.init_error_rate(0.001)
        for key in keys:
            cko.add(key)
        # two different keys share an entry only if they share a fingerprint and a bucket pair,
        # about as often as a false positive
        self.assertGreaterEqual(cko.elements_added, 1998)
        for key in keys[:1000]:
            cko.remove(key)
        self.assertEqual(0, sum(not cko.check(key) for key in keys[1000:]))


class TestCuckooLayer(unittest.TestCase):
    """Tests for a single table"""

    def test_alternate_is_involution(self):
        """either bucket and the fingerprint give the other bucket"""
        layer = CuckooLayer(capacity=1003, bucket_size=4, fingerprint_bits=14)
        rng = random.Random(5)
        for _ in range(1000):
            fingerprint, idx_1, idx_2 = layer.locate(rng.getrandbits(64))
            self.assertTrue(1 <= fingerprint < 2**14)
            self.assertEqual(idx_2, layer.alternate(idx_1, fingerprint))
            self.assertEqual(idx_1, layer.alternate(idx_2, fingerprint))

    def test_fingerprint_never_empty(self):
        """a hash with zero fingerprint bits should not produce the empty marker"""
        layer = CuckooLayer(capacity=10, bucket_size=4, fingerprint_bits=8)
        fingerprint, _, _ = layer.locate(0xABCD00)
        self.assertEqual(1, fingerprint)

    def test_storage_width(self):
        """fingerprints use 1, 2, or 4 bytes per slot"""
        for bits, size in ((8, 1), (9, 2), (16, 2), (17, 4), (32, 4)):
            layer = CuckooLayer(capacity=10, bucket_size=4, fingerprint_bits=bits)
            self.assertEqual(size, layer.slots.itemsize)
            self.assertEqual(40 * size, len(layer.to_bytes()))

    def test_failed_insert_leaves_layer_unchanged(self):
        """a failed insert undoes its kicks"""
        self.addCleanup(random.setstate, random.getstate())
        random.seed(0)
        layer = CuckooLayer(capacity=2, bucket_size=1, fingerprint_bits=16, counting=True)
        self.assertTrue(layer.insert(5, 0, 1, max_swaps=10, count=3))
        self.assertTrue(layer.insert(6, 0, 1, max_swaps=10, count=4))
        before = (bytes(layer.slots), bytes(layer.counts))
        self.assertFalse(layer.insert(7, 0, 1, max_swaps=10))
        self.assertEqual(before, (bytes(layer.slots), bytes(layer.counts)))

    def test_little_endian_bytes(self):
        """exported slots are little-endian on every platform"""
        layer = CuckooLayer(capacity=1, bucket_size=2, fingerprint_bits=16)
        layer.place(0x0102, 0, 0)
        self.assertEqual(b"\x02\x01\x00\x00", layer.to_bytes())

    def test_invalid_layer(self):
        """invalid parameters raise"""
        self.assertRaises(ValueError, CuckooLayer, 0, 4, 8)
        self.assertRaises(ValueError, CuckooLayer, 10, 0, 8)
        self.assertRaises(ValueError, CuckooLayer, 10, 4, 33)


class TestCuckooLayers(unittest.TestCase):
    """Tests for expanding by adding tables"""

    def test_expand_capacity_and_bits(self):
        """each table grows the capacity by expansion_rate and the fingerprint by one bit"""
        cko = CuckooFilter.init_error_rate(0.001, capacity=100, expansion_rate=3)
        self.assertEqual(14, cko.fingerprint_size_bits)
        cko.expand()
        cko.expand()
        self.assertEqual(3, cko.layers)
        self.assertEqual(900, cko.capacity)
        self.assertEqual([100, 200, 600], [layer.capacity for layer in cko._layers])
        self.assertEqual([14, 15, 16], [layer.fingerprint_bits for layer in cko._layers])
        self.assertEqual(14, cko.fingerprint_size_bits)

    def test_fingerprint_bits_stop_at_32(self):
        """fingerprints do not grow past 32 bits"""
        cko = CuckooFilter(capacity=10)
        cko.expand()
        self.assertEqual([32, 32], [layer.fingerprint_bits for layer in cko._layers])

    def test_expand_keeps_elements(self):
        """elements stay where they are and new elements go to the new table"""
        cko = CuckooFilter(capacity=100)
        keys = [str(i) for i in range(200)]
        for key in keys[:100]:
            cko.add(key)
        cko.expand()
        for key in keys[100:]:
            cko.add(key)
        self.assertEqual(200, cko.elements_added)
        for key in keys:
            self.assertTrue(cko.check(key))

    def test_removed_space_reused(self):
        """space freed in an older table is used before kicking in the newest"""
        cko = CuckooFilter(capacity=100)
        keys = [str(i) for i in range(50)]
        for key in keys:
            cko.add(key)
        cko.expand()
        cko.remove(keys[0])
        cko.add(keys[0])
        self.assertEqual(50, cko._layers[0].occupied())
        self.assertEqual(0, cko._layers[1].occupied())

    def test_full_without_expanding(self):
        """a full filter without auto_expand raises and keeps its elements"""
        cko = CuckooFilter(capacity=10, bucket_size=2, max_swaps=10, auto_expand=False)
        added = []
        with self.assertRaises(CuckooFilterFullError):
            for i in range(100):
                cko.add(str(i))
                added.append(str(i))
        self.assertEqual(1, cko.layers)
        self.assertEqual(len(added), cko.elements_added)
        for key in added:
            self.assertTrue(cko.check(key))

    def test_expansion_rate_validation(self):
        """expansion rate must be a whole number greater than 1"""
        for rate in (1, 1.5, 0, True, float("inf"), float("nan"), "2"):
            self.assertRaises(InitializationError, CuckooFilter, expansion_rate=rate)
        self.assertEqual(3, CuckooFilter(expansion_rate=3.0).expansion_rate)
        cko = CuckooFilter()
        with self.assertRaises(ValueError):
            cko.expansion_rate = 0
        cko.expansion_rate = 4.0
        self.assertEqual(4, cko.expansion_rate)
        self.assertIsInstance(cko.expansion_rate, int)

    def test_fingerprint_size_on_non_empty(self):
        """the fingerprint size can only change on an empty filter"""
        cko = CuckooFilter()
        cko.fingerprint_size = 2
        self.assertEqual(16, cko.fingerprint_size_bits)
        self.assertEqual(16 / 2**16, cko.error_rate)
        cko.add("test")
        with self.assertRaises(ValueError):
            cko.fingerprint_size = 3

    def test_error_rate_validation(self):
        """error rates outside (0, 1) or needing more than 32 bits raise"""
        for error_rate in (0, 1, -0.1, 1e-10):
            self.assertRaises(InitializationError, CuckooFilter.init_error_rate, error_rate)
        self.assertEqual(32, CuckooFilter.init_error_rate(4e-9).fingerprint_size_bits)

    def test_buckets_is_a_copy(self):
        """changing buckets does not change the filter"""
        cko = CuckooFilter(capacity=10)
        cko.add("test")
        buckets = cko.buckets
        self.assertEqual(1, sum(len(bucket) for bucket in buckets))
        for bucket in buckets:
            bucket.clear()
        self.assertTrue(cko.check("test"))


class TestCuckooExport(unittest.TestCase):
    """Tests for the export format"""

    def _round_trip(self, cls):
        cko = cls.init_error_rate(0.001, capacity=50, max_swaps=100)
        keys = [f"key-{i}" for i in range(1000)]
        for key in keys:
            cko.add(key)
        cko.add(keys[7])
        self.assertGreater(cko.layers, 1)
        data = bytes(cko)

        cko2 = cls.frombytes(data, error_rate=0.001)
        self.assertEqual(data, bytes(cko2))
        self.assertEqual(cko.layers, cko2.layers)
        self.assertEqual(cko.capacity, cko2.capacity)
        self.assertEqual(cko.elements_added, cko2.elements_added)
        self.assertEqual(cko.load_factor(), cko2.load_factor())
        for key in keys:
            self.assertTrue(cko2.check(key))
        cko2.add("one more")
        self.assertTrue(cko2.check("one more"))
        return cko2

    def test_round_trip(self):
        """an expanded filter keeps every element through export and load"""
        self._round_trip(CuckooFilter)

    def test_counting_round_trip(self):
        """an expanded counting filter keeps every element and count through export and load"""
        cko = self._round_trip(CountingCuckooFilter)
        self.assertEqual(2, cko.check("key-7"))
        self.assertEqual(1001, cko.unique_elements)

    def test_load_file(self):
        """load_error_rate checks the stored error rate"""
        cko = CuckooFilter.init_error_rate(0.001)
        cko.add("test")
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".cko", delete=DELETE_TEMP_FILES) as fobj:
            cko.export(fobj.name)
            ckf = CuckooFilter.load_error_rate(0.001, fobj.name)
            self.assertTrue(ckf.check("test"))
            self.assertRaises(InitializationError, CuckooFilter.load_error_rate, 0.01, fobj.name)

    def test_zero_fingerprint_round_trip(self):
        """a key whose fingerprint bits are all 0 survives export and load (it was dropped)"""
        key = "z179"  # fnv_1a(key) ends in 8 zero bits
        self.assertEqual(0, fnv_1a(key) & 0xFF)
        for cls in (CuckooFilter, CountingCuckooFilter):
            cko = cls(capacity=100, finger_size=1)
            cko.add(key)
            cko2 = cls.frombytes(bytes(cko))
            self.assertTrue(cko2.check(key))
            self.assertEqual(1, cko2.elements_added)

    def test_compact_export(self):
        """14 bit fingerprints take 2 bytes per slot"""
        cko = CuckooFilter.init_error_rate(0.001)
        header = CuckooFilter._HEADER.size + CuckooFilter._LAYER_HEADER.size
        self.assertEqual(header + 10000 * 4 * 2, len(bytes(cko)))

    def test_invalid_data(self):
        """data that is not a valid export raises InitializationError"""
        cko = CuckooFilter(capacity=10)
        cko.add("test")
        data = bytes(cko)
        old_format = bytes(10 * 4 * 4) + bytes(8)  # buckets then (bucket_size, max_swaps)
        bad_version = data[:4] + b"\x09" + data[5:]
        bad_capacity = data[: CuckooFilter._HEADER.size] + b"\xff" * 8 + data[CuckooFilter._HEADER.size + 8 :]
        for bad in (b"", old_format, bad_version, data[:-1], data + b"\x00", bad_capacity):
            self.assertRaises(InitializationError, CuckooFilter.frombytes, bad)
        self.assertRaises(InitializationError, CountingCuckooFilter.frombytes, data)
        self.assertRaises(InitializationError, CuckooFilter.frombytes, bytes(CountingCuckooFilter(capacity=10)))
        self.assertRaises(InitializationError, CuckooFilter.frombytes, data, error_rate=0.5)

    def test_fingerprint_too_wide(self):
        """a stored fingerprint wider than its table raises"""
        layer = CuckooLayer(capacity=1, bucket_size=1, fingerprint_bits=9)
        self.assertRaises(ValueError, layer.load_bytes, (0x3FF).to_bytes(2, "little"))
        cko = CuckooFilter(capacity=1, bucket_size=1, finger_size=2)
        data = bytearray(bytes(cko))
        data[CuckooFilter._HEADER.size + 8] = 9  # first table: 9 bit fingerprints, 2 byte slots
        data[-2:] = (0x3FF).to_bytes(2, "little")
        self.assertRaises(InitializationError, CuckooFilter.frombytes, bytes(data))


class TestCuckooReviewFixes(unittest.TestCase):
    """Tests for issues found in code review"""

    def test_load_bad_file_raises_initialization_error(self):
        """a truncated or padded file raises InitializationError, not BufferError"""
        cko = CuckooFilter(capacity=10)
        cko.add("test")
        data = bytes(cko)
        for bad in (data[:-3], data + b"\x00"):
            with NamedTemporaryFile(dir=os.getcwd(), suffix=".cko", delete=DELETE_TEMP_FILES) as fobj:
                fobj.write(bad)
                fobj.flush()
                self.assertRaises(InitializationError, CuckooFilter, filepath=fobj.name)
                self.assertRaises(InitializationError, CuckooFilter.load_error_rate, cko.error_rate, fobj.name)

    def test_large_buckets_round_trip(self):
        """a filter whose error bound reaches 1 can be exported and loaded"""
        cko = CuckooFilter(capacity=10, bucket_size=64, finger_size=1)
        self.assertEqual(1.0, cko.error_rate)
        cko.add("test")
        cko2 = CuckooFilter.frombytes(bytes(cko))
        self.assertTrue(cko2.check("test"))
        self.assertEqual(1.0, cko2.error_rate)

    def test_32_bit_hash(self):
        """a 32 bit hash with 32 bit fingerprints still spreads keys over every bucket"""
        cko = CuckooFilter(capacity=1000, hash_function=fnv_1a_32)
        keys = [str(i) for i in range(3000)]
        for key in keys:
            cko.add(key)
        self.assertEqual(1, cko.layers)  # 75% full without expanding
        for key in keys:
            self.assertTrue(cko.check(key))
        first_buckets = {locate(cko, key)[1] for key in keys}
        self.assertGreater(len(first_buckets), 900)

    def test_error_rate_includes_32_bit_tables(self):
        """tables past 32 bits add to error_rate"""
        cko = CuckooFilter(capacity=10)
        initial = cko.error_rate
        self.assertEqual(16 / 2**32, initial)
        for _ in range(3):
            cko.expand()
        self.assertEqual(4 * 8 / 2**32, cko.error_rate)  # four 32 bit tables at 2b / 2^32 each
        self.assertEqual(initial, CuckooFilter.frombytes(bytes(cko))._error_rate)

    def test_counting_bin_mutators_deprecated(self):
        """changing a bin warns that it does not change the filter"""
        cko = CountingCuckooFilter(capacity=10)
        cko.add("a")
        (entry,) = next(bucket for bucket in cko.buckets if bucket)
        with self.assertWarns(DeprecationWarning):
            entry.increment()
        with self.assertWarns(DeprecationWarning):
            entry.decrement()
        self.assertEqual(1, cko.check("a"))

    def test_buckets_view(self):
        """buckets is a sequence over every table, built per access"""
        cko = CuckooFilter(capacity=10, bucket_size=2)
        cko.expand()
        cko.add("a")
        buckets = cko.buckets
        self.assertEqual(20, len(buckets))
        self.assertEqual(buckets[-1], buckets[19])
        self.assertEqual(buckets[15:17], [buckets[15], buckets[16]])
        self.assertEqual(1, sum(len(bucket) for bucket in buckets))
        self.assertRaises(IndexError, buckets.__getitem__, 20)
        self.assertRaises(IndexError, buckets.__getitem__, -21)
        (fingerprint,) = next(bucket for bucket in buckets if bucket)
        self.assertEqual(locate(cko, "a")[0], fingerprint)

    def test_init_error_rate_allocates_once(self):
        """init_error_rate and frombytes build only the tables they keep"""
        created = []
        original = CuckooLayer.__init__

        def tracking_init(layer, *args, **kwargs):
            created.append(args)
            original(layer, *args, **kwargs)

        CuckooLayer.__init__ = tracking_init  # type: ignore
        try:
            cko = CuckooFilter.init_error_rate(0.001, capacity=100)
            self.assertEqual(1, len(created))
            created.clear()
            CuckooFilter.frombytes(bytes(cko))
            self.assertEqual(1, len(created))
        finally:
            CuckooLayer.__init__ = original  # type: ignore


if __name__ == "__main__":
    unittest.main()
