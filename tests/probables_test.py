# -*- coding: utf-8 -*-
''' Unittest class '''
from __future__ import (unicode_literals, absolute_import, print_function)
import unittest
from probables import (BloomFilter)


class TestBloomFilter(unittest.TestCase):
    ''' Test the default bloom filter implementation '''
    def test_bloomfilter_init(self):
        ''' test version information '''
        blm = BloomFilter()
        blm.init(10, 0.05)
        self.assertEqual(blm.false_positive_rate, 0.05000000074505806)
        self.assertEqual(blm.estimated_elements, 10)
        self.assertEqual(blm.number_hashes, 4)
        self.assertEqual(blm.number_bits, 63)
        self.assertEqual(blm.elements_added, 0)
        self.assertEqual(blm.is_on_disk, False)
        self.assertEqual(blm.bloom_length, 63 // 8 + 1)
        self.assertEqual(blm.elements_added, 0)
        self.assertEqual(blm.elements_added, 0)
