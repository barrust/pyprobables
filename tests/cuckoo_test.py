# -*- coding: utf-8 -*-
''' Unittest class '''
from __future__ import (unicode_literals, absolute_import, print_function)
import os
import unittest

from probables import (CuckooFilter, CuckooFilterFullError)
from . utilities import(calc_file_md5)


class TestCuckooFilter(unittest.TestCase):
    ''' base Cuckoo Filter test '''

    def test_cuckoo_filter_default(self):
        ''' test cuckoo filter default properties '''
        cko = CuckooFilter()
        self.assertEqual(10000, cko.capacity)
        self.assertEqual(4, cko.bucket_size)
        self.assertEqual(500, cko.max_swaps)
        self.assertEqual(2, cko.expansion_rate)
        self.assertEqual(True, cko.auto_expand)

    def test_cuckoo_filter_diff(self):
        ''' test cuckoo filter non-standard properties '''
        cko = CuckooFilter(capacity=100, bucket_size=2, max_swaps=5,
                           expansion_rate=4, auto_expand=False)
        self.assertEqual(100, cko.capacity)
        self.assertEqual(2, cko.bucket_size)
        self.assertEqual(5, cko.max_swaps)
        self.assertEqual(4, cko.expansion_rate)
        self.assertEqual(False, cko.auto_expand)

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
            ''' runner '''
            cko = CuckooFilter(capacity=100, bucket_size=2, max_swaps=100,
                               auto_expand=False)
            for i in range(175):
                cko.add(str(i))
        self.assertRaises(CuckooFilterFullError, runner)

    def test_cuckoo_full_msg(self):
        ''' test exception message for full cuckoo filter '''
        try:
            cko = CuckooFilter(capacity=100, bucket_size=2, max_swaps=100,
                               auto_expand=False)
            for i in range(175):
                cko.add(str(i))
        except CuckooFilterFullError as ex:
            self.assertEqual(str(ex), 'The CuckooFilter is currently full')
        else:
            self.assertEqual(True, False)

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

    def test_cuckoo_filter_l_fact(self):
        ''' test the load factor of the cuckoo filter '''
        cko = CuckooFilter(capacity=100, bucket_size=2, max_swaps=10)
        self.assertEqual(cko.load_factor(), 0.0)
        for i in range(50):
            cko.add(str(i))
        self.assertEqual(cko.load_factor(), 0.25)
        for i in range(50):
            cko.add(str(i + 50))
        self.assertEqual(cko.load_factor(), 0.50)

    def test_cuckoo_filter_export(self):
        ''' test exporting a cuckoo filter '''
        filename = './test.cko'
        md5sum = '49b947ddf364d27934570a6b33076b93'
        cko = CuckooFilter()
        for i in range(1000):
            cko.add(str(i))
        cko.export(filename)
        md5_out = calc_file_md5(filename)
        self.assertEqual(md5sum, md5_out)
        os.remove(filename)

    def test_cuckoo_filter_load(self):
        ''' test loading a saved cuckoo filter '''
        filename = './test.cko'
        md5sum = '49b947ddf364d27934570a6b33076b93'
        cko = CuckooFilter()
        for i in range(1000):
            cko.add(str(i))
        cko.export(filename)
        md5_out = calc_file_md5(filename)
        self.assertEqual(md5sum, md5_out)

        ckf = CuckooFilter(filepath='./test.cko')
        for i in range(1000):
            self.assertTrue(ckf.check(str(i)))

        self.assertEqual(10000, ckf.capacity)
        self.assertEqual(4, ckf.bucket_size)
        self.assertEqual(500, ckf.max_swaps)
        self.assertEqual(0.025, ckf.load_factor())
        os.remove(filename)

    def test_cuckoo_filter_expand_els(self):
        ''' test out the expansion of the cuckoo filter '''
        cko = CuckooFilter()
        for i in range(200):
            cko.add(str(i))
        cko.expand()
        for i in range(200):
            self.assertTrue(cko.check(str(i)))
        self.assertEqual(20000, cko.capacity)

    def test_cuckoo_filter_auto_expand(self):
        ''' test inserting until cuckoo filter is full '''
        cko = CuckooFilter(capacity=100, bucket_size=2, max_swaps=100)
        for i in range(375):  # this would fail if it doesn't expand
            cko.add(str(i))
        self.assertEqual(400, cko.capacity)
        self.assertEqual(375, cko.elements_added)
        for i in range(375):
            self.assertTrue(cko.check(str(i)))

    def test_cuckoo_filter_str(self):
        ''' test the str representation of the cuckoo filter '''
        cko = CuckooFilter(capacity=100, bucket_size=2, max_swaps=100)
        for i in range(75):
            cko.add(str(i))
        msg = ('CuckooFilter:\n'
               '\tCapacity: 100\n'
               '\tTotal Bins: 200\n'
               '\tLoad Factor: 37.5%\n'
               '\tInserted Elements: 75\n'
               '\tMax Swaps: 100\n'
               '\tExpansion Rate: 2\n'
               '\tAuto Expand: True')
        self.assertEqual(str(cko), msg)
