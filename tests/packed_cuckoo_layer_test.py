"""Tests for packed cuckoo layer storage."""

import random
import unittest
from unittest.mock import patch

from probables.cuckoo._packed_layer import PackedCuckooLayer


class PackedCuckooLayerTest(unittest.TestCase):
    def test_packed_fingerprints_and_zero(self):
        for bits in (8, 13, 16, 17, 32, 33, 64):
            for counting in (False, True):
                with self.subTest(bits=bits, counting=counting):
                    layer = PackedCuckooLayer(3, 4, bits, counting)
                    self.assertEqual(12 * ((bits + 7) // 8), len(layer.fingerprints))
                    self.assertEqual(2, len(layer.occupied))
                    self.assertTrue(layer.insert(0, 0, 1, lambda i, _: 1 - i, 3))
                    slot = layer.find(0, 0, 1)
                    self.assertIsNotNone(slot)
                    self.assertEqual(0, layer.fingerprint(slot))
                    self.assertEqual(1, layer.count(slot))
                    layer.clear(slot)
                    self.assertIsNone(layer.find(0, 0, 1))

    def test_failed_kicks_restore_fingerprints_and_counts(self):
        layer = PackedCuckooLayer(2, 1, 16, counting=True)
        layer.put(0, 0, 2)
        layer.put(1, 1, 3)
        before = bytes(layer.fingerprints), bytes(layer.occupied), bytes(layer.counts)
        with patch.object(random, "choice", return_value=0), patch.object(random, "randrange", return_value=0):
            self.assertFalse(layer.insert(2, 0, 1, lambda i, _: 1 - i, 10))
        self.assertEqual(before, (bytes(layer.fingerprints), bytes(layer.occupied), bytes(layer.counts)))

    def test_successful_kick_preserves_count(self):
        layer = PackedCuckooLayer(3, 1, 16, counting=True)
        layer.put(0, 0, 5)
        layer.put(1, 1, 3)
        with patch.object(random, "choice", return_value=0), patch.object(random, "randrange", return_value=0):
            self.assertTrue(layer.insert(2, 0, 1, lambda i, _: 2 if i == 0 else 0, 2, count=7))
        self.assertEqual((2, 7), (layer.fingerprint(0), layer.count(0)))
        self.assertEqual((0, 5), (layer.fingerprint(2), layer.count(2)))

    def test_exception_during_kicks_restores_state(self):
        layer = PackedCuckooLayer(2, 1, 16, counting=True)
        layer.put(0, 0, 2)
        layer.put(1, 1, 3)
        before = bytes(layer.fingerprints), bytes(layer.occupied), bytes(layer.counts)

        def fail(_bucket, _fingerprint):
            raise RuntimeError("alternate index failed")

        with self.assertRaisesRegex(RuntimeError, "alternate index failed"):
            layer.insert(2, 0, 1, fail, 10)
        self.assertEqual(before, (bytes(layer.fingerprints), bytes(layer.occupied), bytes(layer.counts)))

    def test_count_overflow_does_not_mutate_slot(self):
        layer = PackedCuckooLayer(1, 1, 16, counting=True)
        layer.put(0, 3, 4)
        before = bytes(layer.fingerprints), bytes(layer.occupied), bytes(layer.counts)
        with self.assertRaises(OverflowError):
            layer.put(0, 9, 1 << 32)
        self.assertEqual(before, (bytes(layer.fingerprints), bytes(layer.occupied), bytes(layer.counts)))


if __name__ == "__main__":
    unittest.main()
