#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" Unittest class """

import hashlib
import os
import sys
import unittest
from pathlib import Path
from tempfile import NamedTemporaryFile

this_dir = Path(__file__).parent
sys.path.insert(0, str(this_dir))
sys.path.insert(0, str(this_dir.parent))

from utilities import calc_file_md5

from probables import ExpandingBloomFilter, RotatingBloomFilter
from probables.exceptions import RotatingBloomFilterError

DELETE_TEMP_FILES = True


class TestExpandingBloomFilter(unittest.TestCase):
    """Test ExpandingBloomFilter"""

    def test_ebf_init(self):
        """test the initialization of an expanding bloom filter"""
        blm = ExpandingBloomFilter(est_elements=10, false_positive_rate=0.05)
        self.assertEqual(blm.expansions, 0)
        self.assertEqual(blm.false_positive_rate, 0.05)
        self.assertEqual(blm.estimated_elements, 10)
        self.assertEqual(blm.elements_added, 0)

    def test_ebf_add_lots(self):
        """test adding "lots" of elements to force the expansion"""
        blm = ExpandingBloomFilter(est_elements=10, false_positive_rate=0.05)
        for i in range(100):
            blm.add("{}".format(i), True)
        self.assertEqual(blm.expansions, 9)

    def test_ebf_add_lots_without_force(self):
        """testing adding "lots" but force them to be inserted multiple times"""
        blm = ExpandingBloomFilter(est_elements=10, false_positive_rate=0.05)
        # simulate false positives... notice it didn't grow a few...
        for i in range(120):
            blm.add("{}".format(i))
        self.assertEqual(blm.expansions, 8)
        self.assertEqual(blm.elements_added, 120)

    def test_ebf_check(self):
        """ensure that checking the expanding bloom filter works"""
        blm = ExpandingBloomFilter(est_elements=30, false_positive_rate=0.05)
        # expand it out some first!
        for i in range(100):
            blm.add("{}".format(i))
        blm.add("this is a test")
        blm.add("this is another test")
        self.assertGreater(blm.expansions, 1)
        self.assertEqual(blm.check("this is a test"), True)
        self.assertEqual(blm.check("this is another test"), True)
        self.assertEqual(blm.check("this is yet another test!"), False)
        self.assertEqual(blm.check("this is not another test"), False)
        self.assertEqual(blm.elements_added, 102)

    def test_ebf_contains(self):
        """ensure that "in" functionality for the expanding bloom filter works"""
        blm = ExpandingBloomFilter(est_elements=30, false_positive_rate=0.05)
        # expand it out some first!
        for i in range(100):
            blm.add("{}".format(i))
        blm.add("this is a test")
        blm.add("this is another test")
        self.assertGreater(blm.expansions, 1)
        self.assertEqual("this is a test" in blm, True)
        self.assertEqual("this is another test" in blm, True)
        self.assertEqual("this is yet another test!" in blm, False)
        self.assertEqual("this is not another test" in blm, False)

    def test_ebf_push(self):
        """ensure that we are able to push new Bloom Filters"""
        blm = ExpandingBloomFilter(est_elements=25, false_positive_rate=0.05)
        self.assertEqual(blm.expansions, 0)
        blm.push()
        self.assertEqual(blm.expansions, 1)
        self.assertEqual(blm.elements_added, 0)
        blm.push()
        self.assertEqual(blm.expansions, 2)
        self.assertEqual(blm.elements_added, 0)
        blm.push()
        self.assertEqual(blm.expansions, 3)
        self.assertEqual(blm.elements_added, 0)

    def test_ebf_export(self):
        """basic expanding Bloom Filter export test"""
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".ebf", delete=DELETE_TEMP_FILES) as fobj:
            blm = ExpandingBloomFilter(est_elements=25, false_positive_rate=0.05)
            blm.export(fobj.name)
            self.assertEqual(calc_file_md5(fobj.name), "eb5769ae9babdf7b37d6ce64d58812bc")

    def test_ebf_bytes(self):
        """basic expanding Bloom Filter export bytes test"""
        blm = ExpandingBloomFilter(est_elements=25, false_positive_rate=0.05)
        self.assertEqual(hashlib.md5(bytes(blm)).hexdigest(), "eb5769ae9babdf7b37d6ce64d58812bc")

    def test_ebf_frombytes(self):
        """expanding Bloom Filter load bytes test"""
        blm = ExpandingBloomFilter(est_elements=25, false_positive_rate=0.05)
        for i in range(105):
            blm.add(str(i))
        bytes_out = bytes(blm)

        blm2 = ExpandingBloomFilter.frombytes(bytes_out)
        self.assertEqual(blm2.expansions, 3)
        self.assertEqual(blm2.false_positive_rate, 0.05000000074505806)
        self.assertEqual(blm2.estimated_elements, 25)
        self.assertEqual(blm2.elements_added, 105)
        self.assertEqual(bytes(blm2), bytes(blm))

        for i in range(105):
            self.assertTrue(blm.check(str(i)))

    def test_ebf_import_empty(self):
        """test that expanding Bloom Filter is correct on import"""
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".ebf", delete=DELETE_TEMP_FILES) as fobj:
            blm = ExpandingBloomFilter(est_elements=25, false_positive_rate=0.05)
            blm.export(fobj.name)
            self.assertEqual(calc_file_md5(fobj.name), "eb5769ae9babdf7b37d6ce64d58812bc")

            blm2 = ExpandingBloomFilter(filepath=fobj.name)
            for bloom in blm2._blooms:
                self.assertEqual(bloom.elements_added, 0)

    def test_ebf_import_non_empty(self):
        """test expanding Bloom Filter import when non-empty"""
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".ebf", delete=DELETE_TEMP_FILES) as fobj:
            blm = ExpandingBloomFilter(est_elements=25, false_positive_rate=0.05)
            for i in range(15):
                blm.add("{}".format(i))
                blm.push()

            blm.export(fobj.name)

            blm2 = ExpandingBloomFilter(filepath=fobj.name)
            self.assertEqual(blm2.expansions, 15)
            for i in range(15):
                self.assertEqual("{}".format(i) in blm2, True)

            # check for things that are not there!
            for i in range(99, 125):
                self.assertEqual("{}".format(i) in blm2, False)


class TestRotatingBloomFilter(unittest.TestCase):
    """Test RotatingBloomFilter"""

    def test_rbf_init(self):
        """test the initialization of an rotating bloom filter"""
        blm = RotatingBloomFilter(est_elements=10, false_positive_rate=0.05, max_queue_size=10)
        self.assertEqual(blm.expansions, 0)
        self.assertEqual(blm.max_queue_size, 10)

    def test_rbf_rotate(self):
        """test that the bloom filter rotates the first bloom off the stack"""
        blm = RotatingBloomFilter(est_elements=10, false_positive_rate=0.05, max_queue_size=5)
        self.assertEqual(blm.expansions, 0)
        blm.add("test")
        self.assertEqual(blm.expansions, 0)
        for i in range(10):
            blm.add("{}".format(i), force=True)
        self.assertEqual(blm.expansions, 1)
        self.assertEqual(blm.current_queue_size, 2)
        self.assertEqual(blm.check("test"), True)

        for i in range(10, 20):
            blm.add("{}".format(i), force=True)
        self.assertEqual(blm.check("test"), True)
        self.assertEqual(blm.current_queue_size, 3)

        for i in range(20, 30):
            blm.add("{}".format(i), force=True)
        self.assertEqual(blm.check("test"), True)
        self.assertEqual(blm.current_queue_size, 4)

        for i in range(30, 40):
            blm.add("{}".format(i), force=True)
        self.assertEqual(blm.check("test"), True)
        self.assertEqual(blm.current_queue_size, 5)

        for i in range(40, 50):
            blm.add("{}".format(i), force=True)
        self.assertEqual(blm.check("test"), False)  # it should roll off
        self.assertEqual(blm.current_queue_size, 5)

        self.assertEqual(blm.elements_added, 51)

    def test_rbf_push_pop(self):
        """test forcing push and pop"""
        blm = RotatingBloomFilter(est_elements=10, false_positive_rate=0.05, max_queue_size=5)
        self.assertEqual(blm.current_queue_size, 1)
        blm.add("test")
        blm.push()
        self.assertEqual(blm.current_queue_size, 2)
        self.assertEqual("test" in blm, True)
        blm.push()
        self.assertEqual(blm.current_queue_size, 3)
        self.assertEqual("test" in blm, True)
        blm.push()
        self.assertEqual(blm.current_queue_size, 4)
        self.assertEqual("test" in blm, True)
        blm.push()
        self.assertEqual(blm.current_queue_size, 5)
        self.assertEqual("test" in blm, True)
        blm.push()
        self.assertEqual(blm.current_queue_size, 5)
        self.assertEqual("test" in blm, False)

        # test popping
        blm.add("that")
        blm.pop()
        self.assertEqual(blm.current_queue_size, 4)
        self.assertEqual("that" in blm, True)
        blm.pop()
        self.assertEqual(blm.current_queue_size, 3)
        self.assertEqual("that" in blm, True)
        blm.pop()
        self.assertEqual(blm.current_queue_size, 2)
        self.assertEqual("that" in blm, True)
        blm.pop()
        self.assertEqual(blm.current_queue_size, 1)
        self.assertEqual("that" in blm, True)

    def test_rbf_pop_exception(self):
        """ensure the correct exception is thrown"""
        blm = RotatingBloomFilter(est_elements=10, false_positive_rate=0.05, max_queue_size=5)
        self.assertRaises(RotatingBloomFilterError, lambda: blm.pop())

    def test_rbf_pop_exception_msg(self):
        """rotating bloom filter error: check the resulting error message"""
        blm = RotatingBloomFilter(est_elements=10, false_positive_rate=0.05, max_queue_size=5)
        try:
            blm.pop()
        except RotatingBloomFilterError as ex:
            msg = "Popping a Bloom Filter will result in an unusable system!"
            self.assertEqual(str(ex), msg)
        except:
            self.assertEqual(True, False)

    def test_rfb_basic_export(self):
        """basic rotating Bloom Filter export test"""
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".rbf", delete=DELETE_TEMP_FILES) as fobj:
            blm = RotatingBloomFilter(est_elements=25, false_positive_rate=0.05)
            blm.export(fobj.name)
            self.assertEqual(calc_file_md5(fobj.name), "eb5769ae9babdf7b37d6ce64d58812bc")

    def test_rfb_basic_bytes(self):
        """basic rotating Bloom Filter export bytes test"""
        blm = RotatingBloomFilter(est_elements=25, false_positive_rate=0.05)
        self.assertEqual(hashlib.md5(bytes(blm)).hexdigest(), "eb5769ae9babdf7b37d6ce64d58812bc")

    def test_rfb_from_bytes(self):
        """basic rotating Bloom Filter export bytes test"""
        blm = RotatingBloomFilter(est_elements=25, false_positive_rate=0.05, max_queue_size=3)
        for i in range(105):
            blm.add(str(i))
        bytes_out = bytes(blm)

        blm2 = RotatingBloomFilter.frombytes(bytes_out, max_queue_size=3)
        self.assertEqual(blm2.expansions, 2)
        self.assertEqual(blm2.false_positive_rate, 0.05000000074505806)
        self.assertEqual(blm2.estimated_elements, 25)
        self.assertEqual(blm2.elements_added, 105)
        self.assertEqual(blm2.current_queue_size, 3)
        self.assertEqual(bytes(blm2), bytes(blm))
        for i in range(105):
            self.assertEqual(blm.check(str(i)), blm2.check(str(i)))

    def test_rbf_import_empty(self):
        """test that rotating Bloom Filter is correct on import"""
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".rbf", delete=DELETE_TEMP_FILES) as fobj:
            blm = RotatingBloomFilter(est_elements=25, false_positive_rate=0.05)
            blm.export(fobj.name)
            self.assertEqual(calc_file_md5(fobj.name), "eb5769ae9babdf7b37d6ce64d58812bc")

            blm2 = ExpandingBloomFilter(filepath=fobj.name)
            for bloom in blm2._blooms:
                self.assertEqual(bloom.elements_added, 0)

    def test_rbf_non_basic_import(self):
        """test that the imported rotating Bloom filter is correct"""
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".rbf", delete=DELETE_TEMP_FILES) as fobj:
            blm = RotatingBloomFilter(est_elements=25, false_positive_rate=0.05)
            for i in range(15):
                blm.add("{}".format(i))
                blm.push()
            blm.export(fobj.name)

            blm2 = RotatingBloomFilter(filepath=fobj.name)
            # test those that should be popped off...
            for i in range(5):
                self.assertEqual("{}".format(i) in blm2, False)
            # test things that would not be popped
            for i in range(6, 15):
                self.assertEqual("{}".format(i) in blm2, True)
            self.assertEqual(blm2.current_queue_size, 10)
            self.assertEqual(blm2.expansions, 9)
            self.assertEqual(blm2.elements_added, 15)


if __name__ == "__main__":
    unittest.main()
