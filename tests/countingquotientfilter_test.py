#!/usr/bin/env python3
"""Unittest class"""

import random
import sys
import unittest
from collections import Counter
from unittest import mock
from pathlib import Path

this_dir = Path(__file__).parent
sys.path.insert(0, str(this_dir))
sys.path.insert(0, str(this_dir.parent))

from probables import CountingQuotientFilter, QuotientFilter  # noqa: E402
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
        cqf.resize(10)  # 597 slots fit in 1,023, though over the max load factor: it stays at exactly 10
        self.assertEqual(cqf.quotient, 10)
        self.assertEqual(cqf.get_hashes(), before)
        self.assertTrue(cqf.auto_expand)
        self.assertTrue(cqf.validate_metadata())
        self.assertRaises(QuotientFilterError, lambda: cqf.resize(31))

    def test_cqf_resize_too_small_changes_nothing(self):
        """a resize the elements do not fit in raises before changing anything, with or without auto expand"""
        for auto_expand in (False, True):
            cqf = CountingQuotientFilter(quotient=10, auto_expand=auto_expand)
            for i in range(100):
                cqf.add(str(i), 1000)  # 3 slots each: 300 slots for 100 elements
            before = (cqf.quotient, cqf.get_hashes(), len(cqf), cqf.slots_used)
            with self.assertRaisesRegex(QuotientFilterError, "need 300 slots"):
                cqf.resize(8)  # 255 slots, though 100 elements would fit one slot each
            self.assertEqual((cqf.quotient, cqf.get_hashes(), len(cqf), cqf.slots_used), before)
            self.assertEqual(cqf.auto_expand, auto_expand)
            self.assertTrue(cqf.validate_metadata())
            cqf.resize(9)
            self.assertEqual(cqf.quotient, 9)
            self.assertEqual(cqf.get_hashes(), before[1])

    def test_cqf_resize_failure_restores(self):
        """if re-adding fails part-way through a resize, the filter is restored"""
        cqf = CountingQuotientFilter(quotient=8)
        for i in range(30):
            cqf.add(str(i), i + 1)
        before = (cqf.quotient, cqf.get_hashes(), len(cqf), cqf.slots_used, cqf.auto_expand)
        real_update = CountingQuotientFilter._update
        calls = []

        def failing_update(self, _hash, change):
            calls.append(1)
            if len(calls) == 10:
                raise MemoryError("simulated")
            return real_update(self, _hash, change)

        with mock.patch.object(CountingQuotientFilter, "_update", failing_update):
            self.assertRaises(MemoryError, lambda: cqf.resize(9))
        self.assertEqual((cqf.quotient, cqf.get_hashes(), len(cqf), cqf.slots_used, cqf.auto_expand), before)
        self.assertTrue(cqf.validate_metadata())

    def test_cqf_quotient_must_be_an_integer(self):
        """a quotient that is not an integer raises QuotientFilterError"""
        for bad in (10.0, "10", None):
            self.assertRaises(QuotientFilterError, lambda q=bad: CountingQuotientFilter(quotient=q))
        cqf = CountingQuotientFilter(quotient=8)
        self.assertRaises(QuotientFilterError, lambda: cqf.resize(9.0))
        self.assertEqual(cqf.quotient, 8)

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

        first.merge(first)  # merging a filter into itself doubles its counts
        self.assertEqual((first.check("a"), first.check("b"), first.check("c")), (10, 2, 10))

    def test_cqf_update_absent_changes_nothing(self):
        """removing from a quotient with no run, through the internal update, changes nothing"""
        cqf = CountingQuotientFilter(quotient=4)
        cqf.add_alt((3 << cqf.remainder) | 2)
        self.assertEqual(cqf._update((7 << cqf.remainder) | 1, -1), 0)
        self.assertEqual(cqf._is_occupied[7], 0)
        self.assertEqual(cqf.get_hashes(), [((3 << cqf.remainder) | 2, 1)])
        self.assertTrue(cqf.validate_metadata())

    def test_cqf_merge_failure_after_resize_restores(self):
        """a merge that fails after it expanded the filter restores the original size and contents"""
        cqf = CountingQuotientFilter(quotient=3)
        for i in range(3):
            cqf.add_alt(i << cqf.remainder, 2)
        before = (cqf.quotient, cqf.get_hashes(), len(cqf), cqf.slots_used, cqf.auto_expand)
        other = CountingQuotientFilter(quotient=6)
        for i in range(40):
            other.add(str(i), i + 1)
        real_update = CountingQuotientFilter._update
        calls = []
        expanded = []

        def failing_update(self, _hash, change):
            calls.append(1)
            if len(calls) == 30:  # after the merge has expanded the filter
                expanded.append(self.quotient)
                raise MemoryError("simulated")
            return real_update(self, _hash, change)

        with mock.patch.object(CountingQuotientFilter, "_update", failing_update):
            self.assertRaises(MemoryError, lambda: cqf.merge(other))
        self.assertGreater(expanded[0], 3)  # it had expanded when the failure happened
        self.assertEqual((cqf.quotient, cqf.get_hashes(), len(cqf), cqf.slots_used, cqf.auto_expand), before)
        self.assertTrue(cqf.validate_metadata())

    def test_cqf_merge_other_types(self):
        """merging something other than a CountingQuotientFilter raises TypeError"""
        cqf = CountingQuotientFilter(quotient=8)
        qf = QuotientFilter(quotient=8)
        qf.add("a")
        for other in (qf, "not a filter", None):
            self.assertRaises(TypeError, lambda o=other: cqf.merge(o))
        self.assertEqual(len(cqf), 0)

    def test_cqf_merge_failure_changes_nothing(self):
        """a merge that does not fit, without auto expand, raises and leaves the filter as it was"""
        cqf = CountingQuotientFilter(quotient=4, auto_expand=False)
        for i in range(5):
            cqf.add_alt(i << cqf.remainder, 2)  # 10 of 15 usable slots
        before = (cqf.get_hashes(), len(cqf), cqf.slots_used, cqf.unique_elements)
        other = CountingQuotientFilter(quotient=4)
        for i in range(10):
            other.add_alt((i << other.remainder) | 1)  # 10 more slots
        self.assertRaises(QuotientFilterError, lambda: cqf.merge(other))
        self.assertEqual((cqf.get_hashes(), len(cqf), cqf.slots_used, cqf.unique_elements), before)
        self.assertTrue(cqf.validate_metadata())

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
        self.assertTrue(cqf.validate_metadata())

        def corrupted(change):
            copy = CountingQuotientFilter(quotient=8)
            for i in range(50):
                copy.add(str(i), i + 1)
            change(copy)
            return copy.validate_metadata()

        def first(cqf, test):
            return next(i for i in range(cqf.size) if test(i))

        def shifted_unoccupied(c):
            return first(c, lambda i: c._is_shifted[i] and not c._is_occupied[i])

        def shifted_run_start(c):
            return first(c, lambda i: c._is_shifted[i] and not c._is_continuation[i])

        def set_bit(bits, idx):
            bits[idx] = 1

        def clear_bit(bits, idx):
            bits[idx] = 0

        empty = first(cqf, cqf._is_empty)
        self.assertFalse(corrupted(lambda c: set_bit(c._is_continuation, empty)))  # 0-1-0
        self.assertFalse(corrupted(lambda c: set_bit(c._is_occupied, shifted_unoccupied(c))))  # an extra run
        self.assertFalse(corrupted(lambda c: clear_bit(c._is_occupied, first(c, lambda i: c._is_occupied[i]))))
        self.assertFalse(corrupted(lambda c: clear_bit(c._is_shifted, shifted_run_start(c))))  # not at its home
        self.assertFalse(corrupted(lambda c: c._filter.__setitem__(first(c, lambda i: c._is_occupied[i]), 0)))

        def cluster_start(c):
            return first(c, lambda i: c._is_occupied[i] and not c._is_shifted[i] and not c._is_continuation[i])

        self.assertFalse(corrupted(lambda c: set_bit(c._is_shifted, cluster_start(c))))  # marked shifted at home

        def fill_empty(c):
            for i in range(c.size):
                if c._is_empty(i):
                    c._is_occupied[i] = 1

        self.assertFalse(corrupted(fill_empty))  # no empty slot

        def duplicate_entry(c):  # a run of 5 5 5 decodes as 5 (count 2) then 5 again
            quot = first(c, c._is_empty)
            c._write_runs([(quot, [5, 5, 5])], quot, quot + 3)
            c._elements_added += 3
            c._unique_elements += 2
            c._slots_used += 3

        self.assertFalse(corrupted(duplicate_entry))

        with mock.patch.object(CountingQuotientFilter, "_check_layout", side_effect=IndexError):
            self.assertFalse(cqf.validate_metadata())  # never raises

    def test_cqf_count_change_in_place(self):
        """a count change that keeps the run's length is written in place, without moving other runs"""
        cqf = CountingQuotientFilter(quotient=8)
        cqf.add_alt((7 << cqf.remainder) | 5, 5)
        cqf.add_alt((8 << cqf.remainder) | 9)
        layout = [(cqf._filter[i], cqf._is_occupied[i], cqf._is_continuation[i], cqf._is_shifted[i]) for i in range(20)]
        self.assertEqual(cqf.add_alt((7 << cqf.remainder) | 5), 6)  # 5 and 6 take the same slots
        after = [(cqf._filter[i], cqf._is_occupied[i], cqf._is_continuation[i], cqf._is_shifted[i]) for i in range(20)]
        self.assertEqual([row[1:] for row in after], [row[1:] for row in layout])
        self.assertEqual(cqf.check_alt((7 << cqf.remainder) | 5), 6)
        self.assertEqual(cqf.check_alt((8 << cqf.remainder) | 9), 1)
        self.assertEqual(len(cqf), 7)
        self.assertTrue(cqf.validate_metadata())

    def test_cqf_small_remainders(self):
        """2- and 3-bit remainders (quotients 30 and 29), tested on a small table by shrinking the remainder"""
        rng = random.Random(5)
        for r_bits in (2, 3):
            for _ in range(30):
                cqf = CountingQuotientFilter(quotient=5, auto_expand=False)
                cqf._r = r_bits  # hashes are (quotient << r_bits) | remainder for this table
                pool = [rng.randrange(cqf.size << r_bits) for _ in range(rng.choice([3, 8, 16]))]
                model: Counter = Counter()
                for _ in range(60):
                    _hash, num = rng.choice(pool), rng.choice([1, 2, 3, 4, rng.randint(1, 300)])
                    if rng.random() < 0.6:
                        try:
                            cqf.add_alt(_hash, num)
                        except QuotientFilterError:
                            continue
                        model[_hash] += num
                    else:
                        cqf.remove_alt(_hash, num)
                        model[_hash] = max(model[_hash] - num, 0)
                    self.assertTrue(cqf.validate_metadata())
                self.assertEqual(dict(cqf.get_hashes()), dict(+model))

    def test_cqf_random_full_without_expanding(self):
        """random adds and removes in a filter filled to its last empty slot, without auto expand"""
        rng = random.Random(3)
        for _ in range(40):
            cqf = CountingQuotientFilter(quotient=rng.choice([3, 4, 5]), auto_expand=False)
            cqf.max_load_factor = 1
            pool = [rng.getrandbits(32) for _ in range(rng.choice([4, 10, 30]))]
            pool.append((cqf.size - 1) << cqf.remainder)  # wraps around
            model: Counter = Counter()
            for _ in range(120):
                _hash, num = rng.choice(pool), rng.choice([1, 1, 2, 3, 4, rng.randint(1, 50)])
                if rng.random() < 0.65:
                    before = cqf.get_hashes()
                    try:
                        self.assertEqual(cqf.add_alt(_hash, num), model[_hash] + num)
                        model[_hash] += num
                    except QuotientFilterError:
                        self.assertEqual(cqf.get_hashes(), before)  # a failed add changes nothing
                else:
                    model[_hash] = max(model[_hash] - num, 0)
                    self.assertEqual(cqf.remove_alt(_hash, num), model[_hash])
                self.assertLess(cqf.slots_used, cqf.size)
            self.assertEqual(dict(cqf.get_hashes()), dict(+model))
            self.assertTrue(cqf.validate_metadata())

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
