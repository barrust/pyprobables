# -*- coding: utf-8 -*-
''' Unittest class '''
from __future__ import (unicode_literals, absolute_import, print_function)
import unittest
from probables import (ExpandingBloomFilter, RotatingBloomFilter)

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


class TestRotatingBloomFilter(unittest.TestCase):

    def test_rbf_init(self):
        ''' test the initialization of an rotating bloom filter '''
        blm = RotatingBloomFilter(est_elements=10, false_positive_rate=0.05,
                                  max_queue_size=10)
        self.assertEqual(blm.expansions, 0)
        self.assertEqual(blm.max_queue_size, 10)

    def test_rfb_rotate(self):
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

    def test_rfb_push_pop(self):
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
