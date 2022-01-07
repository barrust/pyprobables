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

from probables import CountingCuckooFilter, CuckooFilterFullError

DELETE_TEMP_FILES = True


class TestCountingCuckooFilter(unittest.TestCase):
    """base Cuckoo Filter test"""

    def test_c_cuckoo_filter_default(self):
        """test counting cuckoo filter default properties"""
        cko = CountingCuckooFilter()
        self.assertEqual(10000, cko.capacity)
        self.assertEqual(4, cko.bucket_size)
        self.assertEqual(500, cko.max_swaps)
        self.assertEqual(2, cko.expansion_rate)
        self.assertEqual(True, cko.auto_expand)

    def test_c_cuckoo_filter_diff(self):
        """test counting cuckoo filter non-standard properties"""
        cko = CountingCuckooFilter(
            capacity=100,
            bucket_size=2,
            max_swaps=5,
            expansion_rate=4,
            auto_expand=False,
        )
        self.assertEqual(100, cko.capacity)
        self.assertEqual(2, cko.bucket_size)
        self.assertEqual(5, cko.max_swaps)
        self.assertEqual(4, cko.expansion_rate)
        self.assertEqual(False, cko.auto_expand)

    def test_c_cuckoo_filter_add(self):
        """test adding to the counting cuckoo filter"""
        cko = CountingCuckooFilter()
        cko.add("this is a test")
        self.assertEqual(cko.elements_added, 1)
        cko.add("this is another test")
        self.assertEqual(cko.elements_added, 2)
        cko.add("this is yet another test")
        self.assertEqual(cko.elements_added, 3)

    def test_c_cuckoo_filter_remove(self):
        """test removing from the counting cuckoo filter"""
        cko = CountingCuckooFilter()
        cko.add("this is a test")
        self.assertEqual(cko.elements_added, 1)
        cko.add("this is another test")
        self.assertEqual(cko.elements_added, 2)
        cko.add("this is yet another test")
        self.assertEqual(cko.elements_added, 3)
        self.assertEqual(cko.unique_elements, 3)
        cko.add("this is a test")
        cko.add("this is a test")
        cko.add("this is a test")
        self.assertEqual(cko.elements_added, 6)
        self.assertEqual(cko.unique_elements, 3)

        res = cko.remove("this is another test")
        self.assertTrue(res)
        self.assertEqual(cko.elements_added, 5)
        self.assertEqual(cko.unique_elements, 2)

        self.assertTrue(cko.check("this is a test"))
        self.assertFalse(cko.check("this is another test"))
        self.assertTrue(cko.check("this is yet another test"))

    def test_c_cuckoo_filter_rmv_miss(self):
        """test removing from the counting cuckoo filter when not present"""
        cko = CountingCuckooFilter()
        cko.add("this is a test")
        self.assertEqual(cko.elements_added, 1)
        cko.add("this is another test")
        self.assertEqual(cko.elements_added, 2)
        cko.add("this is yet another test")
        self.assertEqual(cko.elements_added, 3)

        res = cko.remove("this is still a test")
        self.assertFalse(res)
        self.assertEqual(cko.elements_added, 3)
        self.assertTrue(cko.check("this is a test"))
        self.assertTrue(cko.check("this is another test"))
        self.assertTrue(cko.check("this is yet another test"))

    def test_c_cuckoo_filter_lots(self):
        """test inserting lots into the counting cuckoo filter"""
        cko = CountingCuckooFilter(capacity=100, bucket_size=2, max_swaps=100)
        for i in range(125):
            cko.add(str(i))
        self.assertEqual(cko.elements_added, 125)

    def test_c_cuckoo_filter_full(self):
        """test inserting until counting cuckoo filter is full"""

        def runner():
            """runner"""
            cko = CountingCuckooFilter(capacity=100, bucket_size=2, max_swaps=100, auto_expand=False)
            for i in range(175):
                cko.add(str(i))

        self.assertRaises(CuckooFilterFullError, runner)

    def test_c_cuckoo_full_msg(self):
        """test exception message for full counting cuckoo filter"""
        try:
            cko = CountingCuckooFilter(capacity=100, bucket_size=2, max_swaps=100, auto_expand=False)
            for i in range(175):
                cko.add(str(i))
        except CuckooFilterFullError as ex:
            msg = "The CountingCuckooFilter is currently full"
            self.assertEqual(str(ex), msg)
        else:
            self.assertEqual(True, False)

    def test_c_cuckoo_idx(self):
        """test that the indexing works correctly for counting cuckoo filter
        swap"""
        cko = CountingCuckooFilter(capacity=100, bucket_size=2, max_swaps=5)
        txt = "this is a test"
        idx_1, idx_2, fingerprint = cko._generate_fingerprint_info(txt)
        index_1, index_2 = cko._indicies_from_fingerprint(fingerprint)
        self.assertEqual(idx_1, index_1)
        self.assertEqual(idx_2, index_2)

    def test_c_cuckoo_filter_check(self):
        """test checking if element in counting cuckoo filter"""
        cko = CountingCuckooFilter()
        cko.add("this is a test")
        cko.add("this is another test")
        cko.add("this is yet another test")
        self.assertEqual(cko.check("this is a test"), True)
        self.assertEqual(cko.check("this is another test"), True)
        self.assertEqual(cko.check("this is yet another test"), True)
        self.assertEqual(cko.check("this is not another test"), False)
        self.assertEqual(cko.check("this is not a test"), False)

    def test_c_cuckoo_filter_in(self):
        """test checking using 'in' counting cuckoo filter"""
        cko = CountingCuckooFilter()
        cko.add("this is a test")
        cko.add("this is another test")
        cko.add("this is yet another test")
        self.assertEqual("this is a test" in cko, True)
        self.assertEqual("this is another test" in cko, True)
        self.assertEqual("this is yet another test" in cko, True)
        self.assertEqual("this is not another test" in cko, False)
        self.assertEqual("this is not a test" in cko, False)

    def test_c_cuckoo_filter_dup_add(self):
        """test adding same item multiple times counting cuckoo filter"""
        cko = CountingCuckooFilter()
        cko.add("this is a test")
        cko.add("this is another test")
        cko.add("this is yet another test")
        self.assertEqual(cko.elements_added, 3)
        cko.add("this is a test")
        cko.add("this is another test")
        cko.add("this is yet another test")
        self.assertEqual(cko.elements_added, 6)
        self.assertEqual(cko.unique_elements, 3)

    def test_c_cuckoo_filter_l_fact(self):
        """test the load factor of the counting cuckoo filter"""
        cko = CountingCuckooFilter(capacity=100, bucket_size=2, max_swaps=10)
        self.assertEqual(cko.load_factor(), 0.0)
        for i in range(50):
            cko.add(str(i))
        self.assertEqual(cko.load_factor(), 0.25)
        for i in range(50):
            cko.add(str(i + 50))

        if cko.capacity == 200:  # self expanded
            self.assertEqual(cko.load_factor(), 0.25)
        else:
            self.assertEqual(cko.load_factor(), 0.50)

        for i in range(100):
            cko.add(str(i))
        if cko.capacity == 200:  # self expanded
            self.assertEqual(cko.load_factor(), 0.25)
        else:
            self.assertEqual(cko.load_factor(), 0.50)

    def test_c_cuckoo_filter_export(self):
        """test exporting a counting cuckoo filter"""
        md5sum = "6a98c2df1ec9fbb4f75f8e6392696b9b"
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".cck", delete=DELETE_TEMP_FILES) as fobj:
            cko = CountingCuckooFilter(capacity=1000, bucket_size=2, auto_expand=False)
            for i in range(100):
                cko.add(str(i))

            cko.export(fobj.name)
            md5_out = calc_file_md5(fobj.name)
            self.assertEqual(md5sum, md5_out)

    def test_c_cuckoo_filter_bytes(self):
        """test exporting a counting cuckoo filter"""
        md5sum = "6a98c2df1ec9fbb4f75f8e6392696b9b"
        cko = CountingCuckooFilter(capacity=1000, bucket_size=2, auto_expand=False)
        for i in range(100):
            cko.add(str(i))
        md5_out = hashlib.md5(bytes(cko)).hexdigest()
        self.assertEqual(md5sum, md5_out)

    def test_c_cuckoo_filter_frombytes(self):
        """test initializing a counting cuckoo filter frombytes"""
        cko = CountingCuckooFilter(capacity=1000, bucket_size=2, auto_expand=False)
        for i in range(100):
            cko.add(str(i))
        bytes_out = bytes(cko)

        cko2 = CountingCuckooFilter.frombytes(bytes_out)

        self.assertEqual(bytes_out, bytes(cko2))
        for i in range(100):
            self.assertTrue(cko2.check(str(i)))
        self.assertFalse(cko2.check("999"))

    def test_c_cuckoo_filter_load(self):
        """test loading a saved counting cuckoo filter"""
        md5sum = "6a98c2df1ec9fbb4f75f8e6392696b9b"
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".cck", delete=DELETE_TEMP_FILES) as fobj:
            cko = CountingCuckooFilter(capacity=1000, bucket_size=2, auto_expand=False)
            for i in range(100):
                cko.add(str(i))

            cko.export(fobj.name)
            md5_out = calc_file_md5(fobj.name)
            self.assertEqual(md5sum, md5_out)

            ckf = CountingCuckooFilter(filepath=fobj.name)
            for i in range(100):
                self.assertEqual(ckf.check(str(i)), 1)

            self.assertEqual(1000, ckf.capacity)
            self.assertEqual(2, ckf.bucket_size)
            self.assertEqual(500, ckf.max_swaps)
            self.assertEqual(0.05, ckf.load_factor())

    def test_c_cuckoo_filter_expand_els(self):
        """test out the expansion of the counting cuckoo filter"""
        cko = CountingCuckooFilter()
        for i in range(200):
            cko.add(str(i))
        cko.expand()
        for i in range(200):
            self.assertGreater(cko.check(str(i)), 0)
        self.assertEqual(20000, cko.capacity)

    def test_c_cuckoo_filter_auto_exp(self):
        """test inserting until counting cuckoo filter is full"""
        cko = CountingCuckooFilter(capacity=100, bucket_size=2, max_swaps=100)
        for i in range(375):  # this would fail if it doesn't expand
            cko.add(str(i))
        self.assertEqual(400, cko.capacity)
        self.assertEqual(375, cko.elements_added)
        for i in range(375):
            self.assertGreater(cko.check(str(i)), 0)

    def test_c_cuckoo_filter_bin(self):
        """test the cuckoo bin repr"""
        cko = CountingCuckooFilter(capacity=1, bucket_size=2, max_swaps=100)
        cko.add("this is a test")
        self.assertEqual("[(fingerprint:4280557824 count:1)]", str(cko.buckets[0]))

    def test_c_cuckoo_filter_str(self):
        """test the str representation of the counting cuckoo filter"""
        cko = CountingCuckooFilter(capacity=100, bucket_size=2, max_swaps=100)
        for i in range(75):
            cko.add(str(i))
        msg = (
            "CountingCuckooFilter:\n"
            "\tCapacity: 100\n"
            "\tTotal Bins: 200\n"
            "\tLoad Factor: 37.5%\n"
            "\tInserted Elements: 75\n"
            "\tMax Swaps: 100\n"
            "\tExpansion Rate: 2\n"
            "\tAuto Expand: True"
        )
        self.assertEqual(str(cko), msg)


class TestCuckooFilterErrorRate(unittest.TestCase):
    """Test CountingCuckooFilter using Error Rate"""

    def test_c_cuckoo_filter_er_default(self):
        """test cuckoo filter default properties"""
        cko = CountingCuckooFilter.init_error_rate(0.00001)
        self.assertEqual(10000, cko.capacity)
        self.assertEqual(4, cko.bucket_size)
        self.assertEqual(500, cko.max_swaps)
        self.assertEqual(2, cko.expansion_rate)
        self.assertEqual(True, cko.auto_expand)
        self.assertEqual(3, cko.fingerprint_size)
        self.assertEqual(20, cko.fingerprint_size_bits)
        self.assertEqual(0.00001, cko.error_rate)

    def test_c_cuckoo_filter_er_add_check(self):
        """test adding to the cuckoo filter"""
        cko = CountingCuckooFilter.init_error_rate(0.00001)
        cko.add("this is a test")
        self.assertEqual(cko.elements_added, 1)
        cko.add("this is another test")
        self.assertEqual(cko.elements_added, 2)
        cko.add("this is yet another test")
        self.assertEqual(cko.elements_added, 3)

        # check
        self.assertEqual(cko.check("this is a test"), True)
        self.assertEqual(cko.check("this is another test"), True)
        self.assertEqual(cko.check("this is yet another test"), True)
        self.assertEqual(cko.check("this is not another test"), False)
        self.assertEqual(cko.check("this is not a test"), False)

        # use of `in`
        self.assertEqual("this is a test" in cko, True)
        self.assertEqual("this is another test" in cko, True)
        self.assertEqual("this is yet another test" in cko, True)
        self.assertEqual("this is not another test" in cko, False)
        self.assertEqual("this is not a test" in cko, False)

    def test_c_cuckoo_filter_er_export(self):
        """test exporting a cuckoo filter"""
        md5sum = "f68767bd97b21426f5d2315fb38961ad"
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".cko", delete=DELETE_TEMP_FILES) as fobj:
            cko = CountingCuckooFilter.init_error_rate(0.00001)
            for i in range(1000):
                cko.add(str(i))
            cko.export(fobj.name)
            md5_out = calc_file_md5(fobj.name)
            self.assertEqual(md5sum, md5_out)

    def test_c_cuckoo_filter_load(self):
        """test loading a saved cuckoo filter"""
        md5sum = "88bc3a08bfc967f9ba60e9d57c21207f"
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".cko", delete=DELETE_TEMP_FILES) as fobj:
            cko = CountingCuckooFilter.init_error_rate(0.00001)
            for i in range(1000):
                cko.add(str(i))
                if i % 2 == 1:
                    cko.add(str(i))
            cko.export(fobj.name)
            md5_out = calc_file_md5(fobj.name)
            self.assertEqual(md5sum, md5_out)

            ckf = CountingCuckooFilter.load_error_rate(error_rate=0.00001, filepath=fobj.name)
            for i in range(1000):
                self.assertEqual(ckf.check(str(i)), (i % 2) + 1)

            self.assertEqual(10000, ckf.capacity)
            self.assertEqual(4, ckf.bucket_size)
            self.assertEqual(500, ckf.max_swaps)
            self.assertEqual(2, ckf.expansion_rate)
            self.assertEqual(True, ckf.auto_expand)
            self.assertEqual(20, ckf.fingerprint_size_bits)
            self.assertEqual(3, ckf.fingerprint_size)
            self.assertEqual(0.00001, ckf.error_rate)
            self.assertEqual(0.025, ckf.load_factor())

    def test_c_cuckoo_filter_er_bytes(self):
        """test exporting a cuckoo filter to bytes"""
        md5sum = "f68767bd97b21426f5d2315fb38961ad"
        cko = CountingCuckooFilter.init_error_rate(0.00001)
        for i in range(1000):
            cko.add(str(i))
        md5_out = hashlib.md5(bytes(cko)).hexdigest()
        self.assertEqual(md5sum, md5_out)

    def test_c_cuckoo_filter_er_frombytes(self):
        """test initializing a couting cuckoo filter from bytes"""
        cko = CountingCuckooFilter.init_error_rate(0.00001, capacity=3000)
        for i in range(1000):
            cko.add(str(i))
        bytes_out = bytes(cko)

        cko2 = CountingCuckooFilter.frombytes(bytes_out, error_rate=0.00001)

        self.assertEqual(bytes_out, bytes(cko2))
        for i in range(1000):
            self.assertTrue(cko2.check(str(i)))
        self.assertFalse(cko2.check("9999"))
        self.assertEqual(cko2.capacity, 3000)

    def test_c_cuckoo_filter_er_remove(self):
        """test removing from the counting cuckoo filter"""
        cko = CountingCuckooFilter.init_error_rate(0.00001)
        cko.add("this is a test")
        self.assertEqual(cko.elements_added, 1)
        cko.add("this is another test")
        self.assertEqual(cko.elements_added, 2)
        cko.add("this is yet another test")
        self.assertEqual(cko.elements_added, 3)
        self.assertEqual(cko.unique_elements, 3)
        cko.add("this is a test")
        cko.add("this is a test")
        cko.add("this is a test")
        self.assertEqual(cko.elements_added, 6)
        self.assertEqual(cko.unique_elements, 3)

        res = cko.remove("this is another test")
        self.assertTrue(res)
        self.assertEqual(cko.elements_added, 5)
        self.assertEqual(cko.unique_elements, 2)

        self.assertTrue(cko.check("this is a test"))
        self.assertFalse(cko.check("this is another test"))
        self.assertTrue(cko.check("this is yet another test"))


if __name__ == "__main__":
    unittest.main()
