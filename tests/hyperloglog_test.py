#!/usr/bin/env python3
"""Unittest class"""

import math
import os
import sys
import unittest
from io import BytesIO
from hashlib import sha1
from pathlib import Path
from struct import Struct
from tempfile import NamedTemporaryFile

this_dir = Path(__file__).parent
sys.path.insert(0, str(this_dir))
sys.path.insert(0, str(this_dir.parent))

from probables import HyperLogLog  # noqa: E402
from probables.exceptions import InitializationError, NotSupportedError  # noqa: E402

DELETE_TEMP_FILES = True


class TestHyperLogLog(unittest.TestCase):
    """Test the HyperLogLog implementation"""

    def test_hll_init(self):
        """Test HyperLogLog initialization"""
        hll = HyperLogLog()
        self.assertEqual(hll.precision, 14)
        self.assertEqual(hll.number_registers, 16384)
        self.assertAlmostEqual(hll.error_rate, 0.008125, places=6)
        self.assertEqual(hll.elements_added, 0)
        self.assertEqual(hll.cardinality(), 0)

    def test_hll_init_error(self):
        """Test HyperLogLog initialization errors"""
        self.assertRaises(InitializationError, lambda: HyperLogLog(precision=3))

    def test_hll_init_error_msg(self):
        """Test HyperLogLog initialization error message"""
        try:
            HyperLogLog(precision=21)
        except InitializationError as ex:
            self.assertEqual(str(ex), "HyperLogLog: precision must be between 4 and 20")
        else:
            self.assertEqual(True, False)

    def test_hll_precision_boundaries(self):
        """Test precision lower and upper bounds"""
        lower = HyperLogLog(precision=4)
        upper = HyperLogLog(precision=20)
        self.assertEqual(lower.precision, 4)
        self.assertEqual(upper.precision, 20)

    def test_hll_init_invalid_file(self):
        """Test initialization error for invalid filepath"""
        self.assertRaises(InitializationError, lambda: HyperLogLog(filepath="/tmp/does-not-exist.hll"))

    def test_hll_add_duplicates(self):
        """Test duplicate additions do not inflate the estimate"""
        hll = HyperLogLog(precision=10)
        hll.add("this is a test")
        hll.add("this is a test")
        hll.add("this is a test")

        self.assertEqual(hll.elements_added, 3)
        self.assertEqual(hll.cardinality(), 1)
        self.assertEqual(len(hll), 1)

    def test_hll_cardinality(self):
        """Test approximate cardinality estimation"""
        hll = HyperLogLog(precision=10)
        for i in range(1000):
            hll.add(str(i))

        self.assertEqual(hll.elements_added, 1000)
        self.assertGreaterEqual(hll.cardinality(), 900)
        self.assertLessEqual(hll.cardinality(), 1100)

    def test_hll_clear(self):
        """Test clearing the sketch"""
        hll = HyperLogLog(precision=10)
        for i in range(100):
            hll.add(str(i))

        self.assertGreater(hll.cardinality(), 0)
        hll.clear()
        self.assertEqual(hll.elements_added, 0)
        self.assertEqual(hll.cardinality(), 0)

    def test_hll_merge(self):
        """Test merging two HyperLogLogs"""
        first = HyperLogLog(precision=10)
        second = HyperLogLog(precision=10)

        for i in range(500):
            first.add(str(i))
        for i in range(500, 1000):
            second.add(str(i))

        first.merge(second)
        self.assertEqual(first.elements_added, 1000)
        self.assertGreaterEqual(first.cardinality(), 900)
        self.assertLessEqual(first.cardinality(), 1100)

    def test_hll_merge_error(self):
        """Test HyperLogLog merge errors"""
        first = HyperLogLog(precision=10)
        second = HyperLogLog(precision=12)
        self.assertRaises(NotSupportedError, lambda: first.merge(second))

    def test_hll_custom_hash_option(self):
        """Test providing a custom hash function"""

        def custom_hash(key, seed=0):
            data = key if isinstance(key, bytes) else key.encode("utf-8")
            digest = sha1(seed.to_bytes(8, byteorder="big", signed=False) + data).digest()
            return int.from_bytes(digest[:8], byteorder="big", signed=False)

        default_hll = HyperLogLog(precision=10)
        custom_hll = HyperLogLog(precision=10, hash_function=custom_hash)

        for i in range(1000):
            val = str(i)
            default_hll.add(val)
            custom_hll.add(val)

        self.assertGreaterEqual(custom_hll.cardinality(), 900)
        self.assertLessEqual(custom_hll.cardinality(), 1100)
        self.assertRaises(NotSupportedError, lambda: default_hll.merge(custom_hll))

    def test_hll_merge_compatibility_custom_hash(self):
        """Test merge succeeds with matching custom hash functions"""

        def custom_hash(key, seed=0):
            data = key if isinstance(key, bytes) else key.encode("utf-8")
            digest = sha1(seed.to_bytes(8, byteorder="big", signed=False) + data).digest()
            return int.from_bytes(digest[:8], byteorder="big", signed=False)

        first = HyperLogLog(precision=10, hash_function=custom_hash)
        second = HyperLogLog(precision=10, hash_function=custom_hash)
        for i in range(500):
            first.add(str(i))
        for i in range(500, 1000):
            second.add(str(i))

        first.merge(second)
        self.assertGreaterEqual(first.cardinality(), 900)
        self.assertLessEqual(first.cardinality(), 1100)

    def test_hll_frombytes(self):
        """Test loading a HyperLogLog from bytes"""
        hll = HyperLogLog(precision=10)
        for i in range(1000):
            hll.add(str(i))

        hll2 = HyperLogLog.frombytes(bytes(hll))
        self.assertEqual(bytes(hll2), bytes(hll))
        self.assertEqual(hll2.precision, 10)
        self.assertEqual(hll2.elements_added, 1000)
        self.assertEqual(hll2.cardinality(), hll.cardinality())

    def test_hll_frombytes_malformed(self):
        """Test loading malformed HyperLogLog bytes"""
        self.assertRaises(InitializationError, lambda: HyperLogLog.frombytes(b""))
        self.assertRaises(InitializationError, lambda: HyperLogLog.frombytes(b"\x01\x02\x03"))

    def test_hll_frombytes_corrupted_precision(self):
        """Test loading bytes with invalid precision value"""
        hll = HyperLogLog(precision=10)
        data = bytes(hll)
        footer = Struct("IQ")
        corrupt = data[: -footer.size] + footer.pack(2, 0)
        self.assertRaises(InitializationError, lambda: HyperLogLog.frombytes(corrupt))

    def test_hll_frombytes_register_length_mismatch(self):
        """Test loading bytes where register count does not match precision"""
        hll = HyperLogLog(precision=10)
        data = bytes(hll)
        footer = Struct("IQ")
        precision, elements = footer.unpack(data[-footer.size :])
        broken = data[:-1]  # remove one register byte
        broken = broken[: -footer.size] + footer.pack(precision, elements)
        self.assertRaises(InitializationError, lambda: HyperLogLog.frombytes(broken))

    def test_hll_export_load(self):
        """Test exporting and loading a HyperLogLog from file"""
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".hll", delete=DELETE_TEMP_FILES) as fobj:
            hll = HyperLogLog(precision=10)
            for i in range(1000):
                hll.add(str(i))
            hll.export(fobj.name)

            hll2 = HyperLogLog(filepath=fobj.name)
            self.assertEqual(hll2.precision, 10)
            self.assertEqual(hll2.elements_added, 1000)
            self.assertEqual(bytes(hll2), bytes(hll))

    def test_hll_export_import_file_object(self):
        """Test exporting to an IO object and loading through frombytes"""
        hll = HyperLogLog(precision=10)
        for i in range(500):
            hll.add(str(i))

        fobj = BytesIO()
        hll.export(fobj)
        hll2 = HyperLogLog.frombytes(fobj.getvalue())
        self.assertEqual(bytes(hll), bytes(hll2))

    def test_hll_add_alt_normalization(self):
        """Test add_alt with negative and oversized hash values"""
        hll_neg = HyperLogLog(precision=10)
        hll_masked_neg = HyperLogLog(precision=10)
        hll_neg.add_alt(-1)
        hll_masked_neg.add_alt((1 << 64) - 1)
        self.assertEqual(bytes(hll_neg), bytes(hll_masked_neg))

        hll_big = HyperLogLog(precision=10)
        hll_masked_big = HyperLogLog(precision=10)
        hll_big.add_alt((1 << 80) + 123)
        hll_masked_big.add_alt(123)
        self.assertEqual(bytes(hll_big), bytes(hll_masked_big))

    def test_hll_rank_all_zero_suffix(self):
        """Test rank behavior when remaining hash bits are all zero"""
        precision = 10
        hll = HyperLogLog(precision=precision)
        width = 64 - precision
        idx = 42
        hll.add_alt(idx << width)
        self.assertEqual(hll._registers[idx], width + 1)

    def test_hll_small_range_correction(self):
        """Test small-range linear-counting branch"""
        hll = HyperLogLog(precision=4)
        hll._registers[0] = 1
        estimate = hll.estimate()
        expected = hll.number_registers * math.log(hll.number_registers / (hll.number_registers - 1))
        self.assertAlmostEqual(estimate, expected, places=12)

    def test_hll_large_range_correction(self):
        """Test large-range correction branch handles extreme synthetic state"""
        hll = HyperLogLog(precision=4)
        for idx in range(hll.number_registers):
            hll._registers[idx] = 255

        estimate = hll.estimate()
        self.assertTrue(math.isfinite(estimate))
        self.assertLessEqual(estimate, float((1 << 64)))

    def test_hll_merge_associative_commutative(self):
        """Test merge operation associativity and commutativity"""
        a = HyperLogLog(precision=10)
        b = HyperLogLog(precision=10)
        c = HyperLogLog(precision=10)

        for i in range(0, 400):
            a.add(str(i))
        for i in range(300, 700):
            b.add(str(i))
        for i in range(600, 1000):
            c.add(str(i))

        ab = HyperLogLog.frombytes(bytes(a))
        ab.merge(b)
        ba = HyperLogLog.frombytes(bytes(b))
        ba.merge(a)
        self.assertEqual(ab.cardinality(), ba.cardinality())

        left = HyperLogLog.frombytes(bytes(a))
        left.merge(b)
        left.merge(c)

        right = HyperLogLog.frombytes(bytes(b))
        right.merge(c)
        right2 = HyperLogLog.frombytes(bytes(a))
        right2.merge(right)

        self.assertEqual(left.cardinality(), right2.cardinality())

    def test_hll_merge_after_clear(self):
        """Test merge behavior after one sketch is cleared"""
        first = HyperLogLog(precision=10)
        second = HyperLogLog(precision=10)
        for i in range(1000):
            first.add(str(i))
            second.add(str(i))

        first.clear()
        first.merge(second)
        self.assertEqual(first.cardinality(), second.cardinality())

    def test_hll_error_rate_empirical_sweep(self):
        """Test empirical error across precisions and cardinalities"""
        scenarios = [(6, 300), (8, 1000), (10, 3000)]
        for precision, cardinality in scenarios:
            hll = HyperLogLog(precision=precision)
            for i in range(cardinality):
                hll.add(str(i))
            est = hll.estimate()
            rel_err = abs(est - cardinality) / cardinality
            # Allow a generous envelope to avoid flaky failures while still catching regressions.
            self.assertLessEqual(rel_err, min(0.35, (3.0 * hll.error_rate) + 0.1))
