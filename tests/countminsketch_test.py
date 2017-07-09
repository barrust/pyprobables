# -*- coding: utf-8 -*-
''' Unittest class '''
from __future__ import (unicode_literals, absolute_import, print_function)
import unittest
import os
from hashlib import (md5)
from probables import (CountMinSketch, HeavyHitters, StreamThreshold)
from . utilities import(calc_file_md5)


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
                   'Count-Min Sketch: \n'
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


class TestHeavyHitters(unittest.TestCase):
    ''' Test the default heavy hitters implementation '''
    def test_heavyhitters(self):
        pass


class TestStreamThreshold(unittest.TestCase):
    ''' Test the default stream threshold implementation '''
    def test_streamthreshold(self):
        pass
