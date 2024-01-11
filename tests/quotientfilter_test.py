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

        qf = QuotientFilter(quotient=24)

        self.assertEqual(qf.bits_per_elm, 8)
        self.assertEqual(qf.quotient, 24)
        self.assertEqual(qf.remainder, 8)
        self.assertEqual(qf.elements_added, 0)
        self.assertEqual(qf.num_elements, 16777216)  # 2**qf.quotient

    def test_qf_add_check(self):
        "test that the qf is able to add and check elements"
        qf = QuotientFilter(quotient=8)

        for i in range(0, 200, 2):
            qf.add(str(i))
        self.assertEqual(qf.elements_added, 100)

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

    def test_qf_errors(self):
        self.assertRaises(ValueError, lambda: QuotientFilter(quotient=2))
        self.assertRaises(ValueError, lambda: QuotientFilter(quotient=32))
