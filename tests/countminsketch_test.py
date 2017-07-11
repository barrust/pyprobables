# -*- coding: utf-8 -*-
''' Unittest class '''
from __future__ import (unicode_literals, absolute_import, print_function)
import unittest
import os
from probables import (CountMinSketch, HeavyHitters, StreamThreshold)
from . utilities import(calc_file_md5, different_hash)


class TestCountMinSketch(unittest.TestCase):
    ''' Test the default count-min sketch implementation '''

    def test_cms_init_wd(self):
        ''' Test count-min sketch initialization using depth and width '''
        cms = CountMinSketch(width=1000, depth=5)
        self.assertEqual(cms.width, 1000)
        self.assertEqual(cms.depth, 5)
        self.assertEqual(cms.confidence, 0.96875)
        self.assertEqual(cms.error_rate, 0.002)
        self.assertEqual(cms.elements_added, 0)

    def test_cms_init_ce(self):
        ''' Test count-min sketch initialization using confidence and error
            rate '''
        cms = CountMinSketch(confidence=0.96875, error_rate=0.002)
        self.assertEqual(cms.width, 1000)
        self.assertEqual(cms.depth, 5)
        self.assertEqual(cms.confidence, 0.96875)
        self.assertEqual(cms.error_rate, 0.002)
        self.assertEqual(cms.elements_added, 0)

    def test_cms_init_error(self):
        ''' Test count-min sketch initialization without enough params '''
        self.assertRaises(SyntaxError, lambda: CountMinSketch(width=1000))

    def test_cms_init_error_msg(self):
        ''' Test count-min sketch initialization without enough params '''
        try:
            CountMinSketch(width=1000)
        except SyntaxError as ex:
            msg = ('Must provide one of the following to initialize the '
                   'Count-Min Sketch:\n'
                   '    A file to load,\n'
                   '    The width and depth,\n'
                   '    OR confidence and error rate')
            self.assertEqual(str(ex), msg)

    def test_cms_add_single(self):
        ''' test the insertion of a single element at a time '''
        cms = CountMinSketch(width=1000, depth=5)
        self.assertEqual(cms.add('this is a test'), 1)
        self.assertEqual(cms.add('this is a test'), 2)
        self.assertEqual(cms.add('this is a test'), 3)
        self.assertEqual(cms.add('this is a test'), 4)
        self.assertEqual(cms.elements_added, 4)

    def test_cms_add_mult(self):
        ''' test the insertion of multiple elements at a time '''
        cms = CountMinSketch(width=1000, depth=5)
        self.assertEqual(cms.add('this is a test', 4), 4)
        self.assertEqual(cms.add('this is a test', 4), 8)
        self.assertEqual(cms.add('this is a test', 4), 12)
        self.assertEqual(cms.add('this is a test', 4), 16)
        self.assertEqual(cms.elements_added, 16)

    def test_cms_remove_single(self):
        ''' test the removal of a single element at a time '''
        cms = CountMinSketch(width=1000, depth=5)
        self.assertEqual(cms.add('this is a test', 4), 4)
        self.assertEqual(cms.elements_added, 4)
        self.assertEqual(cms.remove('this is a test'), 3)
        self.assertEqual(cms.remove('this is a test'), 2)
        self.assertEqual(cms.elements_added, 2)

    def test_cms_remove_mult(self):
        ''' test the removal of multiple elements at a time '''
        cms = CountMinSketch(width=1000, depth=5)
        self.assertEqual(cms.add('this is a test', 16), 16)
        self.assertEqual(cms.elements_added, 16)
        self.assertEqual(cms.remove('this is a test', 4), 12)
        self.assertEqual(cms.elements_added, 12)

    def test_cms_check_min(self):
        ''' test checking number elements using min algorithm '''
        cms = CountMinSketch(width=1000, depth=5)
        self.assertEqual(cms.add('this is a test', 255), 255)
        self.assertEqual(cms.add('this is another test', 189), 189)
        self.assertEqual(cms.add('this is also a test', 16), 16)
        self.assertEqual(cms.add('this is something to test', 5), 5)

        self.assertEqual(cms.check('this is something to test'), 5)
        self.assertEqual(cms.check('this is also a test'), 16)
        self.assertEqual(cms.check('this is another test'), 189)
        self.assertEqual(cms.check('this is a test'), 255)
        self.assertEqual(cms.elements_added, 5 + 16 + 189 + 255)

    def test_cms_check_min_called(self):
        ''' test checking number elements using min algorithm called out '''
        cms = CountMinSketch(width=1000, depth=5)
        self.assertEqual(cms.add('this is a test', 255), 255)
        self.assertEqual(cms.add('this is another test', 189), 189)
        self.assertEqual(cms.add('this is also a test', 16), 16)
        self.assertEqual(cms.add('this is something to test', 5), 5)

        self.assertEqual(cms.check('this is something to test', 'min'), 5)
        self.assertEqual(cms.check('this is also a test', 'min'), 16)
        self.assertEqual(cms.check('this is another test', 'min'), 189)
        self.assertEqual(cms.check('this is a test', 'min'), 255)
        self.assertEqual(cms.elements_added, 5 + 16 + 189 + 255)

    def test_cms_check_mean_called(self):
        ''' test checking number elements using mean algorithm called out '''
        cms = CountMinSketch(width=1000, depth=5)
        self.assertEqual(cms.add('this is a test', 255), 255)
        self.assertEqual(cms.add('this is another test', 189), 189)
        self.assertEqual(cms.add('this is also a test', 16), 16)
        self.assertEqual(cms.add('this is something to test', 5), 5)

        self.assertEqual(cms.check('this is something to test', 'mean'), 5)
        self.assertEqual(cms.check('this is also a test', 'mean'), 16)
        self.assertEqual(cms.check('this is another test', 'mean'), 189)
        self.assertEqual(cms.check('this is a test', 'mean'), 255)
        self.assertEqual(cms.elements_added, 5 + 16 + 189 + 255)

    def test_cms_check_mean_min_called(self):
        ''' test checking number elements using mean-min algorithm called
            out '''
        cms = CountMinSketch(width=1000, depth=5)
        self.assertEqual(cms.add('this is a test', 255), 255)
        self.assertEqual(cms.add('this is another test', 189), 189)
        self.assertEqual(cms.add('this is also a test', 16), 16)
        self.assertEqual(cms.add('this is something to test', 5), 5)

        self.assertEqual(cms.check('this is something to test', 'mean-min'), 5)
        self.assertEqual(cms.check('this is also a test', 'mean-min'), 16)
        self.assertEqual(cms.check('this is another test', 'mean-min'), 189)
        self.assertEqual(cms.check('this is a test', 'mean-min'), 255)
        self.assertEqual(cms.elements_added, 5 + 16 + 189 + 255)

    def test_cms_check_mean_called_even(self):
        ''' test checking number elements using mean algorithm called out when
            the depth is an even number... '''
        cms = CountMinSketch(width=1000, depth=6)
        self.assertEqual(cms.add('this is a test', 255), 255)
        self.assertEqual(cms.add('this is another test', 189), 189)
        self.assertEqual(cms.add('this is also a test', 16), 16)
        self.assertEqual(cms.add('this is something to test', 5), 5)

        self.assertEqual(cms.check('this is something to test', 'mean-min'), 5)
        self.assertEqual(cms.check('this is also a test', 'mean-min'), 16)
        self.assertEqual(cms.check('this is another test', 'mean-min'), 189)
        self.assertEqual(cms.check('this is a test', 'mean-min'), 255)
        self.assertEqual(cms.elements_added, 5 + 16 + 189 + 255)

    def test_cms_export(self):
        ''' test exporting a count-min sketch '''
        md5_val = '61d2ea9d0cb09b7bb284e1cf1a860449'
        filename = 'test.cms'
        cms = CountMinSketch(width=1000, depth=5)
        cms.add('this is a test', 100)
        cms.export(filename)
        md5_out = calc_file_md5(filename)
        os.remove(filename)

        self.assertEqual(md5_out, md5_val)

    def test_cms_load(self):
        ''' test loading a count-min sketch from file '''
        md5_val = '61d2ea9d0cb09b7bb284e1cf1a860449'
        filename = 'test.cms'
        cms = CountMinSketch(width=1000, depth=5)
        self.assertEqual(cms.add('this is a test', 100), 100)
        cms.export(filename)
        md5_out = calc_file_md5(filename)
        self.assertEqual(md5_out, md5_val)

        # try loading directly to file!
        cms2 = CountMinSketch(filepath=filename)
        self.assertEqual(cms2.elements_added, 100)
        self.assertEqual(cms2.check('this is a test'), 100)
        os.remove(filename)

    def test_cms_load_diff_hash(self):
        ''' test loading a count-min sketch from file '''
        md5_val = '61d2ea9d0cb09b7bb284e1cf1a860449'
        filename = 'test.cms'
        cms = CountMinSketch(width=1000, depth=5)
        self.assertEqual(cms.add('this is a test', 100), 100)
        cms.export(filename)
        md5_out = calc_file_md5(filename)
        self.assertEqual(md5_out, md5_val)

        cms2 = CountMinSketch(filepath=filename, hash_function=different_hash)
        self.assertEqual(cms2.elements_added, 100)
        # should not work since it is a different hash
        self.assertNotEqual(cms.check('this is a test'), True)
        self.assertNotEqual(cms.hashes('this is a test'),
                            cms2.hashes('this is a test'))
        os.remove(filename)

    def test_cms_different_hash(self):
        ''' test using a different hash function '''
        cms = CountMinSketch(width=1000, depth=5)
        hashes1 = cms.hashes('this is a test')

        cms2 = CountMinSketch(width=1000, depth=5,
                              hash_function=different_hash)
        hashes2 = cms2.hashes('this is a test')
        self.assertNotEqual(hashes1, hashes2)

    def test_cms_min_val(self):
        ''' test when we come to the bottom of the 32 bit int
            (stop overflow) '''
        cms = CountMinSketch(width=1000, depth=5)
        cms.remove('this is a test', 2147483648 + 1)
        self.assertEqual(cms.check('this is a test'), -2147483648)
        self.assertEqual(cms.elements_added, 2147483647)

    def test_cms_max_val(self):
        ''' test when we come to the top of the 32 bit int
            (stop overflow) '''
        cms = CountMinSketch(width=1000, depth=5)
        cms.add('this is a test', 2147483647 + 1)
        self.assertEqual(cms.check('this is a test'), 2147483647)
        self.assertEqual(cms.elements_added, 2147483647)

    def test_cms_clear(self):
        ''' test the clear functionality '''
        cms = CountMinSketch(width=1000, depth=5)
        self.assertEqual(cms.add('this is a test', 100), 100)
        self.assertEqual(cms.elements_added, 100)

        cms.clear()
        self.assertEqual(cms.elements_added, 0)
        self.assertEqual(cms.check('this is a test'), 0)

    def test_cms_bad_query(self):
        ''' test a bad query '''
        cms = CountMinSketch(width=1000, depth=5)
        self.assertEqual(cms.add('this is a test', 100), 100)
        self.assertRaises(SyntaxError,
                          lambda: cms.check('this is a test', 'unknown'))

    def test_cms_bad_query_msg(self):
        ''' test a bad query '''
        cms = CountMinSketch(width=1000, depth=5)
        self.assertEqual(cms.add('this is a test', 100), 100)
        try:
            cms.check('this is a test', 'unknown')
        except SyntaxError as ex:
            msg = "Invalid query type"
            self.assertEqual(str(ex), msg)

    def test_cms_str(self):
        ''' test the string representation of the count-min sketch '''
        cms = CountMinSketch(width=1000, depth=5)
        self.assertEqual(cms.add('this is a test', 100), 100)
        msg = ('Count-Min Sketch:\n'
        	   '\tWidth: 1000\n'
        	   '\tDepth: 5\n'
        	   '\tConfidence: 0.96875\n'
        	   '\tError Rate: 0.002\n'
        	   '\tElements Added: 100')
        self.assertEqual(str(cms), msg)


class TestHeavyHitters(unittest.TestCase):
    ''' Test the default heavy hitters implementation '''

    def test_heavyhitters_init_wd(self):
        ''' test initializing heavy hitters '''
        hh1 = HeavyHitters(num_hitters=1000, width=1000, depth=5)
        self.assertEqual(hh1.width, 1000)
        self.assertEqual(hh1.depth, 5)
        self.assertEqual(hh1.confidence, 0.96875)
        self.assertEqual(hh1.error_rate, 0.002)
        self.assertEqual(hh1.elements_added, 0)
        self.assertEqual(hh1.heavy_hitters, dict())
        self.assertEqual(hh1.number_heavy_hitters, 1000)

    def test_heavyhitters_init_ce(self):
        ''' test initializing heavy hitters '''
        hh1 = HeavyHitters(num_hitters=1000, confidence=0.96875,
                           error_rate=0.002)
        self.assertEqual(hh1.width, 1000)
        self.assertEqual(hh1.depth, 5)
        self.assertEqual(hh1.confidence, 0.96875)
        self.assertEqual(hh1.error_rate, 0.002)
        self.assertEqual(hh1.elements_added, 0)
        self.assertEqual(hh1.heavy_hitters, dict())
        self.assertEqual(hh1.number_heavy_hitters, 1000)

    def test_heavyhitters_add(self):
        ''' test adding things (singular) to the heavy hitters '''
        hh1 = HeavyHitters(num_hitters=2, width=1000, depth=5)
        self.assertEqual(hh1.add('this is a test'), 1)
        self.assertEqual(hh1.add('this is a test'), 2)
        self.assertEqual(hh1.add('this is a test'), 3)
        self.assertEqual(hh1.add('this is also a test'), 1)
        self.assertEqual(hh1.add('this is not a test'), 1)
        self.assertEqual(hh1.add('this is not a test'), 2)
        self.assertEqual(hh1.heavy_hitters,
                         {'this is a test': 3, 'this is not a test': 2})
        self.assertEqual(hh1.add('this is also a test'), 2)
        self.assertEqual(hh1.add('this is also a test'), 3)
        self.assertEqual(hh1.add('this is also a test'), 4)
        self.assertEqual(hh1.heavy_hitters,
                         {'this is a test': 3, 'this is also a test': 4})

    def test_heavyhitters_add_mult(self):
        ''' test adding things (multiple) to the heavy hitters '''
        hh1 = HeavyHitters(num_hitters=2, width=1000, depth=5)
        self.assertEqual(hh1.add('this is a test', 3), 3)
        self.assertEqual(hh1.add('this is also a test'), 1)
        self.assertEqual(hh1.add('this is not a test', 2), 2)
        self.assertEqual(hh1.heavy_hitters,
                         {'this is a test': 3, 'this is not a test': 2})
        self.assertEqual(hh1.add('this is also a test', 3), 4)
        self.assertEqual(hh1.heavy_hitters,
                         {'this is a test': 3, 'this is also a test': 4})
        self.assertEqual(hh1.add('this is not a test', 2), 4)
        self.assertEqual(hh1.add('this is not a test', 2), 6)
        self.assertEqual(hh1.add('this is not a test', 2), 8)
        self.assertEqual(hh1.add('this is not a test', 2), 10)
        self.assertEqual(hh1.heavy_hitters,
                         {'this is not a test': 10, 'this is also a test': 4})

    def test_hh_remove(self):
        ''' test remove from heavy hitters exception '''
        hh1 = HeavyHitters(num_hitters=2, width=1000, depth=5)
        self.assertEqual(hh1.add('this is a test', 3), 3)
        self.assertRaises(NotImplementedError,
                          lambda: hh1.remove('this is a test'))

    def test_hh_remove_msg(self):
        ''' test remove from heavy hitters exception message '''
        hh1 = HeavyHitters(num_hitters=2, width=1000, depth=5)
        self.assertEqual(hh1.add('this is a test', 3), 3)
        try:
            hh1.remove('this is a test')
        except NotImplementedError as ex:
            msg = ('Unable to remove elements in the HeavyHitters '
                   'class as it is an un supported action (and does not'
                   'make sense)!')
            self.assertEqual(str(ex), msg)

    def test_hh_clear(self):
        ''' test clearing out the heavy hitters object '''
        hh1 = HeavyHitters(num_hitters=1000, width=1000, depth=5)
        self.assertEqual(hh1.width, 1000)
        self.assertEqual(hh1.depth, 5)
        self.assertEqual(hh1.confidence, 0.96875)
        self.assertEqual(hh1.error_rate, 0.002)
        self.assertEqual(hh1.elements_added, 0)
        self.assertEqual(hh1.heavy_hitters, dict())
        self.assertEqual(hh1.number_heavy_hitters, 1000)

        self.assertEqual(hh1.add('this is a test', 3), 3)
        self.assertEqual(hh1.elements_added, 3)
        self.assertEqual(hh1.heavy_hitters, {'this is a test': 3})

        hh1.clear()
        self.assertEqual(hh1.elements_added, 0)
        self.assertEqual(hh1.heavy_hitters, dict())

    def test_hh_export(self):
        ''' test exporting a heavy hitters sketch '''
        md5_val = '61d2ea9d0cb09b7bb284e1cf1a860449'
        filename = 'test.cms'
        hh1 = HeavyHitters(num_hitters=1000, width=1000, depth=5)
        hh1.add('this is a test', 100)
        hh1.export(filename)
        md5_out = calc_file_md5(filename)
        os.remove(filename)

        self.assertEqual(md5_out, md5_val)

    def test_hh_load(self):
        ''' test loading a heavy hitters from file '''
        md5_val = '61d2ea9d0cb09b7bb284e1cf1a860449'
        filename = 'test.cms'
        hh1 = HeavyHitters(num_hitters=1000, width=1000, depth=5)
        self.assertEqual(hh1.add('this is a test', 100), 100)
        self.assertEqual(hh1.elements_added, 100)
        self.assertEqual(hh1.heavy_hitters, {'this is a test': 100})
        hh1.export(filename)
        md5_out = calc_file_md5(filename)
        self.assertEqual(md5_out, md5_val)

        # try loading directly to file!
        hh2 = HeavyHitters(num_hitters=1000, filepath=filename)
        self.assertEqual(hh2.width, 1000)
        self.assertEqual(hh2.depth, 5)
        self.assertEqual(hh2.elements_added, 100)
        self.assertEqual(hh2.check('this is a test'), 100)
        # show on load that the tracking of heavy hitters is gone
        self.assertEqual(hh2.heavy_hitters, dict())
        self.assertEqual(hh2.add('this is a test', 1), 101)
        self.assertEqual(hh2.heavy_hitters, {'this is a test': 101})
        os.remove(filename)

    def test_hh_str(self):
        ''' test the string representation of the heavy hitters sketch '''
        hh1 = HeavyHitters(num_hitters=2, width=1000, depth=5)
        self.assertEqual(hh1.add('this is a test', 100), 100)
        msg = ('Heavy Hitters Count-Min Sketch:\n'
        	   '\tWidth: 1000\n'
        	   '\tDepth: 5\n'
        	   '\tConfidence: 0.96875\n'
        	   '\tError Rate: 0.002\n'
        	   '\tElements Added: 100\n'
               '\tNumber Hitters: 2\n'
               '\tNumber Recorded: 1')
        self.assertEqual(str(hh1), msg)


class TestStreamThreshold(unittest.TestCase):
    ''' Test the default stream threshold implementation '''

    def test_streamthreshold_init_wd(self):
        ''' test initializing the stream threshold using width and depth '''
        st1 = StreamThreshold(threshold=1000, width=1000, depth=5)
        self.assertEqual(st1.width, 1000)
        self.assertEqual(st1.depth, 5)
        self.assertEqual(st1.confidence, 0.96875)
        self.assertEqual(st1.error_rate, 0.002)
        self.assertEqual(st1.elements_added, 0)
        self.assertEqual(st1.meets_threshold, dict())
        self.assertEqual(st1.threshold, 1000)

    def test_streamthreshold_init_ec(self):
        ''' test initializing the stream threshold using error rate and
            confidence '''
        st1 = StreamThreshold(threshold=1000, confidence=0.96875,
                              error_rate=0.002)
        self.assertEqual(st1.width, 1000)
        self.assertEqual(st1.depth, 5)
        self.assertEqual(st1.confidence, 0.96875)
        self.assertEqual(st1.error_rate, 0.002)
        self.assertEqual(st1.elements_added, 0)
        self.assertEqual(st1.meets_threshold, dict())
        self.assertEqual(st1.threshold, 1000)

    def test_streamthreshold_add(self):
        ''' test adding elements to the stream threshold in singular '''
        st1 = StreamThreshold(threshold=2, width=1000, depth=5)
        self.assertEqual(st1.add('this is a test'), 1)
        self.assertEqual(st1.meets_threshold, dict())
        self.assertEqual(st1.add('this is a test'), 2)
        self.assertEqual(st1.meets_threshold, {'this is a test': 2})
        self.assertEqual(st1.add('this is not a test'), 1)
        self.assertEqual(st1.meets_threshold, {'this is a test': 2})
        self.assertEqual(st1.add('this is a test'), 3)
        self.assertEqual(st1.meets_threshold, {'this is a test': 3})
        self.assertEqual(st1.add('this is not a test'), 2)
        self.assertEqual(st1.add('this is still not a test'), 1)
        self.assertEqual(st1.meets_threshold,
                         {'this is a test': 3, 'this is not a test': 2})
        self.assertEqual(st1.elements_added, 6)

    def test_streamthreshold_add_mult(self):
        ''' test adding elements to the stream threshold in multiple '''
        st1 = StreamThreshold(threshold=10, width=1000, depth=5)
        self.assertEqual(st1.add('this is a test', 5), 5)
        self.assertEqual(st1.meets_threshold, dict())
        self.assertEqual(st1.add('this is a test', 5), 10)
        self.assertEqual(st1.meets_threshold, {'this is a test': 10})
        self.assertEqual(st1.add('this is not a test', 9), 9)
        self.assertEqual(st1.meets_threshold, {'this is a test': 10})
        self.assertEqual(st1.add('this is a test', 20), 30)
        self.assertEqual(st1.meets_threshold, {'this is a test': 30})
        self.assertEqual(st1.add('this is not a test', 2), 11)
        self.assertEqual(st1.meets_threshold,
                         {'this is a test': 30, 'this is not a test': 11})
        self.assertEqual(st1.elements_added, 41)

    def test_streamthreshold_clear(self):
        ''' test clearing the stream threshold '''
        st1 = StreamThreshold(threshold=10, width=1000, depth=5)
        self.assertEqual(st1.add('this is a test', 5), 5)
        self.assertEqual(st1.meets_threshold, dict())
        self.assertEqual(st1.add('this is a test', 5), 10)
        self.assertEqual(st1.meets_threshold, {'this is a test': 10})
        self.assertEqual(st1.add('this is not a test', 9), 9)
        self.assertEqual(st1.meets_threshold, {'this is a test': 10})
        self.assertEqual(st1.add('this is a test', 20), 30)
        self.assertEqual(st1.meets_threshold, {'this is a test': 30})
        self.assertEqual(st1.add('this is not a test', 2), 11)
        self.assertEqual(st1.meets_threshold,
                         {'this is a test': 30, 'this is not a test': 11})
        self.assertEqual(st1.elements_added, 41)

        st1.clear()
        self.assertEqual(st1.meets_threshold, dict())
        self.assertEqual(st1.elements_added, 0)

    def test_streamthreshold_remove(self):
        ''' test removing elements from the stream threshold singular '''
        st1 = StreamThreshold(threshold=10, width=1000, depth=5)
        self.assertEqual(st1.add('this is a test', 5), 5)
        self.assertEqual(st1.meets_threshold, dict())
        self.assertEqual(st1.add('this is a test', 5), 10)
        self.assertEqual(st1.meets_threshold, {'this is a test': 10})
        self.assertEqual(st1.add('this is not a test', 9), 9)
        self.assertEqual(st1.meets_threshold, {'this is a test': 10})
        self.assertEqual(st1.add('this is a test', 20), 30)
        self.assertEqual(st1.meets_threshold, {'this is a test': 30})
        self.assertEqual(st1.add('this is not a test', 2), 11)
        self.assertEqual(st1.meets_threshold,
                         {'this is a test': 30, 'this is not a test': 11})
        self.assertEqual(st1.remove('this is a test'), 29)
        self.assertEqual(st1.meets_threshold,
                         {'this is a test': 29, 'this is not a test': 11})
        self.assertEqual(st1.remove('this is not a test'), 10)
        self.assertEqual(st1.remove('this is not a test'), 9)
        self.assertEqual(st1.meets_threshold, {'this is a test': 29})

        self.assertEqual(st1.elements_added, 38)

    def test_streamthreshold_rem_mult(self):
        ''' test adding elements to the stream threshold in multiple '''
        st1 = StreamThreshold(threshold=10, width=1000, depth=5)
        self.assertEqual(st1.add('this is a test', 30), 30)
        self.assertEqual(st1.add('this is not a test', 11), 11)
        self.assertEqual(st1.meets_threshold,
                         {'this is a test': 30, 'this is not a test': 11})
        self.assertEqual(st1.elements_added, 41)
        self.assertEqual(st1.remove('this is not a test', 2), 9)
        self.assertEqual(st1.meets_threshold, {'this is a test': 30})
        self.assertEqual(st1.elements_added, 39)

    def test_streamthreshold_export(self):
        ''' test exporting a stream threshold sketch '''
        md5_val = '61d2ea9d0cb09b7bb284e1cf1a860449'
        filename = 'test.cms'
        st1 = StreamThreshold(threshold=10, width=1000, depth=5)
        st1.add('this is a test', 100)
        st1.export(filename)
        md5_out = calc_file_md5(filename)
        os.remove(filename)

        self.assertEqual(md5_out, md5_val)

    def test_streamthreshold_load(self):
        ''' test loading a stream threshold sketch from file '''
        md5_val = '61d2ea9d0cb09b7bb284e1cf1a860449'
        filename = 'test.cms'
        st1 = StreamThreshold(threshold=10, width=1000, depth=5)
        self.assertEqual(st1.add('this is a test', 100), 100)
        self.assertEqual(st1.elements_added, 100)
        self.assertEqual(st1.meets_threshold, {'this is a test': 100})
        st1.export(filename)
        md5_out = calc_file_md5(filename)
        self.assertEqual(md5_out, md5_val)

        # try loading directly to file!
        st2 = StreamThreshold(threshold=10, filepath=filename)
        self.assertEqual(st2.width, 1000)
        self.assertEqual(st2.depth, 5)
        self.assertEqual(st2.elements_added, 100)
        self.assertEqual(st2.check('this is a test'), 100)
        # show on load that the tracking of stream threshold is gone
        self.assertEqual(st2.meets_threshold, dict())
        self.assertEqual(st2.add('this is a test', 1), 101)
        self.assertEqual(st2.meets_threshold, {'this is a test': 101})
        os.remove(filename)

    def test_streamthreshold_str(self):
        ''' test the string representation of the stream threshold sketch '''
        st1 = StreamThreshold(threshold=10, width=1000, depth=5)
        self.assertEqual(st1.add('this is a test', 100), 100)
        msg = ('Stream Threshold Count-Min Sketch:\n'
        	   '\tWidth: 1000\n'
        	   '\tDepth: 5\n'
        	   '\tConfidence: 0.96875\n'
        	   '\tError Rate: 0.002\n'
        	   '\tElements Added: 100\n'
               '\tThreshold: 10\n'
               '\tNumber Meeting Threshold: 1')
        self.assertEqual(str(st1), msg)
