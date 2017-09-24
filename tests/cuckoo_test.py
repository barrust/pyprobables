# -*- coding: utf-8 -*-
''' Unittest class '''
from __future__ import (unicode_literals, absolute_import, print_function)
import unittest

from probables import (CuckooFilter)
# from . utilities import(calc_file_md5, different_hash)

class TestCuckooFilter(unittest.TestCase):
    ''' base Cuckoo Filter test '''

    def test_cuckoo_filter_default(self):
        cko = CuckooFilter()
        self.assertEqual(10000, cko.capacity)
        self.assertEqual(4, cko.bucket_size)
        self.assertEqual(500, cko.max_swaps)

    def test_cuckoo_filter_diff(self):
        cko = CuckooFilter(capacity=100, bucket_size=2, max_swaps=5)
        self.assertEqual(100, cko.capacity)
        self.assertEqual(2, cko.bucket_size)
        self.assertEqual(5, cko.max_swaps)

    def test_cuckoo_filter_add(self):
        cko = CuckooFilter()
        cko.add_element('this is a test')
        self.assertEqual(cko.elements_added, 1)
        cko.add_element('this is another test')
        self.assertEqual(cko.elements_added, 2)
        cko.add_element('this is yet another test')
        self.assertEqual(cko.elements_added, 3)

    def test_cuckoo_filter_check(self):
        cko = CuckooFilter()
        cko.add_element('this is a test')
        cko.add_element('this is another test')
        cko.add_element('this is yet another test')
        self.assertEqual(cko.check_element('this is a test'), True)
        self.assertEqual(cko.check_element('this is another test'), True)
        self.assertEqual(cko.check_element('this is yet another test'), True)
        self.assertEqual(cko.check_element('this is not another test'), False)
        self.assertEqual(cko.check_element('this is not a test'), False)
