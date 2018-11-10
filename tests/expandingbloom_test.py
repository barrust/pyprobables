# -*- coding: utf-8 -*-
''' Unittest class '''
from __future__ import (unicode_literals, absolute_import, print_function)
import unittest
from probables import (ExpandingBloomFilter)

class TestExpandingBloomFilter(unittest.TestCase):

    def test_ebf_init(self):
        ''' test the initialization of an expanding bloom filter '''
        blm = ExpandingBloomFilter(est_elements=10, false_positive_rate=0.05)
        self.assertEqual(len(blm.blooms), 1)

    def test_ebf_add_lots(self):
        ''' test adding "lots" of elements to force the expansion '''
        blm = ExpandingBloomFilter(est_elements=10, false_positive_rate=0.05)
        for i in range(100):
            blm.add("{}".format(i), True)
        self.assertEqual(len(blm.blooms), 10)

    def test_ebf_add_lots_without_force(self):
        ''' testing adding "lots" but force them to be inserted multiple times'''
        blm = ExpandingBloomFilter(est_elements=10, false_positive_rate=0.05)
        # simulate false positives... notice it didn't grow a few...
        for i in range(120):
            blm.add("{}".format(i))
        self.assertEqual(len(blm.blooms), 10)
        self.assertEqual(blm.elements_added, 120)

    def test_ebf_check(self):
        ''' ensure that checking the expanding bloom filter works '''
        blm = ExpandingBloomFilter(est_elements=25, false_positive_rate=0.05)
        # expand it out some first!
        for i in range(100):
            blm.add("{}".format(i))
        blm.add('this is a test')
        blm.add('this is another test')
        self.assertGreater(len(blm.blooms), 2)
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
        self.assertGreater(len(blm.blooms), 2)
        self.assertEqual('this is a test' in blm, True)
        self.assertEqual('this is another test' in blm, True)
        self.assertEqual('this is yet another test' in blm, False)
        self.assertEqual('this is not another test' in blm, False)
