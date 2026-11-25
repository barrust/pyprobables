"""Tests for packed, expanding cuckoo filters."""

import math
import random
import unittest
from struct import pack

from probables import CountingCuckooFilter, CuckooFilter, CuckooFilterFullError, InitializationError


class LayeredCuckooTest(unittest.TestCase):
    def setUp(self):
        self.addCleanup(random.setstate, random.getstate())

    def test_growth_round_trip_and_error_budget(self):
        for cls in (CuckooFilter, CountingCuckooFilter):
            with self.subTest(cls=cls):
                random.seed(17)
                cko = cls.init_error_rate(0.001, capacity=40, auto_expand=False)
                self.assertEqual(14, cko.fingerprint_size_bits)
                for i in range(60):
                    cko.add(f"before-{i}")
                cko.expand()
                for i in range(120):
                    cko.add(f"after-{i}")
                cko.expand()
                self.assertEqual([40, 80, 160], [layer.capacity for layer in cko._layers])
                self.assertEqual([14, 15, 16], [layer.fingerprint_bits for layer in cko._layers])
                self.assertEqual(280, cko.capacity)
                self.assertLessEqual(
                    sum(2 * cko.bucket_size / (1 << layer.fingerprint_bits) for layer in cko._layers), cko.error_rate
                )
                loaded = cls.frombytes(bytes(cko))
                self.assertEqual(bytes(cko), bytes(loaded))
                for i in range(60):
                    self.assertTrue(loaded.check(f"before-{i}"))
                for i in range(120):
                    self.assertTrue(loaded.check(f"after-{i}"))
                loaded.expand()
                loaded.add("after-reload")
                self.assertTrue(cls.frombytes(bytes(loaded)).check("after-reload"))

    def test_automatic_growth_and_settings_are_not_persisted(self):
        for cls in (CuckooFilter, CountingCuckooFilter):
            with self.subTest(cls=cls):
                cko = cls.init_error_rate(0.001, capacity=2, bucket_size=1, expansion_rate=3, auto_expand=False)
                cko.add("a")
                cko.auto_expand = True
                for i in range(50):
                    cko.add(f"key-{i}")
                self.assertGreaterEqual(len(cko._layers), 3)
                loaded = cls.frombytes(bytes(cko))
                self.assertTrue(loaded.auto_expand)
                self.assertEqual(2, loaded.expansion_rate)
                for i in range(50):
                    self.assertTrue(loaded.check(f"key-{i}"))
                loaded.expand()
                self.assertEqual(2 * loaded._layers[-2].capacity, loaded._layers[-1].capacity)

    def test_little_endian_fixture_zero_and_count(self):
        def zero_hash(_key):
            return 0

        for cls in (CuckooFilter, CountingCuckooFilter):
            with self.subTest(cls=cls):
                cko = cls(capacity=1, bucket_size=1, max_swaps=5, finger_size=1, hash_function=zero_hash)
                cko.add("zero")
                if cls is CountingCuckooFilter:
                    cko.add("zero")
                header = pack("<8sBIIdI", b"PYCKOO\x02\x00", int(cls is CountingCuckooFilter), 1, 5, 0.015625, 1)
                expected = header + pack("<IB", 1, 8) + b"\x01\x00"
                if cls is CountingCuckooFilter:
                    expected += b"\x02\x00\x00\x00"
                self.assertEqual(expected, bytes(cko))
                loaded = cls.frombytes(expected, hash_function=zero_hash)
                self.assertEqual(2 if cls is CountingCuckooFilter else True, loaded.check("zero"))

    def test_malformed_data_and_empty_error_rate_mismatch(self):
        for cls in (CuckooFilter, CountingCuckooFilter):
            with self.subTest(cls=cls):
                cko = cls.init_error_rate(0.001, capacity=1, bucket_size=1)
                data = bytes(cko)
                with self.assertRaises(ValueError):
                    cls.frombytes(data, error_rate=0.01)
                with self.assertRaises(InitializationError):
                    cls.frombytes(data + b"\x00")
                with self.assertRaises(InitializationError):
                    cls.frombytes(data[:-1])
                occupancy_offset = cls._FORMAT_HEADER.size + cls._FORMAT_LAYER.size
                invalid = bytearray(data)
                invalid[occupancy_offset] = 0x80
                with self.assertRaises(InitializationError):
                    cls.frombytes(invalid)

    def test_budget_exhaustion_preserves_data(self):
        for cls in (CuckooFilter, CountingCuckooFilter):
            with self.subTest(cls=cls):
                cko = cls.init_error_rate(1e-18, capacity=1)
                self.assertEqual(64, cko.fingerprint_size_bits)
                cko.add("key")
                before = bytes(cko)
                with self.assertRaises(CuckooFilterFullError):
                    cko.expand()
                self.assertEqual(before, bytes(cko))
                self.assertTrue(cko.check("key"))

    def test_error_budget_rounds_up_at_floating_point_boundary(self):
        target = math.nextafter(4 / (1 << 8), 0)
        for cls in (CuckooFilter, CountingCuckooFilter):
            with self.subTest(cls=cls):
                cko = cls.init_error_rate(target, capacity=1, bucket_size=1)
                self.assertEqual(9, cko.fingerprint_size_bits)
                self.assertLessEqual(4 * cko.bucket_size / (1 << cko.fingerprint_size_bits), target)
                self.assertEqual(target, cls.frombytes(bytes(cko)).error_rate)

    def test_count_overflow_does_not_change_filter(self):
        def fixed_hash(_key):
            return 0

        header = pack("<8sBIIdI", b"PYCKOO\x02\x00", 1, 1, 5, 0.015625, 1)
        data = header + pack("<IB", 1, 8) + b"\x01\x00" + b"\xff\xff\xff\xff"
        cko = CountingCuckooFilter.frombytes(data, hash_function=fixed_hash)
        self.assertEqual(0xFFFFFFFF, cko.check("key"))
        with self.assertRaises(OverflowError):
            cko.add("key")
        self.assertEqual(0xFFFFFFFF, cko.elements_added)
        self.assertEqual(data, bytes(cko))

    def test_string_with_surrogate_round_trips(self):
        for cls in (CuckooFilter, CountingCuckooFilter):
            with self.subTest(cls=cls):
                cko = cls(capacity=4)
                cko.add("key\ud800")
                self.assertTrue(cls.frombytes(bytes(cko)).check("key\ud800"))

    def test_multilayer_false_positive_rate(self):
        for cls in (CuckooFilter, CountingCuckooFilter):
            with self.subTest(cls=cls):
                random.seed(314)
                rng = random.Random(314)
                cko = cls.init_error_rate(0.001, capacity=200)
                keys = [f"k{rng.getrandbits(64):016x}" for _ in range(6000)]
                for key in keys:
                    cko.add(key)
                self.assertGreaterEqual(len(cko._layers), 3)
                self.assertTrue(all(cko.check(key) for key in keys))
                queries = 100_000
                hits = sum(bool(cko.check(f"q{rng.getrandbits(64):016x}")) for _ in range(queries))
                self.assertLessEqual(hits, 100)


if __name__ == "__main__":
    unittest.main()
