# -*- coding: utf-8 -*-
''' Unittest class '''
from __future__ import (unicode_literals, absolute_import, print_function)
import unittest

from probables import (CuckooFilter, CuckooFilterFullError)
# from . utilities import(calc_file_md5, different_hash)

class TestCuckooFilter(unittest.TestCase):
    ''' base Cuckoo Filter test '''

    def test_cuckoo_filter_default(self):
        ''' test cuckoo filter default properties '''
        cko = CuckooFilter()
        self.assertEqual(10000, cko.capacity)
        self.assertEqual(4, cko.bucket_size)
        self.assertEqual(500, cko.max_swaps)

    def test_cuckoo_filter_diff(self):
        ''' test cuckoo filter non-standard properties '''
        cko = CuckooFilter(capacity=100, bucket_size=2, max_swaps=5)
        self.assertEqual(100, cko.capacity)
        self.assertEqual(2, cko.bucket_size)
        self.assertEqual(5, cko.max_swaps)

    def test_cuckoo_filter_add(self):
        ''' test adding to the cuckoo filter '''
        cko = CuckooFilter()
        cko.add('this is a test')
        self.assertEqual(cko.elements_added, 1)
        cko.add('this is another test')
        self.assertEqual(cko.elements_added, 2)
        cko.add('this is yet another test')
        self.assertEqual(cko.elements_added, 3)

    def test_cuckoo_filter_remove(self):
        ''' test removing from the cuckoo filter '''
        cko = CuckooFilter()
        cko.add('this is a test')
        self.assertEqual(cko.elements_added, 1)
        cko.add('this is another test')
        self.assertEqual(cko.elements_added, 2)
        cko.add('this is yet another test')
        self.assertEqual(cko.elements_added, 3)

        res = cko.remove('this is a test')
        self.assertTrue(res)
        self.assertEqual(cko.elements_added, 2)
        self.assertFalse(cko.check('this is a test'))
        self.assertTrue(cko.check('this is another test'))
        self.assertTrue(cko.check('this is yet another test'))

    def test_cuckoo_filter_remove_miss(self):
        ''' test removing from the cuckoo filter when not present '''
        cko = CuckooFilter()
        cko.add('this is a test')
        self.assertEqual(cko.elements_added, 1)
        cko.add('this is another test')
        self.assertEqual(cko.elements_added, 2)
        cko.add('this is yet another test')
        self.assertEqual(cko.elements_added, 3)

        res = cko.remove('this is still a test')
        self.assertFalse(res)
        self.assertEqual(cko.elements_added, 3)
        self.assertTrue(cko.check('this is a test'))
        self.assertTrue(cko.check('this is another test'))
        self.assertTrue(cko.check('this is yet another test'))

    def test_cuckoo_filter_lots(self):
        ''' test inserting lots into the cuckoo filter '''
        cko = CuckooFilter(capacity=100, bucket_size=2, max_swaps=100)
        for i in range(125):
            cko.add(str(i))
        self.assertEqual(cko.elements_added, 125)

    def test_cuckoo_filter_full(self):
        ''' test inserting until cuckoo filter is full '''
        def runner():
            cko = CuckooFilter(capacity=100, bucket_size=2, max_swaps=100)
            for i in range(175):
                cko.add(str(i))
        self.assertRaises(CuckooFilterFullError, runner)

    def test_cuckoo_full_msg(self):
        ''' test exception message for full cuckoo filter '''
        try:
            cko = CuckooFilter(capacity=100, bucket_size=2, max_swaps=100)
            for i in range(175):
                cko.add(str(i))
        except CuckooFilterFullError as ex:
            self.assertEqual(str(ex), 'The CuckooFilter is currently full')

    def test_cuckoo_idx(self):
        ''' test that the indexing works correctly for cuckoo filter swap '''
        cko = CuckooFilter(capacity=100, bucket_size=2, max_swaps=5)
        txt = 'this is a test'
        idx_1, idx_2, fingerprint = cko._generate_fingerprint_info(txt)
        index_1, index_2 = cko._indicies_from_fingerprint(fingerprint)
        self.assertEqual(idx_1, index_1)
        self.assertEqual(idx_2, index_2)

    def test_cuckoo_filter_check(self):
        ''' test checking if element in cuckoo filter '''
        cko = CuckooFilter()
        cko.add('this is a test')
        cko.add('this is another test')
        cko.add('this is yet another test')
        self.assertEqual(cko.check('this is a test'), True)
        self.assertEqual(cko.check('this is another test'), True)
        self.assertEqual(cko.check('this is yet another test'), True)
        self.assertEqual(cko.check('this is not another test'), False)
        self.assertEqual(cko.check('this is not a test'), False)

    def test_cuckoo_filter_in(self):
        ''' test checking using 'in' cuckoo filter '''
        cko = CuckooFilter()
        cko.add('this is a test')
        cko.add('this is another test')
        cko.add('this is yet another test')
        self.assertEqual('this is a test' in cko, True)
        self.assertEqual('this is another test' in cko, True)
        self.assertEqual('this is yet another test' in cko, True)
        self.assertEqual('this is not another test' in cko, False)
        self.assertEqual('this is not a test' in cko, False)

    def test_cuckoo_filter_dup_add(self):
        ''' test adding same item multiple times cuckoo filter '''
        cko = CuckooFilter()
        cko.add('this is a test')
        cko.add('this is another test')
        cko.add('this is yet another test')
        self.assertEqual(cko.elements_added, 3)
        cko.add('this is a test')
        cko.add('this is another test')
        cko.add('this is yet another test')
        self.assertEqual(cko.elements_added, 3)

    def test_cuckoo_filter_load(self):
        ''' test the load factor of the cuckoo filter '''
        cko = CuckooFilter(capacity=100, bucket_size=2, max_swaps=10)
        self.assertEqual(cko.load_factor(), 0.0)
        for i in range(50):
            cko.add(str(i))
        self.assertEqual(cko.load_factor(), 0.25)
        for i in range(50):
            cko.add(str(i + 50))
        self.assertEqual(cko.load_factor(), 0.50)
