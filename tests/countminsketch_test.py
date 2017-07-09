# -*- coding: utf-8 -*-
''' Unittest class '''
from __future__ import (unicode_literals, absolute_import, print_function)
import unittest
import os
from hashlib import (md5)
from probables import (CountMinSketch, HeavyHitters, StreamThreshold)


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


class TestHeavyHitters(unittest.TestCase):
    ''' Test the default heavy hitters implementation '''
    def test_heavyhitters(self):
        pass


class TestStreamThreshold(unittest.TestCase):
    ''' Test the default stream threshold implementation '''
    def test_streamthreshold(self):
        pass
