"""Regression tests for cuckoo indexing and persisted layouts."""

import random
import unittest
from array import array
from io import BytesIO
from pathlib import Path
from struct import pack
from tempfile import TemporaryDirectory
from unittest.mock import patch

from probables import CountingCuckooFilter, CuckooFilter, InitializationError
from probables.hashes import fnv_1a


class CuckooIndexRegressionTest(unittest.TestCase):
    def test_false_positive_rate_and_membership(self):
        for cls in (CuckooFilter, CountingCuckooFilter):
            with self.subTest(cls=cls):
                rng = random.Random(1)
                cko = cls.init_error_rate(0.001)
                keys = [f"{rng.getrandbits(64):016x}" for _ in range(5000)]
                for key in keys:
                    cko.add(key)
                self.assertEqual(len(keys), cko.elements_added)
                queries = 100_000
                hits = sum(bool(cko.check(f"q{rng.getrandbits(64):016x}")) for _ in range(queries))
                self.assertLessEqual(hits / queries, 0.001)
                for key in keys[:2500]:
                    self.assertTrue(cko.remove(key))
                for key in keys[2500:]:
                    self.assertTrue(cko.check(key))

    def test_colliding_keys_and_duplicates(self):
        def fixed_hash(key):
            return (int(key[1:]) << 32) | 3 if key.startswith("k") else 1

        for cls in (CuckooFilter, CountingCuckooFilter):
            with self.subTest(cls=cls):
                cko = cls(capacity=2, bucket_size=4, hash_function=fixed_hash)
                self.assertEqual(cko._generate_fingerprint_info("k0"), cko._generate_fingerprint_info("k2"))
                cko.add("k0")
                cko.add("k2")
                cko.add("k2")
                self.assertEqual(2 if cls is CuckooFilter else 3, cko.elements_added)
                if cls is CountingCuckooFilter:
                    self.assertEqual(1, cko.check("k0"))
                    self.assertEqual(2, cko.check("k2"))
                self.assertTrue(cko.remove("k0"))
                self.assertTrue(cko.check("k2"))
                self.assertFalse(cko.remove("k0"))
                cko.expand()
                loaded = cls.frombytes(bytes(cko), hash_function=fixed_hash)
                self.assertTrue(loaded.check("k2"))
                self.assertTrue(loaded.remove("k2"))
                if cls is CountingCuckooFilter:
                    self.assertEqual(1, loaded.check("k2"))

    def test_reported_fingerprint_collision(self):
        for cls in (CuckooFilter, CountingCuckooFilter):
            with self.subTest(cls=cls):
                cko = cls.init_error_rate(0.001)
                self.assertEqual(
                    cko._generate_fingerprint_info("user-99")[2], cko._generate_fingerprint_info("user-404")[2]
                )
                cko.add("user-99")
                cko.add("user-404")
                self.assertEqual(2, cko.elements_added)
                self.assertTrue(cko.remove("user-404"))
                self.assertTrue(cko.check("user-99"))

    def test_zero_fingerprint_round_trip(self):
        def fixed_hash(key):
            return 1 << 32 if key == "key" else 7

        for cls in (CuckooFilter, CountingCuckooFilter):
            with self.subTest(cls=cls):
                cko = cls(capacity=4, hash_function=fixed_hash)
                cko.add("key")
                if cls is CountingCuckooFilter:
                    cko.add("key")
                loaded = cls.frombytes(bytes(cko), hash_function=fixed_hash)
                self.assertEqual(2 if cls is CountingCuckooFilter else True, loaded.check("key"))
                self.assertTrue(loaded.remove("key"))
                if cls is CountingCuckooFilter:
                    self.assertEqual(1, loaded.check("key"))
                    self.assertTrue(loaded.remove("key"))
                self.assertFalse(loaded.check("key"))

    def test_successful_kicks_preserve_hashes_and_counts(self):
        hashes = {"a": 1, "b": (1 << 32) | 2, "c": 3, "1": 1, "2": 3, "3": 0}

        def fixed_hash(key):
            return hashes[key]

        for cls in (CuckooFilter, CountingCuckooFilter):
            with self.subTest(cls=cls):
                cko = cls(capacity=4, bucket_size=1, hash_function=fixed_hash)
                cko.add("a")
                if cls is CountingCuckooFilter:
                    cko.add("a")
                cko.add("b")
                with patch("random.choice", return_value=0), patch("random.randrange", return_value=0):
                    cko.add("c")
                self.assertEqual(
                    [[3], [1], [2], []],
                    [
                        [entry.finger if cls is CountingCuckooFilter else entry for entry in bucket]
                        for bucket in cko.buckets
                    ],
                )
                for key in ("a", "b", "c"):
                    self.assertTrue(cko.check(key))
                loaded = cls.frombytes(bytes(cko), hash_function=fixed_hash)
                self.assertEqual(2 if cls is CountingCuckooFilter else 1, loaded.check("a"))
                loaded.expand()
                for key in ("a", "b", "c"):
                    self.assertTrue(loaded.check(key))

    def test_legacy_exports_are_rejected(self):
        capacity, bucket_size, bits = 20, 4, 13
        key = "user-99"
        fingerprint = fnv_1a(key) & ((1 << bits) - 1)
        idx = fingerprint % capacity
        for cls in (CuckooFilter, CountingCuckooFilter):
            with self.subTest(cls=cls):
                width = 2 if cls is CountingCuckooFilter else 1
                raw = array("I", [0] * (capacity * bucket_size * width))
                raw[idx * bucket_size * width] = fingerprint
                if width == 2:
                    raw[idx * bucket_size * width + 1] = 3
                data = raw.tobytes() + pack("II", bucket_size, 500)
                with self.assertRaisesRegex(InitializationError, "older pyprobables releases"):
                    cls.frombytes(data, error_rate=0.001)
                zero_raw = array("I", [0] * (bucket_size * width))
                if width == 2:
                    zero_raw[1] = 3
                with self.assertRaisesRegex(InitializationError, "older pyprobables releases"):
                    cls.frombytes(zero_raw.tobytes() + pack("II", bucket_size, 500))
                with TemporaryDirectory() as temp_dir:
                    path = Path(temp_dir) / "legacy.cko"
                    path.write_bytes(data)
                    with self.assertRaisesRegex(InitializationError, "older pyprobables releases"):
                        cls(filepath=path)
                    with self.assertRaisesRegex(InitializationError, "older pyprobables releases"):
                        cls.load_error_rate(0.001, path)

    def test_counting_load_resets_unique_count(self):
        original = CountingCuckooFilter(capacity=10)
        original.add("a")
        original.add("a")
        loaded = CountingCuckooFilter(capacity=10)
        loaded.add("old")
        loaded.add("another")
        loaded._load(BytesIO(bytes(original)))
        self.assertEqual(1, loaded.unique_elements)
        self.assertEqual(2, loaded.elements_added)
        self.assertEqual(2, loaded.check("a"))

    def test_invalid_modern_data_and_error_rate(self):
        for cls in (CuckooFilter, CountingCuckooFilter):
            with self.subTest(cls=cls):
                cko = cls.init_error_rate(0.001, capacity=2)
                cko.add("key")
                data = bytes(cko)
                self.assertTrue(cls.frombytes(bytearray(data)).check("key"))
                reloaded = cls(capacity=2)
                reloaded._load(BytesIO(data))
                self.assertTrue(reloaded.check("key"))
                with self.assertRaises(InitializationError):
                    cls.frombytes(data[:-1])
                with self.assertRaisesRegex(InitializationError, "format version"):
                    cls.frombytes(data[:6] + b"\x02" + data[7:])
                with self.assertRaises(ValueError):
                    cls.frombytes(data, error_rate=0.00001)
                with self.assertRaises(ValueError):
                    cls.init_error_rate(0.0)
                with self.assertRaises(ValueError):
                    cls.init_error_rate(1e-20)
                with self.assertRaises(ValueError):
                    cls.init_error_rate(1e-320)
                with self.assertRaises(ValueError):
                    cko.fingerprint_size = 1
                cko.buckets[0].append(99)
                with self.assertRaises(ValueError):
                    bytes(cko)

        with self.assertRaises(InitializationError):
            CountingCuckooFilter.frombytes(bytes(CuckooFilter(capacity=2)))


if __name__ == "__main__":
    unittest.main()
