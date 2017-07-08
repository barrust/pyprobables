# -*- coding: utf-8 -*-
''' Unittest class '''
from __future__ import (unicode_literals, absolute_import, print_function)
import unittest
from probables import (BloomFilter, BloomFilterOnDisk, CountMinSketch,
                       HeavyHitters, StreamThreshold)


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

    def test_bloomfilter_ea(self):
        ''' test elements added is correct '''
        blm = BloomFilter()
        blm.init(10, 0.05)
        self.assertEqual(blm.elements_added, 0)
        blm.add('this is a test')
        self.assertEqual(blm.elements_added, 1)

    def test_bloomfilter_ee(self):
        ''' test estimate elements is correct '''
        blm = BloomFilter()
        blm.init(10, 0.05)
        res1 = blm.estimate_elements()
        blm.add('this is a test')
        res2 = blm.estimate_elements()
        self.assertNotEqual(res1, res2)
        self.assertEqual(res1, 0)
        self.assertEqual(res2, 1)


class TestBloomFilterOnDisk(unittest.TestCase):
    ''' Test the default count-min sketch implementation '''
    def test_bloomfilterod_init(self):
        ''' test the initalization of the on disk version '''
        blmd = BloomFilterOnDisk()
        blmd.init('tmp.blm', 10, 0.05)
        self.assertEqual(blmd.false_positive_rate, 0.05000000074505806)
        self.assertEqual(blmd.estimated_elements, 10)
        self.assertEqual(blmd.number_hashes, 4)
        self.assertEqual(blmd.number_bits, 63)
        self.assertEqual(blmd.elements_added, 0)
        self.assertEqual(blmd.is_on_disk, True)
        self.assertEqual(blmd.bloom_length, 63 // 8 + 1)
        blmd.close()

    def test_bloomfilterod_ea(self):
        ''' test on disk elements added is correct '''
        blmd = BloomFilterOnDisk()
        blmd.init('tmp.blm', 10, 0.05)
        self.assertEqual(blmd.elements_added, 0)
        blmd.add('this is a test')
        self.assertEqual(blmd.elements_added, 1)
        blmd.close()

    def test_bloomfilter_ee(self):
        ''' test on disk estimate elements is correct '''
        blmd = BloomFilterOnDisk()
        blmd.init('tmp.blm', 10, 0.05)
        res1 = blmd.estimate_elements()
        blmd.add('this is a test')
        res2 = blmd.estimate_elements()
        self.assertNotEqual(res1, res2)
        self.assertEqual(res1, 0)
        self.assertEqual(res2, 1)
        blmd.close()

class TestCountMinSketch(unittest.TestCase):
    ''' Test the default count-min sketch implementation '''
    def test_countminsketch(self):
        pass


class TestHeavyHitters(unittest.TestCase):
    ''' Test the default heavy hitters implementation '''
    def test_heavyhitters(self):
        pass


class TestStreamThreshold(unittest.TestCase):
    ''' Test the default stream threshold implementation '''
    def test_streamthreshold(self):
        pass
