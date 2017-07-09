# -*- coding: utf-8 -*-
''' Unittest class '''
from __future__ import (unicode_literals, absolute_import, print_function)
import unittest
import os
from hashlib import (md5)
from probables import (CountMinSketch, HeavyHitters, StreamThreshold)


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
