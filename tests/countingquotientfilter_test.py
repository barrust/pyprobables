#!/usr/bin/env python3
"""Unittest class"""

import random
import sys
import unittest
from collections import Counter
from pathlib import Path

this_dir = Path(__file__).parent
sys.path.insert(0, str(this_dir))
sys.path.insert(0, str(this_dir.parent))

from probables import CountingQuotientFilter  # noqa: E402
from probables.exceptions import QuotientFilterError  # noqa: E402
from probables.hashes import fnv_1a, fnv_1a_32  # noqa: E402
from probables.quotientfilter.countingquotientfilter import (  # noqa: E402
    _decode_run,
    _encode_counter,
    _encode_run,
)


class TestCounterEncoding(unittest.TestCase):
    """Test the counter encoding used in the runs"""

    def test_small_counts(self):
        """the fixed encodings for counts of 1, 2, and 3"""
        self.assertEqual(_encode_counter(5, 1, 8), [5])
        self.assertEqual(_encode_counter(5, 2, 8), [5, 5])
        self.assertEqual(_encode_counter(5, 3, 8), [5, 0, 5])
        self.assertEqual(_encode_counter(0, 3, 8), [0, 0, 0])

    def test_count_below_one(self):
        """a count below 1 has no encoding"""
        self.assertRaises(ValueError, lambda: _encode_counter(5, 0, 8))
        self.assertRaises(ValueError, lambda: _encode_counter(0, -3, 8))

    def test_large_counts_use_few_slots(self):
        """a large count takes a few slots, each holding a remainder-sized value"""
        for r_bits, rem in ((2, 1), (2, 3), (4, 0), (8, 200), (12, 7)):
            slots = _encode_counter(rem, 10**9, r_bits)
            self.assertLess(len(slots), 40)
            self.assertTrue(all(0 <= val < (1 << r_bits) for val in slots))
            self.assertEqual(_decode_run(slots, r_bits), [[rem, 10**9]])

    def test_round_trip(self):
        """encoding then decoding a run gives back its entries"""
        rng = random.Random(7)
        for r_bits in range(2, 9):
            top = (1 << r_bits) - 1
            for rem in sorted({0, 1, top - 1, top}):
                for count in [*range(1, 70), 1000, 123456789]:
                    self.assertEqual(_decode_run(_encode_counter(rem, count, r_bits), r_bits), [[rem, count]])
        for _ in range(5000):
            r_bits = rng.randint(2, 10)
            rems = sorted(rng.sample(range(1 << r_bits), rng.randint(1, min(5, 1 << r_bits))))
            entries = [[rem, rng.choice([1, 2, 3, 4, rng.randint(1, 10**6)])] for rem in rems]
            self.assertEqual(_decode_run(_encode_run(entries, r_bits), r_bits), entries)


class TestCountingQuotientFilter(unittest.TestCase):
    """Test the counting quotient filter"""

    def test_cqf_init(self):
        """test initializing a counting quotient filter"""
        cqf = CountingQuotientFilter()
        self.assertEqual(cqf.quotient, 20)
        self.assertEqual(cqf.remainder, 12)
        self.assertEqual(cqf.size, 1 << 20)
        self.assertEqual(cqf.bits_per_elm, 16)
        self.assertEqual(cqf._filter.itemsize * 8, 16)
        self.assertEqual(len(cqf), 0)
        self.assertEqual(cqf.elements_added, 0)
        self.assertEqual(cqf.unique_elements, 0)
        self.assertEqual(cqf.slots_used, 0)
        self.assertEqual(cqf.load_factor, 0)
        self.assertTrue(cqf.auto_expand)
        self.assertEqual(cqf.max_load_factor, 0.85)

        for quotient, bits in ((3, 32), (15, 32), (16, 16), (23, 16), (24, 8)):
            self.assertEqual(CountingQuotientFilter(quotient=quotient).bits_per_elm, bits)

        for quotient in (2, 31, 32):
            self.assertRaises(QuotientFilterError, lambda q=quotient: CountingQuotientFilter(quotient=q))

    def test_cqf_add_check_remove(self):
        """counts go up with add and down with remove"""
        cqf = CountingQuotientFilter(quotient=8)
        self.assertEqual(cqf.add("this is a test"), 1)
        self.assertEqual(cqf.add("this is a test", 4), 5)
        self.assertEqual(cqf.add("another"), 1)
        self.assertEqual(cqf.check("this is a test"), 5)
        self.assertEqual(cqf.check("another"), 1)
        self.assertEqual(cqf.check("not added"), 0)
        self.assertIn("this is a test", cqf)
        self.assertNotIn("not added", cqf)
        self.assertEqual(len(cqf), 6)
        self.assertEqual(cqf.unique_elements, 2)

        self.assertEqual(cqf.remove("this is a test", 2), 3)
        self.assertEqual(cqf.remove("this is a test"), 2)
        self.assertEqual(cqf.remove("this is a test", 10), 0)  # more than its count removes it
        self.assertNotIn("this is a test", cqf)
        self.assertEqual(cqf.remove("not added"), 0)
        self.assertEqual(len(cqf), 1)
        self.assertEqual(cqf.unique_elements, 1)
        self.assertTrue(cqf.validate_metadata())

    def test_cqf_remove_absent_from_existing_run(self):
        """removing a hash whose quotient has a run, but not that remainder, changes nothing"""
        cqf = CountingQuotientFilter(quotient=8)
        cqf.add_alt((7 << cqf.remainder) | 5, 2)
        self.assertEqual(cqf.remove_alt((7 << cqf.remainder) | 9), 0)
        self.assertEqual(cqf.remove_alt((7 << cqf.remainder) | 1, 3), 0)
        self.assertEqual(cqf.get_hashes(), [((7 << cqf.remainder) | 5, 2)])
        self.assertEqual((len(cqf), cqf.slots_used), (2, 2))

    def test_cqf_num_els_validation(self):
        """num_els must be a positive integer"""
        cqf = CountingQuotientFilter(quotient=8)
        for val in (0, -1, 1.5, True):
            self.assertRaises(QuotientFilterError, lambda v=val: cqf.add("test", v))
            self.assertRaises(QuotientFilterError, lambda v=val: cqf.remove("test", v))
        self.assertEqual(len(cqf), 0)

    def test_cqf_shared_hash(self):
        """two keys with the same 32-bit hash share a count, so removing one keeps the other"""
        key_a, key_b = "kmbaudjantlo", "lfjbpyjhzflg"
        self.assertEqual(fnv_1a_32(key_a), fnv_1a_32(key_b))
        cqf = CountingQuotientFilter(quotient=10)
        cqf.add(key_a)
        cqf.add(key_b)
        self.assertEqual(cqf.check(key_a), 2)
        cqf.remove(key_a)
        self.assertEqual(cqf.check(key_b), 1)

    def test_cqf_large_counts(self):
        """very large counts take a few slots"""
        cqf = CountingQuotientFilter(quotient=8)
        self.assertEqual(cqf.add("big", 10**12), 10**12)
        self.assertLess(cqf.slots_used, 6)
        self.assertEqual(cqf.add("big"), 10**12 + 1)
        self.assertEqual(cqf.remove("big", 10**12), 1)
        self.assertEqual(cqf.slots_used, 1)
        self.assertTrue(cqf.validate_metadata())

    def test_cqf_remainder_zero_and_largest(self):
        """remainders of 0 and the largest value, which the counter encoding treats specially"""
        cqf = CountingQuotientFilter(quotient=4)
        largest = (1 << cqf.remainder) - 1
        hashes = {(5 << cqf.remainder): 7, (5 << cqf.remainder) | 1: 1, (5 << cqf.remainder) | largest: 4}
        for _hash, count in hashes.items():
            cqf.add_alt(_hash, count)
        for _hash, count in hashes.items():
            self.assertEqual(cqf.check_alt(_hash), count)
        self.assertEqual(cqf.get_hashes(), sorted(hashes.items()))
        cqf.remove_alt(5 << cqf.remainder, 3)
        self.assertEqual(cqf.check_alt(5 << cqf.remainder), 4)
        self.assertTrue(cqf.validate_metadata())

    def test_cqf_wrap_around(self):
        """runs at the end of the table wrap around to the start"""
        cqf = CountingQuotientFilter(quotient=4, auto_expand=False)
        last = cqf.size - 1
        hashes = [(last << cqf.remainder) | i for i in range(1, 5)] + [(0 << cqf.remainder) | 9]
        for i, _hash in enumerate(hashes):
            cqf.add_alt(_hash, i + 1)
        self.assertEqual(cqf.get_hashes(), sorted((h, i + 1) for i, h in enumerate(hashes)))
        self.assertEqual(cqf._is_shifted[0], 1)  # the run of the last quotient reached slot 0
        self.assertTrue(cqf.validate_metadata())

    def test_cqf_hashes(self):
        """hashes and get_hashes give each hash with its count"""
        cqf = CountingQuotientFilter(quotient=8)
        expected = Counter()
        for i in range(100):
            key = str(i % 30)
            cqf.add(key)
            expected[fnv_1a_32(key)] += 1
        self.assertEqual(cqf.get_hashes(), sorted(expected.items()))
        self.assertEqual(dict(cqf.hashes()), dict(expected))

    def test_cqf_auto_expand(self):
        """the filter expands before the slots in use pass the max load factor, keeping the counts"""
        cqf = CountingQuotientFilter(quotient=4)
        cqf.max_load_factor = 0.6
        for i in range(60):
            cqf.add(str(i), i % 3 + 1)
        self.assertGreater(cqf.quotient, 4)
        self.assertLessEqual(cqf.load_factor, 0.6)
        self.assertEqual(cqf.max_load_factor, 0.6)
        self.assertTrue(all(cqf.check(str(i)) == i % 3 + 1 for i in range(60)))
        self.assertTrue(cqf.validate_metadata())

    def test_cqf_full_without_auto_expand(self):
        """without auto expand, the filter raises once no empty slot would remain"""
        cqf = CountingQuotientFilter(quotient=3, auto_expand=False)  # 8 slots, one always kept empty
        for i in range(6):
            cqf.add_alt(i << cqf.remainder)
        self.assertEqual(cqf.slots_used, 6)
        self.assertRaises(QuotientFilterError, lambda: cqf.add_alt(0, 2))  # a count of 3 needs 2 more slots
        self.assertEqual(cqf.add_alt(0), 2)  # a count of 2 needs 1 more slot
        self.assertEqual(cqf.slots_used, 7)
        self.assertRaises(QuotientFilterError, lambda: cqf.add_alt(7 << cqf.remainder))
        self.assertEqual(cqf.check_alt(0), 2)
        self.assertTrue(cqf.validate_metadata())

    def test_cqf_resize(self):
        """resizing keeps every count, growing or shrinking"""
        cqf = CountingQuotientFilter(quotient=10)
        for i in range(200):
            cqf.add(str(i), i + 1)
        before = cqf.get_hashes()
        cqf.resize(12)
        self.assertEqual(cqf.quotient, 12)
        self.assertEqual(cqf.get_hashes(), before)
        cqf.resize(9)
        self.assertEqual(cqf.get_hashes(), before)
        self.assertTrue(cqf.validate_metadata())
        self.assertRaises(QuotientFilterError, lambda: cqf.resize(7))  # too many elements
        self.assertRaises(QuotientFilterError, lambda: cqf.resize(31))

    def test_cqf_expand_past_largest_quotient(self):
        """expanding a filter with a quotient of 30 raises a clear error"""
        cqf = CountingQuotientFilter(quotient=3)
        cqf._q = 30  # avoid allocating 2**30 slots; resize checks the quotient first
        with self.assertRaisesRegex(QuotientFilterError, "largest size"):
            cqf.resize()

    def test_cqf_merge(self):
        """merging adds the counts"""
        first = CountingQuotientFilter(quotient=8)
        second = CountingQuotientFilter(quotient=6)
        first.add("a", 3)
        first.add("b")
        second.add("a", 2)
        second.add("c", 5)
        first.merge(second)
        self.assertEqual((first.check("a"), first.check("b"), first.check("c")), (5, 1, 5))
        self.assertEqual(len(first), 11)
        self.assertEqual(len(second), 7)  # unchanged

        other_hash = CountingQuotientFilter(quotient=8, hash_function=fnv_1a)
        self.assertRaises(QuotientFilterError, lambda: first.merge(other_hash))

    def test_cqf_clear(self):
        """clear removes every element and keeps the size and settings"""
        cqf = CountingQuotientFilter(quotient=4)
        cqf.max_load_factor = 0.9
        for i in range(40):
            cqf.add(str(i), 2)
        quotient = cqf.quotient
        cqf.clear()
        self.assertEqual((len(cqf), cqf.unique_elements, cqf.slots_used), (0, 0, 0))
        self.assertEqual(cqf.get_hashes(), [])
        self.assertEqual(cqf.quotient, quotient)
        self.assertEqual(cqf.max_load_factor, 0.9)
        cqf.add("a", 3)
        self.assertEqual(cqf.check("a"), 3)
        self.assertTrue(cqf.validate_metadata())

    def test_cqf_max_load_factor_validation(self):
        """the max load factor must be greater than 0 and at most 1"""
        cqf = CountingQuotientFilter(quotient=8)
        for val in (0, -0.5, 1.01):
            with self.assertRaises(QuotientFilterError):
                cqf.max_load_factor = val
        cqf.max_load_factor = 1
        self.assertEqual(cqf.max_load_factor, 1.0)
        cqf.auto_expand = False
        self.assertFalse(cqf.auto_expand)

    def test_cqf_hash_uses_lower_32_bits(self):
        """hashes wider than 32 bits use their lower 32 bits"""
        cqf = CountingQuotientFilter(quotient=8, hash_function=fnv_1a)
        cqf.add("test", 2)
        self.assertEqual(cqf.check_alt(fnv_1a("test") & 0xFFFFFFFF), 2)
        self.assertEqual(cqf.add_alt(0x1234_5678 + (1 << 40)), 1)
        self.assertEqual(cqf.check_alt(0x1234_5678), 1)

    def test_cqf_validate_metadata(self):
        """validate_metadata finds invalid bits and counts that do not match"""
        cqf = CountingQuotientFilter(quotient=8)
        for i in range(50):
            cqf.add(str(i), i + 1)
        self.assertTrue(cqf.validate_metadata())
        cqf._elements_added += 1
        self.assertFalse(cqf.validate_metadata())
        cqf._elements_added -= 1
        empty = next(i for i in range(cqf.size) if cqf._is_empty(i))
        cqf._is_continuation[empty] = 1
        self.assertFalse(cqf.validate_metadata())

    def test_cqf_random_against_counter(self):
        """random adds and removes match a Counter of the hashes"""
        rng = random.Random(11)
        for _ in range(60):
            cqf = CountingQuotientFilter(quotient=rng.choice([3, 4, 5]))
            pool = [rng.getrandbits(32) for _ in range(rng.choice([3, 8, 20]))]
            pool.append((cqf.size - 1) << cqf.remainder)  # wraps around
            model: Counter = Counter()
            for _ in range(80):
                _hash, num = rng.choice(pool), rng.choice([1, 1, 2, 3, 4, rng.randint(1, 500)])
                if rng.random() < 0.6:
                    self.assertEqual(cqf.add_alt(_hash, num), model[_hash] + num)
                    model[_hash] += num
                else:
                    model[_hash] = max(model[_hash] - num, 0)
                    self.assertEqual(cqf.remove_alt(_hash, num), model[_hash])
            model = +model
            self.assertEqual(dict(cqf.get_hashes()), dict(model))
            self.assertTrue(all(cqf.check_alt(h) == model[h] for h in pool))
            self.assertTrue(cqf.validate_metadata())


if __name__ == "__main__":
    unittest.main()
