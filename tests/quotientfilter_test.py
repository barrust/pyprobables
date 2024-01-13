#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" Unittest class """

import hashlib
import os
import sys
import unittest
from pathlib import Path
from tempfile import NamedTemporaryFile

this_dir = Path(__file__).parent
sys.path.insert(0, str(this_dir))
sys.path.insert(0, str(this_dir.parent))
from probables import QuotientFilter
from tests.utilities import calc_file_md5, different_hash

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
        self.assertRaises(ValueError, lambda: QuotientFilter(quotient=2))
        self.assertRaises(ValueError, lambda: QuotientFilter(quotient=32))

    def test_retrieve_hashes(self):
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

    def test_resize(self):
        """test resizing the quotient filter"""
        qf = QuotientFilter(quotient=8, auto_expand=False)
        for i in range(200):
            qf.add(str(i))

        self.assertEqual(qf.elements_added, 200)
        self.assertEqual(qf.load_factor, 200 / qf.size)
        self.assertEqual(qf.quotient, 8)
        self.assertEqual(qf.remainder, 24)
        self.assertEqual(qf.bits_per_elm, 32)

        self.assertRaises(ValueError, lambda: qf.resize(7))  # should be too small to fit

        qf.resize(17)
        self.assertEqual(qf.elements_added, 200)
        self.assertEqual(qf.load_factor, 200 / qf.size)
        self.assertEqual(qf.quotient, 17)
        self.assertEqual(qf.remainder, 15)
        self.assertEqual(qf.bits_per_elm, 16)
        # ensure everything is still accessable
        for i in range(200):
            self.assertTrue(qf.check(str(i)))

    def test_auto_resize(self):
        """test resizing the quotient filter"""
        qf = QuotientFilter(quotient=8, auto_expand=True)
        self.assertEqual(qf.max_load_factor, 0.85)
        self.assertEqual(qf.elements_added, 0)
        self.assertEqual(qf.load_factor, 0 / qf.size)
        self.assertEqual(qf.quotient, 8)
        self.assertEqual(qf.remainder, 24)
        self.assertEqual(qf.bits_per_elm, 32)

        for i in range(220):
            qf.add(str(i))

        self.assertEqual(qf.max_load_factor, 0.85)
        self.assertEqual(qf.elements_added, 220)
        self.assertEqual(qf.load_factor, 220 / qf.size)
        self.assertEqual(qf.quotient, 9)
        self.assertEqual(qf.remainder, 23)
        self.assertEqual(qf.bits_per_elm, 32)
