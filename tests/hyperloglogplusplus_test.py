#!/usr/bin/env python3
"""Unittest class"""

import math
import os
import sys
import unittest
from io import BytesIO
from pathlib import Path
from struct import Struct
from tempfile import NamedTemporaryFile

this_dir = Path(__file__).parent
sys.path.insert(0, str(this_dir))
sys.path.insert(0, str(this_dir.parent))

from probables import HyperLogLog, HyperLogLogPlusPlus  # noqa: E402
from probables.exceptions import InitializationError  # noqa: E402
from probables.hyperloglog.hllpp_bias_data import BIAS_DATA, LINEAR_COUNTING_THRESHOLD, RAW_ESTIMATE_DATA  # noqa: E402

DELETE_TEMP_FILES = True


class TestHyperLogLogPlusPlus(unittest.TestCase):
    """Test HyperLogLog++ (phase 1 dense mode) implementation"""

    def test_hllpp_init(self):
        """Test HyperLogLog++ initialization"""
        hllpp = HyperLogLogPlusPlus()
        self.assertEqual(hllpp.precision, 14)
        self.assertEqual(hllpp.number_registers, 16384)
        self.assertTrue(hllpp.bias_correction)
        self.assertFalse(hllpp.sparse_enabled)
        self.assertFalse(hllpp.is_sparse)

    def test_hllpp_precision_boundaries(self):
        """Test precision lower and upper bounds"""
        lower = HyperLogLogPlusPlus(precision=4)
        upper = HyperLogLogPlusPlus(precision=20)
        self.assertEqual(lower.precision, 4)
        self.assertEqual(upper.precision, 20)

    def test_hllpp_precision_error(self):
        """Test precision validation"""
        self.assertRaises(InitializationError, lambda: HyperLogLogPlusPlus(precision=3))
        self.assertRaises(InitializationError, lambda: HyperLogLogPlusPlus(precision=21))

    def test_hllpp_init_invalid_file(self):
        """Test initialization error for invalid filepath"""
        self.assertRaises(InitializationError, lambda: HyperLogLogPlusPlus(filepath="/tmp/does-not-exist.hllpp"))

    def test_hllpp_cardinality(self):
        """Test approximate cardinality estimation"""
        hllpp = HyperLogLogPlusPlus(precision=10)
        for i in range(1000):
            hllpp.add(str(i))
        self.assertGreaterEqual(hllpp.cardinality(), 900)
        self.assertLessEqual(hllpp.cardinality(), 1100)

    def test_hllpp_bias_correction_toggle(self):
        """Test bias-correction option scaffold"""
        with_bias = HyperLogLogPlusPlus(precision=10, bias_correction=True)
        without_bias = HyperLogLogPlusPlus(precision=10, bias_correction=False)
        for i in range(1000):
            val = str(i)
            with_bias.add(val)
            without_bias.add(val)
        self.assertTrue(with_bias.bias_correction)
        self.assertFalse(without_bias.bias_correction)
        self.assertNotEqual(with_bias.estimate(), without_bias.estimate())

    def test_hllpp_bias_correction_passthrough_high_precision(self):
        """Bias correction should pass through when precision is above paper tables"""
        hllpp = HyperLogLogPlusPlus(precision=19, bias_correction=True)
        raw = 12345.678
        corrected = hllpp._apply_bias_correction(raw)
        self.assertEqual(raw, corrected)

    def test_hllpp_bias_correction_nearest_neighbor(self):
        """Bias correction should use nearest-neighbor mean bias"""
        hllpp = HyperLogLogPlusPlus(precision=10, bias_correction=True)
        estimate = 1005.0
        corrected = hllpp._apply_bias_correction(estimate)
        self.assertLess(corrected, estimate)

    def test_hllpp_bias_table_integrity(self):
        """Full digitized table should cover precisions 4 through 18"""
        for precision in range(4, 19):
            self.assertIn(precision, RAW_ESTIMATE_DATA)
            self.assertIn(precision, BIAS_DATA)
            self.assertIn(precision, LINEAR_COUNTING_THRESHOLD)
            self.assertEqual(len(RAW_ESTIMATE_DATA[precision]), len(BIAS_DATA[precision]))
            self.assertGreater(len(RAW_ESTIMATE_DATA[precision]), 0)

    def test_hllpp_merge(self):
        """Test merging two HyperLogLog++ sketches"""
        first = HyperLogLogPlusPlus(precision=10)
        second = HyperLogLogPlusPlus(precision=10)
        for i in range(500):
            first.add(str(i))
        for i in range(500, 1000):
            second.add(str(i))
        first.merge(second)
        self.assertGreaterEqual(first.cardinality(), 900)
        self.assertLessEqual(first.cardinality(), 1100)

    def test_hllpp_merge_with_hll(self):
        """Test merging HyperLogLog++ with HyperLogLog"""
        hllpp = HyperLogLogPlusPlus(precision=10)
        hll = HyperLogLog(precision=10)
        for i in range(500):
            hllpp.add(str(i))
        for i in range(500, 1000):
            hll.add(str(i))
        hllpp.merge(hll)
        self.assertGreaterEqual(hllpp.cardinality(), 900)
        self.assertLessEqual(hllpp.cardinality(), 1100)

    def test_hllpp_bytes_roundtrip(self):
        """Test export/import via bytes"""
        hllpp = HyperLogLogPlusPlus(precision=10)
        for i in range(1000):
            hllpp.add(str(i))
        hllpp2 = HyperLogLogPlusPlus.frombytes(bytes(hllpp))
        self.assertEqual(bytes(hllpp), bytes(hllpp2))
        self.assertEqual(hllpp2.precision, 10)

    def test_hllpp_export_import_file_object(self):
        """Test export/import via IO object"""
        hllpp = HyperLogLogPlusPlus(precision=10)
        for i in range(500):
            hllpp.add(str(i))
        fobj = BytesIO()
        hllpp.export(fobj)
        hllpp2 = HyperLogLogPlusPlus.frombytes(fobj.getvalue())
        self.assertEqual(bytes(hllpp), bytes(hllpp2))

    def test_hllpp_header_validation(self):
        """Test invalid header handling"""
        hllpp = HyperLogLogPlusPlus(precision=10)
        data = bytearray(bytes(hllpp))
        data[0:4] = b"ABCD"
        self.assertRaises(InitializationError, lambda: HyperLogLogPlusPlus.frombytes(bytes(data)))

    def test_hllpp_reject_hll_bytes(self):
        """Test that HLL++ loader rejects HLL byte format"""
        hll = HyperLogLog(precision=10)
        self.assertRaises(InitializationError, lambda: HyperLogLogPlusPlus.frombytes(bytes(hll)))

    def test_hllpp_frombytes_malformed(self):
        """Test loading malformed HyperLogLog++ bytes"""
        self.assertRaises(InitializationError, lambda: HyperLogLogPlusPlus.frombytes(b""))
        self.assertRaises(InitializationError, lambda: HyperLogLogPlusPlus.frombytes(b"\x01\x02\x03"))

    def test_hllpp_frombytes_corrupted_precision(self):
        """Test loading bytes with invalid precision value"""
        hllpp = HyperLogLogPlusPlus(precision=10)
        data = bytearray(bytes(hllpp))
        footer = Struct("IQ")
        header = Struct("4sBB")
        precision_field = Struct("I")
        footer_start = len(data) - footer.size
        data[footer_start : footer_start + 4] = precision_field.pack(3)
        self.assertRaises(InitializationError, lambda: HyperLogLogPlusPlus.frombytes(bytes(data)))

    def test_hllpp_frombytes_register_length_mismatch(self):
        """Test loading bytes where register count does not match precision"""
        hllpp = HyperLogLogPlusPlus(precision=10)
        data = bytearray(bytes(hllpp))
        broken = data[:-1]
        self.assertRaises(InitializationError, lambda: HyperLogLogPlusPlus.frombytes(bytes(broken)))

    def test_hllpp_version_mismatch(self):
        """Test that wrong HLL++ version is rejected"""
        hllpp = HyperLogLogPlusPlus(precision=10)
        data = bytearray(bytes(hllpp))
        header = Struct("4sBB")
        data[4] = 99
        self.assertRaises(InitializationError, lambda: HyperLogLogPlusPlus.frombytes(bytes(data)))

    def test_hllpp_invalid_magic(self):
        """Test that invalid magic bytes are rejected"""
        hllpp = HyperLogLogPlusPlus(precision=10)
        data = bytearray(bytes(hllpp))
        data[0:4] = b"XXXX"
        self.assertRaises(InitializationError, lambda: HyperLogLogPlusPlus.frombytes(bytes(data)))

    def test_hllpp_add_alt_normalization(self):
        """Test add_alt with negative and oversized hash values"""
        hllpp_neg = HyperLogLogPlusPlus(precision=10)
        hllpp_masked_neg = HyperLogLogPlusPlus(precision=10)
        hllpp_neg.add_alt(-1)
        hllpp_masked_neg.add_alt((1 << 64) - 1)
        self.assertEqual(bytes(hllpp_neg), bytes(hllpp_masked_neg))

        hllpp_big = HyperLogLogPlusPlus(precision=10)
        hllpp_masked_big = HyperLogLogPlusPlus(precision=10)
        hllpp_big.add_alt((1 << 80) + 123)
        hllpp_masked_big.add_alt(123)
        self.assertEqual(bytes(hllpp_big), bytes(hllpp_masked_big))

    def test_hllpp_rank_all_zero_suffix(self):
        """Test rank behavior when remaining hash bits are all zero"""
        precision = 10
        hllpp = HyperLogLogPlusPlus(precision=precision)
        width = 64 - precision
        idx = 42
        hllpp.add_alt(idx << width)
        self.assertEqual(hllpp._registers[idx], width + 1)

    def test_hllpp_small_range_correction(self):
        """Test small-range linear-counting branch"""
        hllpp = HyperLogLogPlusPlus(precision=4)
        hllpp._registers[0] = 1
        estimate = hllpp.estimate()
        expected = hllpp.number_registers * math.log(hllpp.number_registers / (hllpp.number_registers - 1))
        self.assertAlmostEqual(estimate, expected, places=12)

    def test_hllpp_large_range_correction(self):
        """Test large-range correction branch handles extreme synthetic state"""
        hllpp = HyperLogLogPlusPlus(precision=4)
        for idx in range(hllpp.number_registers):
            hllpp._registers[idx] = 255
        estimate = hllpp.estimate()
        self.assertTrue(math.isfinite(estimate))
        self.assertLessEqual(estimate, float((1 << 64)))

    def test_hllpp_merge_associative_commutative(self):
        """Test merge operation associativity and commutativity"""
        a = HyperLogLogPlusPlus(precision=10)
        b = HyperLogLogPlusPlus(precision=10)
        c = HyperLogLogPlusPlus(precision=10)

        for i in range(0, 400):
            a.add(str(i))
        for i in range(300, 700):
            b.add(str(i))
        for i in range(600, 1000):
            c.add(str(i))

        ab = HyperLogLogPlusPlus.frombytes(bytes(a))
        ab.merge(b)
        ba = HyperLogLogPlusPlus.frombytes(bytes(b))
        ba.merge(a)
        self.assertEqual(ab.cardinality(), ba.cardinality())

        left = HyperLogLogPlusPlus.frombytes(bytes(a))
        left.merge(b)
        left.merge(c)

        right = HyperLogLogPlusPlus.frombytes(bytes(b))
        right.merge(c)
        right2 = HyperLogLogPlusPlus.frombytes(bytes(a))
        right2.merge(right)

        self.assertEqual(left.cardinality(), right2.cardinality())

    def test_hllpp_merge_after_clear(self):
        """Test merge behavior after one sketch is cleared"""
        first = HyperLogLogPlusPlus(precision=10)
        second = HyperLogLogPlusPlus(precision=10)
        for i in range(1000):
            first.add(str(i))
            second.add(str(i))

        first.clear()
        first.merge(second)
        self.assertEqual(first.cardinality(), second.cardinality())

    def test_hllpp_error_rate_empirical_sweep(self):
        """Test empirical error across precisions and cardinalities"""
        scenarios = [(6, 300), (8, 1000), (10, 3000)]
        for precision, cardinality in scenarios:
            hllpp = HyperLogLogPlusPlus(precision=precision)
            for i in range(cardinality):
                hllpp.add(str(i))
            est = hllpp.estimate()
            rel_err = abs(est - cardinality) / cardinality
            self.assertLessEqual(rel_err, min(0.35, (3.0 * hllpp.error_rate) + 0.1))

    def test_hllpp_sparse_flags(self):
        """Test sparse-mode flag behavior"""
        default = HyperLogLogPlusPlus()
        sparse_off = HyperLogLogPlusPlus(sparse_enabled=False)
        sparse_on = HyperLogLogPlusPlus(sparse_enabled=True)

        self.assertFalse(default.sparse_enabled)
        self.assertFalse(default.is_sparse)
        self.assertFalse(sparse_off.sparse_enabled)
        self.assertFalse(sparse_off.is_sparse)
        self.assertTrue(sparse_on.sparse_enabled)
        self.assertTrue(sparse_on.is_sparse)

    def test_hllpp_sparse_threshold(self):
        """Test sparse threshold option"""
        hllpp_no_threshold = HyperLogLogPlusPlus(sparse_enabled=True)
        hllpp_with_threshold = HyperLogLogPlusPlus(sparse_enabled=True, sparse_threshold=1000)

        self.assertIsNone(hllpp_no_threshold.sparse_threshold)
        self.assertEqual(hllpp_with_threshold.sparse_threshold, 1000)

    def test_hllpp_export_load_file(self):
        """Test exporting and loading HyperLogLog++ from file"""
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".hllpp", delete=DELETE_TEMP_FILES) as fobj:
            hllpp = HyperLogLogPlusPlus(precision=10)
            for i in range(1000):
                hllpp.add(str(i))
            hllpp.export(fobj.name)

            hllpp2 = HyperLogLogPlusPlus(filepath=fobj.name)
            self.assertEqual(hllpp2.precision, 10)
            self.assertEqual(hllpp2.elements_added, 1000)
            self.assertEqual(bytes(hllpp2), bytes(hllpp))

    def test_hllpp_str_representation(self):
        """Test string representation"""
        hllpp = HyperLogLogPlusPlus(precision=10, bias_correction=True, sparse_enabled=False)
        str_repr = str(hllpp)
        self.assertIn("HyperLogLog++", str_repr)
        self.assertIn("Precision: 10", str_repr)
        self.assertIn("Bias Correction: True", str_repr)
        self.assertIn("Sparse Enabled: False", str_repr)


if __name__ == "__main__":
    unittest.main()
