# -*- coding: utf-8 -*-
''' Unittest class '''
from __future__ import (unicode_literals, absolute_import, print_function)
import unittest
import os
from probables import (CountingBloomFilter)
from probables.exceptions import (InitializationError, NotSupportedError)
from . utilities import(calc_file_md5, different_hash)


class TestCountingBloomFilter(unittest.TestCase):
    ''' Test the default bloom filter implementation '''

    def test_cbf_init(self):
        ''' test version information '''
        blm = CountingBloomFilter(est_elements=10, false_positive_rate=0.05)
        self.assertEqual(blm.false_positive_rate, 0.05000000074505806)
        self.assertEqual(blm.estimated_elements, 10)
        self.assertEqual(blm.number_hashes, 4)
        self.assertEqual(blm.number_bits, 63)
        self.assertEqual(blm.elements_added, 0)
        self.assertEqual(blm.is_on_disk, False)
        self.assertEqual(blm.bloom_length, 63)

    def test_cbf_ea(self):
        ''' test elements added is correct '''
        blm = CountingBloomFilter(est_elements=10, false_positive_rate=0.05)
        self.assertEqual(blm.elements_added, 0)
        blm.add('this is a test')
        self.assertEqual(blm.elements_added, 1)

    def test_cbf_ea_diff_hash(self):
        ''' test elements added is correct '''
        blm1 = CountingBloomFilter(est_elements=10, false_positive_rate=0.05,
                                   hash_function=different_hash)
        hsh1 = blm1.hashes('this is a test')
        blm2 = CountingBloomFilter(est_elements=10, false_positive_rate=0.05)
        hsh2 = blm2.hashes('this is a test')
        self.assertNotEqual(hsh1, hsh2)

    def test_cbf_check(self):
        ''' ensure that checking the bloom filter works '''
        blm = CountingBloomFilter(est_elements=10, false_positive_rate=0.05)
        blm.add('this is a test')
        blm.add('this is another test')
        self.assertEqual(blm.check('this is a test'), True)
        self.assertEqual(blm.check('this is another test'), True)
        self.assertEqual(blm.check('this is yet another test'), False)
        self.assertEqual(blm.check('this is not another test'), False)

    def test_cbf_in_check(self):
        ''' check that the in construct works '''
        blm = CountingBloomFilter(est_elements=10, false_positive_rate=0.05)
        blm.add('this is a test')
        blm.add('this is another test')
        self.assertEqual('this is a test' in blm, True)
        self.assertEqual('this is another test' in blm, True)
        self.assertEqual('this is yet another test' in blm, False)
        self.assertEqual('this is not another test' in blm, False)

    def test_cbf_stats(self):
        ''' test that the information in the stats is correct '''
        msg = ('CountingBloom:\n'
               '\tbits: 63\n'
               '\testimated elements: 10\n'
               '\tnumber hashes: 4\n'
               '\tmax false positive rate: 0.050000\n'
               '\telements added: 10\n'
               '\tcurrent false positive rate: 0.048806\n'
               '\tis on disk: no\n'
               '\tindex fullness: 0.634921\n'
               '\tmax index usage: 3\n'
               '\tmax index id: 2\n'
               '\tcalculated elements: 10\n')
        blm = CountingBloomFilter(est_elements=10, false_positive_rate=0.05)
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

    def test_cbf_clear(self):
        ''' test clearing out the bloom filter '''
        blm = CountingBloomFilter(est_elements=10, false_positive_rate=0.05)
        self.assertEqual(blm.elements_added, 0)
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

        self.assertEqual(blm.elements_added, 10)

        blm.clear()
        self.assertEqual(blm.elements_added, 0)
        for idx in range(blm.bloom_length):
            self.assertEqual(blm._get_element(idx), 0)

    def test_cbf_export_file(self):
        ''' test exporting bloom filter to file '''
        filename = 'test.cbm'
        md5_val = '941b499746dd72d36658399b209d4869'
        blm = CountingBloomFilter(est_elements=10, false_positive_rate=0.01)
        blm.add('test')
        blm.add('out')
        blm.add('the')
        blm.add('counting')
        blm.add('bloom')
        blm.add('filter')

        blm.add('test')
        blm.add('Test')
        blm.add('out')
        blm.add('test')
        blm.export(filename)

        md5_out = calc_file_md5(filename)
        self.assertEqual(md5_out, md5_val)
        os.remove(filename)

    def test_cbf_load_file(self):
        ''' test loading bloom filter from file '''
        filename = 'test.cbm'
        blm = CountingBloomFilter(est_elements=10, false_positive_rate=0.05)
        blm.add('this is a test')
        blm.export(filename)

        blm2 = CountingBloomFilter(filepath=filename)
        self.assertEqual('this is a test' in blm2, True)
        self.assertEqual('this is not a test' in blm2, False)
        os.remove(filename)

    def test_cbf_load_invalid_file(self):
        ''' test importing a bloom filter from an invalid filepath '''
        filename = 'invalid.cbm'
        self.assertRaises(InitializationError,
                          lambda: CountingBloomFilter(filepath=filename))

    def test_cbf_invalid_params_msg(self):
        ''' test importing a bloom filter from an invalid filepath msg '''
        filename = 'invalid.cbm'
        msg = ('Insufecient parameters to set up the Counting Bloom Filter')
        try:
            CountingBloomFilter(filepath=filename)
        except InitializationError as ex:
            self.assertEqual(str(ex), msg)

    def test_cbf_export_hex(self):
        ''' test the exporting of the bloom filter to a hex string '''
        h_val = ('01000300000000010002000002010102000000000000010000010000000'
                 '10100020100010101000002000101000201000000020001000001010000'
                 '01020002000000000000000a000000000000000a3d4ccccd')

        blm = CountingBloomFilter(est_elements=10, false_positive_rate=0.05)
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

        self.assertEqual(hex_out, h_val)

    def test_cbf_load_hex(self):
        ''' test importing a bloom filter from hex value '''
        h_val = ('01000300000000010002000002010102000000000000010000010000000'
                 '10100020100010101000002000101000201000000020001000001010000'
                 '01020002000000000000000a000000000000000a3d4ccccd')
        blm = CountingBloomFilter(hex_string=h_val)

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

    def test_cbf_load_invalid_hex(self):
        ''' test importing a bloom filter from an invalid hex value '''
        h_val = ('01000300000000010002000002010102000000000000010000010000000'
                 '10100020100010101000002000101000201000000020001000001010000'
                 '01020002000000000000000a000000000000000a3d4ccccQ')
        self.assertRaises(InitializationError,
                          lambda: CountingBloomFilter(hex_string=h_val))

    def test_cbf_export_size(self):
        ''' test the size of the exported file '''
        blm = CountingBloomFilter(est_elements=10, false_positive_rate=0.01)
        self.assertEqual(404, blm.export_size())
