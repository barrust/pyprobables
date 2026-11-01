#!/usr/bin/env python3
"""Unittest class"""

import math
import os
import sys
import unittest
from io import BytesIO
from pathlib import Path
from random import Random
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
        footer = Struct("<IQ")
        header = Struct("<4sBB")
        precision_field = Struct("<I")
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
        header = Struct("<4sBB")
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
        self.assertRaises(
            InitializationError,
            lambda: HyperLogLogPlusPlus(sparse_enabled=True, sparse_threshold=0),
        )
        self.assertRaises(
            InitializationError,
            lambda: HyperLogLogPlusPlus(precision=4, sparse_enabled=True, sparse_threshold=17),
        )

    def test_hllpp_sparse_estimate_matches_dense_registers(self):
        """Sparse estimates should account for stored ranks at every occupancy level."""
        sparse = HyperLogLogPlusPlus(precision=4, sparse_enabled=True, sparse_threshold=16)
        dense = HyperLogLogPlusPlus(precision=4)
        width = 64 - sparse.precision
        suffix = 1 << (width - 1)

        for idx in range(8):
            value = (idx << width) | suffix
            sparse.add_alt(value)
            dense.add_alt(value)

        self.assertEqual(len(sparse._registers), 0)
        self.assertGreater(sparse.estimate(), 0)
        self.assertAlmostEqual(sparse.estimate(), dense.estimate())

    def test_hllpp_sparse_default_threshold_promotes(self):
        """The default sparse threshold is reachable and bounded for memory efficiency."""
        hllpp = HyperLogLogPlusPlus(precision=4, sparse_enabled=True)
        width = 64 - hllpp.precision
        threshold = hllpp._sparse_promotion_threshold()
        self.assertLessEqual(threshold, 128)
        self.assertLessEqual(threshold, hllpp.number_registers)

        for idx in range(threshold - 1):
            hllpp.add_alt(idx << width)

        self.assertTrue(hllpp.is_sparse)
        hllpp.add_alt((threshold - 1) << width)
        self.assertFalse(hllpp.is_sparse)
        self.assertEqual(len(hllpp._sparse_set), 0)
        self.assertEqual(len(hllpp._registers), hllpp.number_registers)
        self.assertEqual(hllpp._registers.count(0), hllpp.number_registers - threshold)

    def test_hllpp_sparse_uses_register_indexed_mapping(self):
        """Sparse updates replace a register value directly rather than scanning entries."""
        hllpp = HyperLogLogPlusPlus(precision=10, sparse_enabled=True, sparse_threshold=1024)
        width = 64 - hllpp.precision
        idx = 73
        hllpp.add_alt((idx << width) | (1 << (width - 1)))
        hllpp.add_alt(idx << width)

        self.assertEqual(len(hllpp._sparse_set), 1)
        self.assertEqual(hllpp._sparse_set[idx], width + 1)

    def test_hllpp_sparse_v2_supports_full_precision_indexes(self):
        """Version 2 sparse serialization supports register indexes beyond 16 bits."""
        hllpp = HyperLogLogPlusPlus(precision=20, sparse_enabled=True, sparse_threshold=2)
        width = 64 - hllpp.precision
        idx = 70_000
        hllpp.add_alt((idx << width) | (1 << (width - 1)))

        serialized = bytes(hllpp)
        self.assertEqual(serialized[4], 2)
        restored = HyperLogLogPlusPlus.frombytes(serialized)
        self.assertEqual(restored._sparse_set, hllpp._sparse_set)
        self.assertEqual(len(restored._registers), 0)
        self.assertTrue(restored.sparse_enabled)
        self.assertTrue(restored.is_sparse)
        restored.clear()
        self.assertTrue(restored.is_sparse)
        self.assertEqual(len(restored._registers), 0)

    def test_hllpp_sparse_to_dense_merge_materializes_registers(self):
        """Merging dense state promotes sparse registers before using the base merge."""
        sparse = HyperLogLogPlusPlus(precision=8, sparse_enabled=True, sparse_threshold=128)
        dense = HyperLogLog(precision=8)
        expected = HyperLogLogPlusPlus(precision=8)
        for value in range(20):
            sparse.add(str(value))
            expected.add(str(value))
            dense.add(str(value + 20))
            expected.add(str(value + 20))

        sparse.merge(dense)
        self.assertFalse(sparse.is_sparse)
        self.assertEqual(len(sparse._registers), sparse.number_registers)
        self.assertEqual(sparse.cardinality(), expected.cardinality())

    def test_hllpp_sparse_sparse_merge_uses_register_maxima(self):
        """Merging sparse maps combines the maximum rank per register."""
        first = HyperLogLogPlusPlus(precision=8, sparse_enabled=True, sparse_threshold=128)
        second = HyperLogLogPlusPlus(precision=8, sparse_enabled=True, sparse_threshold=128)
        expected = HyperLogLogPlusPlus(precision=8)
        for value in range(10):
            first.add(str(value))
            second.add(str(value + 10))
            expected.add(str(value))
            expected.add(str(value + 10))

        first.merge(second)
        self.assertTrue(first.is_sparse)
        self.assertEqual(len(first._registers), 0)
        self.assertEqual(first.elements_added, 20)
        self.assertAlmostEqual(first.estimate(), expected.estimate())

    def test_hllpp_serialization_uses_standard_little_endian_fields(self):
        """Version 2 streams use portable field sizes and byte order."""
        hllpp = HyperLogLogPlusPlus(precision=10)
        hllpp.add("item")
        serialized = bytes(hllpp)
        self.assertEqual(serialized[:6], Struct("<4sBB").pack(b"HLPP", 2, 0))
        self.assertEqual(serialized[-12:], Struct("<IQ").pack(10, 1))

        sparse_enabled = HyperLogLogPlusPlus(precision=10, sparse_enabled=True)
        sparse_enabled._parse_hllpp_bytes(serialized)
        self.assertFalse(sparse_enabled.is_sparse)
        sparse_enabled.clear()
        self.assertTrue(sparse_enabled.is_sparse)

    def test_hllpp_rejects_unsupported_serialization_version(self):
        """Reject legacy or unknown formats rather than interpreting native layouts."""
        hllpp = HyperLogLogPlusPlus(precision=4)
        data = bytearray(bytes(hllpp))
        data[4] = 1
        self.assertRaises(
            InitializationError,
            lambda: HyperLogLogPlusPlus.frombytes(bytes(data)),
        )

    def test_hllpp_rejects_malformed_serialized_registers(self):
        """Reject unknown flags, invalid ranks, and inconsistent sparse payloads."""
        header = Struct("<4sBB")
        footer = Struct("<IQ")
        dense = HyperLogLogPlusPlus(precision=4)
        invalid_rank = bytearray(bytes(dense))
        invalid_rank[header.size] = 62
        invalid_rank[-footer.size :] = footer.pack(4, 1)
        self.assertRaises(
            InitializationError,
            lambda: HyperLogLogPlusPlus.frombytes(bytes(invalid_rank)),
        )

        invalid_count = bytearray(bytes(dense))
        invalid_count[header.size] = 1
        invalid_count[-footer.size :] = footer.pack(4, 0)
        self.assertRaises(
            InitializationError,
            lambda: HyperLogLogPlusPlus.frombytes(bytes(invalid_count)),
        )

        unknown_flags = bytearray(bytes(dense))
        unknown_flags[5] = 0x80
        self.assertRaises(
            InitializationError,
            lambda: HyperLogLogPlusPlus.frombytes(bytes(unknown_flags)),
        )

        sparse_header = header.pack(b"HLPP", 2, 1)
        sparse_count = Struct("<I")
        sparse_entry = Struct("<IB")

        def sparse_stream(
            entries: list[tuple[int, int]],
            elements_added: int,
            declared_count: int | None = None,
            trailing_data: bytes = b"",
        ) -> bytes:
            count = len(entries) if declared_count is None else declared_count
            payload = sparse_header + sparse_count.pack(count)
            payload += b"".join(sparse_entry.pack(idx, rho) for idx, rho in entries)
            return payload + trailing_data + footer.pack(4, elements_added)

        malformed_streams = (
            sparse_stream([(1, 1), (1, 2)], 2),
            sparse_stream([(16, 1)], 1),
            sparse_stream([(1, 0)], 1),
            sparse_stream([(1, 62)], 1),
            sparse_stream([(1, 1)], 1, declared_count=2),
            sparse_stream([(1, 1)], 1, trailing_data=b"x"),
            sparse_stream([(1, 1)], 0),
            sparse_stream([], 1),
        )
        for malformed in malformed_streams:
            with self.subTest(malformed=malformed):
                self.assertRaises(
                    InitializationError,
                    lambda: HyperLogLogPlusPlus.frombytes(malformed),
                )

    def test_hllpp_sparse_accuracy_across_seeds_and_promotion(self):
        """Sparse estimates match dense estimates before promotion and remain accurate after."""
        for seed in (13, 29, 61):
            rng = Random(seed)
            sparse = HyperLogLogPlusPlus(
                precision=8,
                bias_correction=False,
                sparse_enabled=True,
                sparse_threshold=256,
            )
            dense = HyperLogLogPlusPlus(precision=8, bias_correction=False)
            cardinality = 100
            for _ in range(cardinality):
                value = rng.getrandbits(64)
                sparse.add_alt(value)
                dense.add_alt(value)

            self.assertTrue(sparse.is_sparse)
            self.assertAlmostEqual(sparse.estimate(), dense.estimate())
            error = abs(sparse.estimate() - cardinality) / cardinality
            self.assertLessEqual(error, 0.35)

            for _ in range(5000 - cardinality):
                value = rng.getrandbits(64)
                sparse.add_alt(value)
                dense.add_alt(value)
            self.assertFalse(sparse.is_sparse)
            error = abs(sparse.estimate() - 5000) / 5000
            self.assertLessEqual(error, 0.35)

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
