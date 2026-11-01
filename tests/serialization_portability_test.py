#!/usr/bin/env python3
"""Tests for endian-independent serialization and legacy file loading."""

import sys
import unittest
from pathlib import Path
from struct import Struct

this_dir = Path(__file__).parent
sys.path.insert(0, str(this_dir))
sys.path.insert(0, str(this_dir.parent))

from probables.blooms.bloom import BloomFilter  # noqa: E402
from probables.blooms.countingbloom import CountingBloomFilter  # noqa: E402
from probables.blooms.expandingbloom import ExpandingBloomFilter  # noqa: E402
from probables.countminsketch.countminsketch import CountMinSketch  # noqa: E402
from probables.cuckoo.countingcuckoo import CountingCuckooFilter  # noqa: E402
from probables.cuckoo.cuckoo import CuckooFilter  # noqa: E402
from probables.utilities import Bitarray  # noqa: E402


class TestSerializationPortability(unittest.TestCase):
    """Verify legacy big-endian files load and multi-byte metadata is fixed-width."""

    def test_writers_emit_little_endian_metadata(self):
        bloom = BloomFilter(est_elements=20, false_positive_rate=0.05)
        bloom.add("portable")
        self.assertEqual(
            bytes(bloom)[-20:],
            Struct("<QQf").pack(bloom.estimated_elements, bloom.elements_added, bloom.false_positive_rate),
        )

        sketch = CountMinSketch(width=20, depth=3)
        sketch.add("portable")
        self.assertEqual(
            bytes(sketch)[-16:],
            Struct("<IIq").pack(sketch.width, sketch.depth, sketch.elements_added),
        )

        cuckoo = CuckooFilter(capacity=10, bucket_size=4)
        self.assertEqual(
            bytes(cuckoo)[-8:],
            Struct("<II").pack(cuckoo.bucket_size, cuckoo.max_swaps),
        )

        bitarray = Bitarray(23)
        self.assertEqual(bitarray.to_bytes()[-8:], Struct("<Q").pack(bitarray.size))

    def test_bloom_filters_load_legacy_big_endian(self):
        bloom = BloomFilter(est_elements=20, false_positive_rate=0.05)
        bloom.add("portable")
        footer = Struct(">QQf").pack(bloom.estimated_elements, bloom.elements_added, bloom.false_positive_rate)
        loaded = BloomFilter.frombytes(bytes(bloom._bloom) + footer)
        self.assertEqual(loaded._bloom, bloom._bloom)

        counting = CountingBloomFilter(est_elements=20, false_positive_rate=0.05)
        counting.add("portable")
        bins = Struct(">" + "I" * counting.bloom_length).pack(*counting._bloom)
        footer = Struct(">QQf").pack(counting.estimated_elements, counting.elements_added, counting.false_positive_rate)
        loaded_counting = CountingBloomFilter.frombytes(bins + footer)
        self.assertEqual(loaded_counting._bloom, counting._bloom)

    def test_expanding_bloom_loads_legacy_big_endian(self):
        bloom = ExpandingBloomFilter(est_elements=20, false_positive_rate=0.05)
        bloom.add("portable")
        payload = b"".join(
            Struct(">Q").pack(part.elements_added) + bytes(part.bloom) for part in bloom._blooms
        )
        footer = Struct(">QQQf").pack(
            len(bloom._blooms), bloom.estimated_elements, bloom.elements_added, bloom.false_positive_rate
        )
        loaded = ExpandingBloomFilter.frombytes(payload + footer)
        self.assertEqual([bytes(part.bloom) for part in loaded._blooms], [bytes(part.bloom) for part in bloom._blooms])

    def test_count_min_sketch_loads_legacy_big_endian(self):
        sketch = CountMinSketch(width=20, depth=3)
        sketch.add("portable")
        bins = Struct(">" + "i" * (sketch.width * sketch.depth)).pack(*sketch._bins)
        footer = Struct(">IIq").pack(sketch.width, sketch.depth, sketch.elements_added)
        loaded = CountMinSketch.frombytes(bins + footer)
        self.assertEqual(loaded._bins, sketch._bins)

    def test_cuckoo_filters_load_legacy_big_endian(self):
        cuckoo = CuckooFilter(capacity=10, bucket_size=4)
        cuckoo.add("portable")
        buckets = b"".join(
            Struct(">I").pack(value)
            for bucket in cuckoo.buckets
            for value in list(bucket) + [0] * (cuckoo.bucket_size - len(bucket))
        )
        footer = Struct(">II").pack(cuckoo.bucket_size, cuckoo.max_swaps)
        loaded = CuckooFilter.frombytes(buckets + footer)
        self.assertEqual([list(bucket) for bucket in loaded.buckets], [list(bucket) for bucket in cuckoo.buckets])

        counting = CountingCuckooFilter(capacity=10, bucket_size=4)
        counting.add("portable")
        entries = []
        for bucket in counting.buckets:
            values = [value for entry in bucket for value in entry.get_array()]
            values.extend([0, 0] * (counting.bucket_size - len(bucket)))
            entries.extend(values)
        bins = Struct(">" + "I" * len(entries)).pack(*entries)
        footer = Struct(">II").pack(counting.bucket_size, counting.max_swaps)
        loaded_counting = CountingCuckooFilter.frombytes(bins + footer)
        self.assertEqual(
            [
                [(entry.get_array()[0], entry.get_array()[1]) for entry in bucket]
                for bucket in loaded_counting.buckets
            ],
            [[(entry.get_array()[0], entry.get_array()[1]) for entry in bucket] for bucket in counting.buckets],
        )

    def test_bitarray_loads_legacy_big_endian_size(self):
        bitarray = Bitarray(23)
        bitarray.set_bit(7)
        serialized = bytes(bitarray._bitarray) + Struct(">Q").pack(bitarray.size)
        loaded = Bitarray.from_bytes(serialized)
        self.assertEqual(loaded.as_string(), bitarray.as_string())


if __name__ == "__main__":
    unittest.main()
