# -*- coding: utf-8 -*-
''' Unittest class '''
from __future__ import (unicode_literals, absolute_import, print_function)
import unittest
from probables import (BloomFilter, BloomFilterOnDisk, CountMinSketch,
                       HeavyHitters, StreamThreshold)


class TestBloomFilter(unittest.TestCase):
    ''' Test the default bloom filter implementation '''

    def test_bf_init(self):
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

    def test_bf_ea(self):
        ''' test elements added is correct '''
        blm = BloomFilter()
        blm.init(10, 0.05)
        self.assertEqual(blm.elements_added, 0)
        blm.add('this is a test')
        self.assertEqual(blm.elements_added, 1)

    def test_bf_add(self):
        ''' test estimate elements is correct '''
        blm = BloomFilter()
        blm.init(10, 0.05)
        res1 = blm.estimate_elements()
        blm.add('this is a test')
        res2 = blm.estimate_elements()
        self.assertNotEqual(res1, res2)
        self.assertEqual(res1, 0)
        self.assertEqual(res2, 1)
        self.assertEqual(blm.elements_added, 1)

    def test_bf_check(self):
        ''' ensure that checking the bloom filter works '''
        blm = BloomFilter()
        blm.init(10, 0.05)
        blm.add('this is a test')
        blm.add('this is another test')
        self.assertEqual(blm.check('this is a test'), True)
        self.assertEqual(blm.check('this is another test'), True)
        self.assertEqual(blm.check('this is yet another test'), False)
        self.assertEqual(blm.check('this is not another test'), False)

    def test_bf_in_check(self):
        ''' check that the in construct works '''
        blm = BloomFilter()
        blm.init(10, 0.05)
        blm.add('this is a test')
        blm.add('this is another test')
        self.assertEqual('this is a test' in blm, True)
        self.assertEqual('this is another test' in blm, True)
        self.assertEqual('this is yet another test' in blm, False)
        self.assertEqual('this is not another test' in blm, False)

    def test_bf_union(self):
        ''' test the union of two bloom filters '''
        blm = BloomFilter()
        blm.init(10, 0.05)
        blm.add('this is a test')
        blm.add('this is another test')
        blm2 = BloomFilter()
        blm2.init(10, 0.05)
        blm2.add('this is yet another test')

        blm3 = blm.union(blm2)
        self.assertEqual(blm3.estimate_elements(), 3)
        self.assertEqual(blm3.elements_added, 3)
        self.assertEqual(blm3.check('this is a test'), True)
        self.assertEqual(blm3.check('this is another test'), True)
        self.assertEqual(blm3.check('this is yet another test'), True)
        self.assertEqual(blm3.check('this is not another test'), False)

    def test_bf_union_diff(self):
        ''' make sure checking for different bloom filters works union '''
        blm = BloomFilter()
        blm.init(10, 0.05)
        blm.add('this is a test')
        blm2 = BloomFilter()
        blm2.init(100, 0.05)

        blm3 = blm.union(blm2)
        self.assertEqual(blm3, None)

    def test_bf_intersection(self):
        ''' test the union of two bloom filters '''
        blm = BloomFilter()
        blm.init(10, 0.05)
        blm.add('this is a test')
        blm.add('this is another test')
        blm2 = BloomFilter()
        blm2.init(10, 0.05)
        blm2.add('this is another test')
        blm2.add('this is yet another test')

        blm3 = blm.intersection(blm2)
        self.assertEqual(blm3.estimate_elements(), 1)
        self.assertEqual(blm3.elements_added, 1)
        self.assertEqual(blm3.check('this is a test'), False)
        self.assertEqual(blm3.check('this is another test'), True)
        self.assertEqual(blm3.check('this is yet another test'), False)
        self.assertEqual(blm3.check('this is not another test'), False)

    def test_bf_intersection_diff(self):
        ''' make sure checking for different bloom filters works
            intersection '''
        blm = BloomFilter()
        blm.init(10, 0.05)
        blm.add('this is a test')
        blm2 = BloomFilter()
        blm2.init(100, 0.05)

        blm3 = blm.intersection(blm2)
        self.assertEqual(blm3, None)

    def test_bf_jaccard(self):
        ''' test the jaccard index of two bloom filters '''
        blm = BloomFilter()
        blm.init(10, 0.05)
        blm.add('this is a test')
        blm.add('this is another test')
        blm2 = BloomFilter()
        blm2.init(10, 0.05)
        blm2.add('this is another test')
        blm2.add('this is yet another test')

        res = blm.jaccard_index(blm2)
        self.assertGreater(res, 0.33)
        self.assertLess(res, 0.50)

    def test_bf_jaccard_diff(self):
        ''' make sure checking for different bloom filters works jaccard '''
        blm = BloomFilter()
        blm.init(10, 0.05)
        blm.add('this is a test')
        blm2 = BloomFilter()
        blm2.init(100, 0.05)

        blm3 = blm.jaccard_index(blm2)
        self.assertEqual(blm3, None)

    def test_bf_jaccard_empty(self):
        ''' make sure checking for different bloom filters works jaccard '''
        blm = BloomFilter()
        blm.init(10, 0.05)
        blm2 = BloomFilter()
        blm2.init(10, 0.05)

        blm3 = blm.jaccard_index(blm2)
        self.assertEqual(blm3, 1.0)

    def test_bf_stats(self):
        ''' test that the information in the stats is correct '''
        msg = ('BloomFilter: \n'
               '\tbits: 63\n'
               '\testimated elements: 10\n'
               '\tnumber hashes: 4\n'
               '\tmax false positive rate: 0.050000\n'
               '\tbloom length (8 bits): 8\n'
               '\telements added: 10\n'
               '\testimated elements added: 9\n'
               '\tcurrent false positive rate: 0.048806\n'
               '\texport size (bytes): 28\n'
               '\tnumber bits set: 29\n'
               '\tis on disk: no\n')
        blm = BloomFilter()
        blm.init(10, 0.05)
        blm.add('this is a test 0')
        blm.add('this is a test 1')
        blm.add('this is a test 2')
        blm.add('this is a test 3')
        blm.add('this is a test 4')
        blm.add('this is a test 5')
        blm.add('this is a test 6')
        blm.add('this is a test 7')
        blm.add('this is a test 8')
        blm.add('this is a test 9')
        stats = str(blm)
        self.assertEqual(stats, msg)

    def test_bf_export_hex(self):
        ''' test the exporting of the bloom filter to a hex string '''
        hex_val = '85f240623b6d9459000000000000000a000000000000000a3d4ccccd'
        blm = BloomFilter()
        blm.init(10, 0.05)
        blm.add('this is a test 0')
        blm.add('this is a test 1')
        blm.add('this is a test 2')
        blm.add('this is a test 3')
        blm.add('this is a test 4')
        blm.add('this is a test 5')
        blm.add('this is a test 6')
        blm.add('this is a test 7')
        blm.add('this is a test 8')
        blm.add('this is a test 9')
        hex_out = blm.export_hex()

        self.assertEqual(hex_out, hex_val)

    def test_bf_load_hex(self):
        ''' test importing a bloom filter from hex value '''
        hex_val = '85f240623b6d9459000000000000000a000000000000000a3d4ccccd'
        blm = BloomFilter()
        blm.load_hex(hex_val)

        self.assertEqual('this is a test 0' in blm, True)
        self.assertEqual('this is a test 1' in blm, True)
        self.assertEqual('this is a test 2' in blm, True)
        self.assertEqual('this is a test 3' in blm, True)
        self.assertEqual('this is a test 4' in blm, True)
        self.assertEqual('this is a test 5' in blm, True)
        self.assertEqual('this is a test 6' in blm, True)
        self.assertEqual('this is a test 7' in blm, True)
        self.assertEqual('this is a test 8' in blm, True)
        self.assertEqual('this is a test 9' in blm, True)

        self.assertEqual('this is a test 10' in blm, False)
        self.assertEqual('this is a test 11' in blm, False)
        self.assertEqual('this is a test 12' in blm, False)


class TestBloomFilterOnDisk(unittest.TestCase):
    ''' Test the default count-min sketch implementation '''
    def test_bfod_init(self):
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

    def test_bfod_ea(self):
        ''' test on disk elements added is correct '''
        blmd = BloomFilterOnDisk()
        blmd.init('tmp.blm', 10, 0.05)
        self.assertEqual(blmd.elements_added, 0)
        blmd.add('this is a test')
        self.assertEqual(blmd.elements_added, 1)
        blmd.close()

    def test_bfod_ee(self):
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

    def test_bfod_check(self):
        blm = BloomFilterOnDisk()
        blm.init('tmp.blm', 10, 0.05)
        blm.add('this is a test')
        blm.add('this is another test')
        self.assertEqual(blm.check('this is a test'), True)
        self.assertEqual(blm.check('this is another test'), True)
        self.assertEqual(blm.check('this is yet another test'), False)
        self.assertEqual(blm.check('this is not another test'), False)
        blm.close()

    def test_bfod_union(self):
        ''' test the union of two bloom filters '''
        blm = BloomFilterOnDisk()
        blm.init('tmp.blm', 10, 0.05)
        blm.add('this is a test')
        blm.add('this is another test')
        blm2 = BloomFilter()
        blm2.init(10, 0.05)
        blm2.add('this is yet another test')

        blm3 = blm.union(blm2)
        self.assertEqual(blm3.estimate_elements(), 3)
        self.assertEqual(blm3.elements_added, 3)
        self.assertEqual(blm3.check('this is a test'), True)
        self.assertEqual(blm3.check('this is another test'), True)
        self.assertEqual(blm3.check('this is yet another test'), True)
        self.assertEqual(blm3.check('this is not another test'), False)
        blm.close()

    def test_bfod_intersection(self):
        ''' test the union of two bloom filters '''
        blm = BloomFilterOnDisk()
        blm.init('tmp.blm', 10, 0.05)
        blm.add('this is a test')
        blm.add('this is another test')
        blm2 = BloomFilter()
        blm2.init(10, 0.05)
        blm2.add('this is another test')
        blm2.add('this is yet another test')

        blm3 = blm.intersection(blm2)
        self.assertEqual(blm3.estimate_elements(), 1)
        self.assertEqual(blm3.elements_added, 1)
        self.assertEqual(blm3.check('this is a test'), False)
        self.assertEqual(blm3.check('this is another test'), True)
        self.assertEqual(blm3.check('this is yet another test'), False)
        self.assertEqual(blm3.check('this is not another test'), False)
        blm.close()

    def test_bfod_jaccard(self):
        ''' test the on disk jaccard index of two bloom filters '''
        blm = BloomFilterOnDisk()
        blm.init('tmp.blm', 10, 0.05)
        blm.add('this is a test')
        blm.add('this is another test')
        blm2 = BloomFilter()
        blm2.init(10, 0.05)
        blm2.add('this is another test')
        blm2.add('this is yet another test')

        res = blm.jaccard_index(blm2)
        self.assertGreater(res, 0.33)
        self.assertLess(res, 0.50)
        blm.close()

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
