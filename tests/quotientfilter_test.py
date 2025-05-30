#!/usr/bin/env python3
"""Unittest class"""

import os
import random
import sys
import unittest
from pathlib import Path
from tempfile import NamedTemporaryFile

from probables.exceptions import QuotientFilterError

this_dir = Path(__file__).parent
sys.path.insert(0, str(this_dir))
sys.path.insert(0, str(this_dir.parent))
from probables import QuotientFilter  # noqa: E402

DELETE_TEMP_FILES = True


class TestQuotientFilter(unittest.TestCase):
    """Test the default quotient filter implementation"""

    def test_qf_init(self):
        "test initializing a blank quotient filter"
        qf = QuotientFilter()

        self.assertEqual(qf.bits_per_elm, 16)
        self.assertEqual(qf.quotient, 20)
        self.assertEqual(qf.remainder, 12)
        self.assertEqual(qf.elements_added, 0)
        self.assertEqual(qf.num_elements, 1048576)  # 2**qf.quotient

        qf = QuotientFilter(quotient=8)

        self.assertEqual(qf.bits_per_elm, 32)
        self.assertEqual(qf.quotient, 8)
        self.assertEqual(qf.remainder, 24)
        self.assertEqual(qf.elements_added, 0)
        self.assertEqual(qf.num_elements, 256)  # 2**qf.quotient
        self.assertTrue(qf.auto_expand)

        qf = QuotientFilter(quotient=24, auto_expand=False)

        self.assertEqual(qf.bits_per_elm, 8)
        self.assertEqual(qf.quotient, 24)
        self.assertEqual(qf.remainder, 8)
        self.assertEqual(qf.elements_added, 0)
        self.assertEqual(qf.num_elements, 16777216)  # 2**qf.quotient
        self.assertFalse(qf.auto_expand)

        # reset auto_expand
        qf.auto_expand = True
        self.assertTrue(qf.auto_expand)

    def test_qf_add_check(self):
        "test that the qf is able to add and check elements"
        qf = QuotientFilter(quotient=8)

        for i in range(0, 200, 2):
            qf.add(str(i))
        self.assertEqual(qf.elements_added, 100)
        self.assertEqual(qf.load_factor, 100 / qf.size)
        found_no = False
        for i in range(0, 200, 2):
            if not qf.check(str(i)):
                found_no = True
        self.assertFalse(found_no)

        for i in range(1, 200, 2):
            print(i)
            self.assertFalse(qf.check(str(i)))

        self.assertEqual(qf.elements_added, 100)

    def test_qf_add_check_in(self):
        "test that the qf is able to add and check elements using `in`"
        qf = QuotientFilter(quotient=8)

        for i in range(0, 200, 2):
            qf.add(str(i))
        self.assertEqual(qf.elements_added, 100)

        found_no = False
        for i in range(0, 200, 2):
            if str(i) not in qf:
                found_no = True
        self.assertFalse(found_no)

        for i in range(1, 200, 2):
            print(i)
            self.assertFalse(str(i) in qf)

        self.assertEqual(qf.elements_added, 100)

    def test_qf_init_errors(self):
        """test quotient filter initialization errors"""
        self.assertRaises(QuotientFilterError, lambda: QuotientFilter(quotient=2))
        self.assertRaises(QuotientFilterError, lambda: QuotientFilter(quotient=32))

    def test_qf_retrieve_hashes(self):
        """test retrieving hashes back from the quotient filter"""
        qf = QuotientFilter(quotient=8, auto_expand=False)
        hashes = []
        for i in range(255):
            hashes.append(qf._hash_func(str(i), 0))  # use the private function here..
            qf.add(str(i))
        self.assertEqual(qf.size, 256)
        self.assertEqual(qf.load_factor, 255 / qf.size)
        out_hashes = qf.get_hashes()
        self.assertEqual(qf.elements_added, len(out_hashes))
        self.assertEqual(set(hashes), set(out_hashes))

    def test_qf_resize(self):
        """test resizing the quotient filter"""
        qf = QuotientFilter(quotient=8, auto_expand=False)
        for i in range(200):
            qf.add(str(i))

        self.assertEqual(qf.elements_added, 200)
        self.assertEqual(qf.load_factor, 200 / qf.size)
        self.assertEqual(qf.quotient, 8)
        self.assertEqual(qf.remainder, 24)
        self.assertEqual(qf.bits_per_elm, 32)
        self.assertFalse(qf.auto_expand)

        self.assertRaises(QuotientFilterError, lambda: qf.resize(7))  # should be too small to fit

        qf.resize(17)
        self.assertEqual(qf.elements_added, 200)
        self.assertEqual(qf.load_factor, 200 / qf.size)
        self.assertEqual(qf.quotient, 17)
        self.assertEqual(qf.remainder, 15)
        self.assertEqual(qf.bits_per_elm, 16)
        # ensure everything is still accessable
        for i in range(200):
            self.assertTrue(qf.check(str(i)))

    def test_qf_auto_resize(self):
        """test resizing the quotient filter automatically"""
        qf = QuotientFilter(quotient=8, auto_expand=True)
        self.assertEqual(qf.max_load_factor, 0.85)
        self.assertEqual(qf.elements_added, 0)
        self.assertEqual(qf.load_factor, 0 / qf.size)
        self.assertEqual(qf.quotient, 8)
        self.assertEqual(qf.remainder, 24)
        self.assertEqual(qf.bits_per_elm, 32)
        self.assertTrue(qf.auto_expand)

        for i in range(220):
            qf.add(str(i))

        self.assertEqual(qf.max_load_factor, 0.85)
        self.assertEqual(qf.elements_added, 220)
        self.assertEqual(qf.load_factor, 220 / qf.size)
        self.assertEqual(qf.quotient, 9)
        self.assertEqual(qf.remainder, 23)
        self.assertEqual(qf.bits_per_elm, 32)

    def test_qf_auto_resize_changed_max_load_factor(self):
        """test resizing the quotient filter with a different load factor"""
        qf = QuotientFilter(quotient=8, auto_expand=True)
        self.assertEqual(qf.max_load_factor, 0.85)
        self.assertTrue(qf.auto_expand)
        qf.max_load_factor = 0.65
        self.assertEqual(qf.max_load_factor, 0.65)

        self.assertEqual(qf.elements_added, 0)
        self.assertEqual(qf.load_factor, 0 / qf.size)
        self.assertEqual(qf.quotient, 8)
        self.assertEqual(qf.remainder, 24)
        self.assertEqual(qf.bits_per_elm, 32)
        self.assertTrue(qf.auto_expand)

        for i in range(200):
            qf.add(str(i))

        self.assertEqual(qf.max_load_factor, 0.85)
        self.assertEqual(qf.elements_added, 200)
        self.assertEqual(qf.load_factor, 200 / qf.size)
        self.assertEqual(qf.quotient, 9)
        self.assertEqual(qf.remainder, 23)
        self.assertEqual(qf.bits_per_elm, 32)

    def test_qf_resize_errors(self):
        """test resizing errors"""

        qf = QuotientFilter(quotient=8, auto_expand=True)
        for i in range(200):
            qf.add(str(i))

        self.assertRaises(QuotientFilterError, lambda: qf.resize(quotient=2))
        self.assertRaises(QuotientFilterError, lambda: qf.resize(quotient=32))
        self.assertRaises(QuotientFilterError, lambda: qf.resize(quotient=6))

    def test_qf_merge(self):
        """test merging two quotient filters together"""
        qf = QuotientFilter(quotient=8, auto_expand=True)
        for i in range(200):
            qf.add(str(i))

        fq = QuotientFilter(quotient=8)
        for i in range(300, 500):
            fq.add(str(i))

        qf.merge(fq)

        for i in range(200):
            self.assertTrue(qf.check(str(i)))
        for i in range(200, 300):
            self.assertFalse(qf.check(str(i)))
        for i in range(300, 500):
            self.assertTrue(qf.check(str(i)))

        self.assertEqual(qf.elements_added, 400)

    def test_qf_merge_error(self):
        """test unable to merge due to inability to grow"""
        qf = QuotientFilter(quotient=8, auto_expand=False)
        for i in range(200):
            qf.add(str(i))

        fq = QuotientFilter(quotient=8)
        for i in range(300, 400):
            fq.add(str(i))

        self.assertRaises(QuotientFilterError, lambda: qf.merge(fq))

        # test mismatch hashes
        def useless_hash(key, seed) -> int:
            return 99999999

        qq = QuotientFilter(quotient=8, hash_function=useless_hash)
        qq.add("999")

        self.assertRaises(QuotientFilterError, lambda: fq.merge(qq))

    def test_qf_remove_missing_elm(self):
        """test removing a missing element"""
        alpha = [a for a in "abcd.efghij;klm-nopqrs=tuvwxyz"]
        qf = QuotientFilter(quotient=7)
        for a in alpha:
            qf.add(a)

        qf.remove("~")

        missing_vals = []
        for a in alpha:
            if not qf.check(a):
                missing_vals.append(a)
        self.assertListEqual(missing_vals, [])
        self.assertTrue(qf.validate_metadata())

    def test_qf_remove_cluster_start(self):
        """test removing a cluster start followed by empty"""
        alpha = [a for a in "abcd.efghij;klm-nopqrs=tuvwxyz"]
        qf = QuotientFilter(quotient=7)
        for a in alpha:
            qf.add(a)

        qf.remove(".")

        missing_vals = []
        for a in alpha:
            if not qf.check(a):
                missing_vals.append(a)
        self.assertListEqual(missing_vals, ["."])
        self.assertTrue(qf.validate_metadata())

    def test_qf_remove_cluster_start_cluster(self):
        """test removing a cluster start followed by cluster start"""
        alpha = [a for a in "abcd.efghij;klm-nopqrs=tuvwxyz"]
        qf = QuotientFilter(quotient=7)
        for a in alpha:
            qf.add(a)

        qf.remove("-")

        missing_vals = []
        for a in alpha:
            if not qf.check(a):
                missing_vals.append(a)
        self.assertListEqual(missing_vals, ["-"])
        self.assertTrue(qf.validate_metadata())

    def test_qf_remove_shifted_run_start_followed_by_empty(self):
        """test removing a shifted run start followed by empty"""
        alpha = [a for a in "abcd.efghij;klm-nopqrs=tuvwxyz"]
        qf = QuotientFilter(quotient=7)
        for a in alpha:
            qf.add(a)

        qf.remove("z")

        missing_vals = []
        for a in alpha:
            if not qf.check(a):
                missing_vals.append(a)
        self.assertListEqual(missing_vals, ["z"])
        self.assertTrue(qf.validate_metadata())

    def test_qf_remove_shifted_run_start_followed_continuation(self):
        """test removing a shifted run start followed by continuation"""
        alpha = [a for a in "abcd.efghij;klm-nopqrs=tuvwxyz"]
        qf = QuotientFilter(quotient=7)
        for a in alpha:
            qf.add(a)

        qf.remove("y")

        missing_vals = []
        for a in alpha:
            if not qf.check(a):
                missing_vals.append(a)
        self.assertListEqual(missing_vals, ["y"])
        self.assertTrue(qf.validate_metadata())

    def test_qf_remove_shifted_continuation_followed_run_start(self):
        """test removing a shifted continuation followed by run start"""
        alpha = [a for a in "abcd.efghij;klm-nopqrs=tuvwxyz"]
        qf = QuotientFilter(quotient=7)
        for a in alpha:
            qf.add(a)

        qf.remove("x")

        missing_vals = []
        for a in alpha:
            if not qf.check(a):
                missing_vals.append(a)
        self.assertListEqual(missing_vals, ["x"])
        self.assertTrue(qf.validate_metadata())

    def test_qf_remove_shifted_run_start_followed_run_start(self):
        """test removing a shifted run start followed by run start"""
        alpha = [a for a in "abcd.efghij;klm-nopqrs=tuvwxyz"]
        qf = QuotientFilter(quotient=7)
        for a in alpha:
            qf.add(a)

        qf.remove("a")

        missing_vals = []
        for a in alpha:
            if not qf.check(a):
                missing_vals.append(a)
        self.assertListEqual(missing_vals, ["a"])
        self.assertTrue(qf.validate_metadata())

    def test_qf_remove_cluster_start_followed_continuation_follow_run_start(self):
        """test removing a cluster start followed by continuation putting a run start into a cluster start position"""
        alpha = [a for a in "abcd.efghij;klm-nopqrs=tuvwxyz"]
        qf = QuotientFilter(quotient=7)
        for a in alpha:
            qf.add(a)

        qf.remove("d")

        missing_vals = []
        for a in alpha:
            if not qf.check(a):
                missing_vals.append(a)
        self.assertListEqual(missing_vals, ["d"])
        self.assertTrue(qf.validate_metadata())

    def test_qf_remove_full(self):
        """Test removing all elements, but find each one after each removal"""
        alpha = [a for a in "abcd.efghij;klm-nopqrs=tuvwxyz"]
        qf = QuotientFilter(quotient=7)
        for a in alpha:
            _hash = qf._hash_func(a, 0)
            print(a, _hash >> qf._r, _hash & ((1 << qf._r) - 1))
            qf.add(a)

        for a in alpha:
            self.assertTrue(qf.check(a), "failed to insert")

        while alpha:
            missing_vals = []
            val = alpha.pop(0)
            qf.remove(val)
            missing_vals = []
            for a in alpha:
                if not qf.check(a):
                    missing_vals.append(a)
            self.assertListEqual(missing_vals, [])
            self.assertTrue(qf.validate_metadata())

    def test_qf_remove_full_random(self):
        """Test removing all elements, but in a random order"""
        alpha = [a for a in "abcd.efghij;klm-nopqrs=tuvwxyz"]
        qf = QuotientFilter(quotient=7)
        for a in alpha:
            qf.add(a)

        for a in alpha:
            self.assertTrue(qf.check(a), "failed to insert")
            self.assertTrue(qf.validate_metadata())

        while alpha:
            missing_vals = []
            idx = random.randrange(len(alpha))
            val = alpha.pop(idx)
            qf.remove(val)
            missing_vals = []
            for a in alpha:
                if not qf.check(a):
                    missing_vals.append(a)
            self.assertListEqual(missing_vals, [])
            self.assertTrue(qf.validate_metadata())

    def test_qf_remove_full_random_take_2(self):
        """Test removing all elements, but in a random order - take 2"""
        alpha = [a for a in "abcd.efghij;klm-nopqrs=tuvwxyz"]
        qf = QuotientFilter(quotient=7)
        for a in alpha:
            qf.add(a)

        for a in alpha:
            self.assertTrue(qf.check(a), "failed to insert")

        while alpha:
            missing_vals = []
            idx = random.randrange(len(alpha))
            val = alpha.pop(idx)
            qf.remove(val)
            missing_vals = []
            for a in alpha:
                if not qf.check(a):
                    missing_vals.append(a)
            self.assertListEqual(missing_vals, [])
            self.assertTrue(qf.validate_metadata())

    def test_quotient_filter_print_empty(self):
        """Test printing the data of a quotient filter in a manner to be read through"""
        qf = QuotientFilter(quotient=7)
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".txt", delete=DELETE_TEMP_FILES, mode="wt") as fobj:
            qf.print(file=fobj.file)
            fobj.flush()

            with open(fobj.name) as fobj:
                data = fobj.readlines()
        data = [x.strip() for x in data]
        self.assertEqual(data[0], "idx\t--\tO-C-S\tStatus")
        for i in range(2, len(data)):
            self.assertEqual(data[i], f"{i-2}\t--\t0-0-0\tEmpty")

    def test_quotient_filter_print(self):
        """Test printing the data of a quotient filter in a manner to be read through not empty"""
        alpha = [a for a in "abcd.efghij;klm-nopqrs=tuvwxyz"]
        qf = QuotientFilter(quotient=7)
        for a in alpha:
            qf.add(a)

        with NamedTemporaryFile(dir=os.getcwd(), suffix=".txt", delete=DELETE_TEMP_FILES, mode="wt") as fobj:
            qf.print(file=fobj.file)
            fobj.flush()

            with open(fobj.name) as fobj:
                data = fobj.readlines()
        data = [x.strip() for x in data]
        self.assertEqual(data[0], "idx\t--\tO-C-S\tStatus")
        self.assertEqual(data[22], "20\t--\t1-0-0\tCluster Start")
        self.assertEqual(data[23], "21\t--\t1-0-0\tCluster Start")

        self.assertEqual(data[114], "112\t--\t1-0-0\tCluster Start")
        self.assertEqual(data[115], "113\t--\t1-1-1\tContinuation")
        self.assertEqual(data[116], "114\t--\t1-0-1\tRun Start")
        self.assertEqual(data[10], "8\t--\t0-1-1\tContinuation")
        self.assertEqual(data[11], "9\t--\t0-0-1\tRun Start")
