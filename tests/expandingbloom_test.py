# -*- coding: utf-8 -*-
''' Unittest class '''
from __future__ import (unicode_literals, absolute_import, print_function)

import os
import unittest
from . utilities import calc_file_md5
from probables import (ExpandingBloomFilter, RotatingBloomFilter)
from probables.exceptions import (RotatingBloomFilterError)


class TestExpandingBloomFilter(unittest.TestCase):

    def test_ebf_init(self):
        ''' test the initialization of an expanding bloom filter '''
        blm = ExpandingBloomFilter(est_elements=10, false_positive_rate=0.05)
        self.assertEqual(blm.expansions, 0)
        self.assertEqual(blm.false_positive_rate, 0.05)
        self.assertEqual(blm.estimated_elements, 10)
        self.assertEqual(blm.elements_added, 0)

    def test_ebf_add_lots(self):
        ''' test adding "lots" of elements to force the expansion '''
        blm = ExpandingBloomFilter(est_elements=10, false_positive_rate=0.05)
        for i in range(100):
            blm.add("{}".format(i), True)
        self.assertEqual(blm.expansions, 9)

    def test_ebf_add_lots_without_force(self):
        ''' testing adding "lots" but force them to be inserted multiple times'''
        blm = ExpandingBloomFilter(est_elements=10, false_positive_rate=0.05)
        # simulate false positives... notice it didn't grow a few...
        for i in range(120):
            blm.add("{}".format(i))
        self.assertEqual(blm.expansions, 9)
        self.assertEqual(blm.elements_added, 120)

    def test_ebf_check(self):
        ''' ensure that checking the expanding bloom filter works '''
        blm = ExpandingBloomFilter(est_elements=25, false_positive_rate=0.05)
        # expand it out some first!
        for i in range(100):
            blm.add("{}".format(i))
        blm.add('this is a test')
        blm.add('this is another test')
        self.assertGreater(blm.expansions, 1)
        self.assertEqual(blm.check('this is a test'), True)
        self.assertEqual(blm.check('this is another test'), True)
        self.assertEqual(blm.check('this is yet another test'), False)
        self.assertEqual(blm.check('this is not another test'), False)

    def test_ebf_contains(self):
        ''' ensure that "in" functionality for the expanding bloom filter works '''
        blm = ExpandingBloomFilter(est_elements=25, false_positive_rate=0.05)
        # expand it out some first!
        for i in range(100):
            blm.add("{}".format(i))
        blm.add('this is a test')
        blm.add('this is another test')
        self.assertGreater(blm.expansions, 1)
        self.assertEqual('this is a test' in blm, True)
        self.assertEqual('this is another test' in blm, True)
        self.assertEqual('this is yet another test' in blm, False)
        self.assertEqual('this is not another test' in blm, False)

    def test_ebf_push(self):
        ''' ensure that we are able to push new Bloom Filters '''
        blm = ExpandingBloomFilter(est_elements=25, false_positive_rate=0.05)
        self.assertEqual(blm.expansions, 0)
        blm.push()
        self.assertEqual(blm.expansions, 1)
        self.assertEqual(blm.elements_added, 0)
        blm.push()
        self.assertEqual(blm.expansions, 2)
        self.assertEqual(blm.elements_added, 0)
        blm.push()
        self.assertEqual(blm.expansions, 3)
        self.assertEqual(blm.elements_added, 0)

    def test_ebf_export(self):
        ''' basic expanding Bloom Filter export test '''
        blm = ExpandingBloomFilter(est_elements=25, false_positive_rate=0.05)
        blm.export('test.ebf')
        self.assertEqual(calc_file_md5('test.ebf'), '1581beab91f83b7e5aaf0f059ee94eaf')
        os.remove('test.ebf')

    def test_ebf_import_empty(self):
        ''' test that expanding Bloom Filter is correct on import '''
        blm = ExpandingBloomFilter(est_elements=25, false_positive_rate=0.05)
        blm.export('test.ebf')
        self.assertEqual(calc_file_md5('test.ebf'), '1581beab91f83b7e5aaf0f059ee94eaf')

        blm2 = ExpandingBloomFilter(filepath='test.ebf')
        for bloom in blm2._blooms:
            self.assertEqual(bloom.elements_added, 0)

        os.remove('test.ebf')

    def test_ebf_import_non_empty(self):
        ''' test expanding Bloom Filter import when non-empty '''
        blm = ExpandingBloomFilter(est_elements=25, false_positive_rate=0.05)
        for i in range(15):
            blm.add('{}'.format(i))
            blm.push()

        blm.export('test.ebf')

        blm2 = ExpandingBloomFilter(filepath='test.ebf')
        self.assertEqual(blm2.expansions, 15)
        for i in range(15):
            self.assertEqual('{}'.format(i) in blm2, True)

        # check for things that are not there!
        for i in range(99, 125):
            self.assertEqual('{}'.format(i) in blm2, False)

        os.remove('test.ebf')


class TestRotatingBloomFilter(unittest.TestCase):

    def test_rbf_init(self):
        ''' test the initialization of an rotating bloom filter '''
        blm = RotatingBloomFilter(est_elements=10, false_positive_rate=0.05,
                                  max_queue_size=10)
        self.assertEqual(blm.expansions, 0)
        self.assertEqual(blm.max_queue_size, 10)

    def test_rbf_rotate(self):
        ''' test that the bloom filter rotates the first bloom off the stack '''
        blm = RotatingBloomFilter(est_elements=10, false_positive_rate=0.05,
                                  max_queue_size=5)
        self.assertEqual(blm.expansions, 0)
        blm.add('test')
        self.assertEqual(blm.expansions, 0)
        for i in range(10):
            blm.add('{}'.format(i), force=True)
        self.assertEqual(blm.expansions, 1)
        self.assertEqual(blm.current_queue_size, 2)
        self.assertEqual(blm.check('test'), True)

        for i in range(10, 20):
            blm.add('{}'.format(i), force=True)
        self.assertEqual(blm.check('test'), True)
        self.assertEqual(blm.current_queue_size, 3)

        for i in range(20, 30):
            blm.add('{}'.format(i), force=True)
        self.assertEqual(blm.check('test'), True)
        self.assertEqual(blm.current_queue_size, 4)

        for i in range(30, 40):
            blm.add('{}'.format(i), force=True)
        self.assertEqual(blm.check('test'), True)
        self.assertEqual(blm.current_queue_size, 5)

        for i in range(40, 50):
            blm.add('{}'.format(i), force=True)
        self.assertEqual(blm.check('test'), False)  # it should roll off
        self.assertEqual(blm.current_queue_size, 5)

    def test_rbf_push_pop(self):
        blm = RotatingBloomFilter(est_elements=10, false_positive_rate=0.05,
                                  max_queue_size=5)
        self.assertEqual(blm.current_queue_size, 1)
        blm.add('test')
        blm.push()
        self.assertEqual(blm.current_queue_size, 2)
        self.assertEqual('test' in blm, True)
        blm.push()
        self.assertEqual(blm.current_queue_size, 3)
        self.assertEqual('test' in blm, True)
        blm.push()
        self.assertEqual(blm.current_queue_size, 4)
        self.assertEqual('test' in blm, True)
        blm.push()
        self.assertEqual(blm.current_queue_size, 5)
        self.assertEqual('test' in blm, True)
        blm.push()
        self.assertEqual(blm.current_queue_size, 5)
        self.assertEqual('test' in blm, False)

        # test popping
        blm.add("that")
        blm.pop()
        self.assertEqual(blm.current_queue_size, 4)
        self.assertEqual('that' in blm, True)
        blm.pop()
        self.assertEqual(blm.current_queue_size, 3)
        self.assertEqual('that' in blm, True)
        blm.pop()
        self.assertEqual(blm.current_queue_size, 2)
        self.assertEqual('that' in blm, True)
        blm.pop()
        self.assertEqual(blm.current_queue_size, 1)
        self.assertEqual('that' in blm, True)

    def test_rbf_pop_exception(self):
        ''' ensure the correct exception is thrown '''
        blm = RotatingBloomFilter(est_elements=10, false_positive_rate=0.05,
                                  max_queue_size=5)
        self.assertRaises(RotatingBloomFilterError, lambda: blm.pop())

    def test_rbf_pop_exception_msg(self):
        ''' rotating bloom filter error: check the resulting error message '''
        blm = RotatingBloomFilter(est_elements=10, false_positive_rate=0.05,
                                  max_queue_size=5)
        try:
            blm.pop()
        except RotatingBloomFilterError as ex:
            msg = "Popping a Bloom Filter will result in an unusable system!"
            self.assertEqual(str(ex), msg)
        except:
            self.assertEqual(True, False)

    def test_rfb_basic_export(self):
        ''' basic rotating Bloom Filter export test '''
        blm = RotatingBloomFilter(est_elements=25, false_positive_rate=0.05)
        blm.export('test.rbf')
        self.assertEqual(calc_file_md5('test.rbf'), '1581beab91f83b7e5aaf0f059ee94eaf')
        os.remove('test.rbf')

    def test_rbf_import_empty(self):
        ''' test that rotating Bloom Filter is correct on import '''
        blm = RotatingBloomFilter(est_elements=25, false_positive_rate=0.05)
        blm.export('test.rbf')
        self.assertEqual(calc_file_md5('test.rbf'), '1581beab91f83b7e5aaf0f059ee94eaf')

        blm2 = ExpandingBloomFilter(filepath='test.rbf')
        for bloom in blm2._blooms:
            self.assertEqual(bloom.elements_added, 0)

        os.remove('test.rbf')

    def test_rbf_non_basic_import(self):
        ''' test that the imported rotating Bloom filter is correct '''
        blm = RotatingBloomFilter(est_elements=25, false_positive_rate=0.05)
        for i in range(15):
            blm.add('{}'.format(i))
            blm.push()
        blm.export('test.rbf')

        blm2 = RotatingBloomFilter(filepath='test.rbf')
        # test those that should be popped off...
        for i in range(5):
            self.assertEqual('{}'.format(i) in blm2, False)
        # test things that would not be popped
        for i in range(6, 15):
            self.assertEqual('{}'.format(i) in blm2, True)
        self.assertEqual(blm2.current_queue_size, 10)
        self.assertEqual(blm2.expansions, 9)
        os.remove('test.rbf')
