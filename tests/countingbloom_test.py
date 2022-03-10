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

from utilities import calc_file_md5, different_hash

from probables import CountingBloomFilter
from probables.exceptions import InitializationError

DELETE_TEMP_FILES = True


class TestCountingBloomFilter(unittest.TestCase):
    """Test the default bloom filter implementation"""

    def test_cbf_init(self):
        """test version information"""
        blm = CountingBloomFilter(est_elements=10, false_positive_rate=0.05)
        self.assertEqual(blm.false_positive_rate, 0.05000000074505806)
        self.assertEqual(blm.estimated_elements, 10)
        self.assertEqual(blm.number_hashes, 4)
        self.assertEqual(blm.number_bits, 63)
        self.assertEqual(blm.elements_added, 0)
        self.assertEqual(blm.is_on_disk, False)
        self.assertEqual(blm.bloom_length, 63)

    def test_cbf_ea(self):
        """test elements added is correct"""
        blm = CountingBloomFilter(est_elements=10, false_positive_rate=0.05)
        self.assertEqual(blm.elements_added, 0)
        blm.add("this is a test")
        self.assertEqual(blm.elements_added, 1)

    def test_cbf_ea_diff_hash(self):
        """test elements added is correct"""
        blm1 = CountingBloomFilter(est_elements=10, false_positive_rate=0.05, hash_function=different_hash)
        hsh1 = blm1.hashes("this is a test")
        blm2 = CountingBloomFilter(est_elements=10, false_positive_rate=0.05)
        hsh2 = blm2.hashes("this is a test")
        self.assertNotEqual(hsh1, hsh2)

    def test_cbf_check(self):
        """ensure that checking the bloom filter works"""
        blm = CountingBloomFilter(est_elements=10, false_positive_rate=0.05)
        blm.add("this is a test")
        blm.add("this is another test")
        self.assertEqual(blm.check("this is a test"), True)
        self.assertEqual(blm.check("this is another test"), True)
        self.assertEqual(blm.check("this is yet another test"), False)
        self.assertEqual(blm.check("this is not another test"), False)

    def test_cbf_in_check(self):
        """check that the in construct works"""
        blm = CountingBloomFilter(est_elements=10, false_positive_rate=0.05)
        blm.add("this is a test")
        blm.add("this is another test")
        self.assertEqual("this is a test" in blm, True)
        self.assertEqual("this is another test" in blm, True)
        self.assertEqual("this is yet another test" in blm, False)
        self.assertEqual("this is not another test" in blm, False)

    def test_cbf_stats(self):
        """test that the information in the stats is correct"""
        msg = (
            "CountingBloom:\n"
            "\tbits: 63\n"
            "\testimated elements: 10\n"
            "\tnumber hashes: 4\n"
            "\tmax false positive rate: 0.050000\n"
            "\telements added: 10\n"
            "\tcurrent false positive rate: 0.048806\n"
            "\tis on disk: no\n"
            "\tindex fullness: 0.634921\n"
            "\tmax index usage: 3\n"
            "\tmax index id: 56\n"
            "\tcalculated elements: 10\n"
        )
        blm = CountingBloomFilter(est_elements=10, false_positive_rate=0.05)
        for i in range(0, 10):
            blm.add("this is a test {0}".format(i))
        stats = str(blm)
        self.assertEqual(stats, msg)

    def test_cbf_clear(self):
        """test clearing out the bloom filter"""
        blm = CountingBloomFilter(est_elements=10, false_positive_rate=0.05)
        self.assertEqual(blm.elements_added, 0)
        for i in range(0, 10):
            blm.add("this is a test {0}".format(i))
        self.assertEqual(blm.elements_added, 10)

        blm.clear()
        self.assertEqual(blm.elements_added, 0)
        for idx in range(blm.bloom_length):
            self.assertEqual(blm._get_element(idx), 0)

    def test_cbf_export_file(self):
        """test exporting bloom filter to file"""
        md5_val = "0b83c837da30e25f768f0527c039d341"
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".cbm", delete=DELETE_TEMP_FILES) as fobj:
            blm = CountingBloomFilter(est_elements=10, false_positive_rate=0.01)
            blm.add("test")
            blm.add("out")
            blm.add("the")
            blm.add("counting")
            blm.add("bloom")
            blm.add("filter")

            blm.add("test")
            blm.add("Test")
            blm.add("out")
            blm.add("test")
            blm.export(fobj.name)

            md5_out = calc_file_md5(fobj.name)
            self.assertEqual(md5_out, md5_val)

    def test_cbf_bytes(self):
        """test exporting counting bloom filter to bytes"""
        md5_val = "0b83c837da30e25f768f0527c039d341"
        blm = CountingBloomFilter(est_elements=10, false_positive_rate=0.01)
        blm.add("test")
        blm.add("out")
        blm.add("the")
        blm.add("counting")
        blm.add("bloom")
        blm.add("filter")

        blm.add("test")
        blm.add("Test")
        blm.add("out")
        blm.add("test")

        md5_out = hashlib.md5(bytes(blm)).hexdigest()
        self.assertEqual(md5_out, md5_val)

    def test_cbf_frombytes(self):
        """test loading counting bloom filter from bytes"""
        blm = CountingBloomFilter(est_elements=10, false_positive_rate=0.05)
        blm.add("test")
        blm.add("out")
        blm.add("the")
        blm.add("counting")
        blm.add("bloom")
        blm.add("filter")

        blm.add("test")
        blm.add("Test")
        blm.add("out")
        blm.add("test")
        bytes_out = bytes(blm)

        blm2 = CountingBloomFilter.frombytes(bytes_out)
        self.assertEqual(blm.false_positive_rate, 0.05000000074505806)
        self.assertEqual(blm.estimated_elements, 10)
        self.assertEqual(blm.number_hashes, 4)
        self.assertEqual(blm.number_bits, 63)
        self.assertEqual(blm.elements_added, 10)
        self.assertEqual(blm.is_on_disk, False)
        self.assertEqual(blm.bloom_length, 63)

        self.assertEqual(bytes(blm2), bytes(blm))
        self.assertTrue(blm2.check("test"))
        self.assertFalse(blm2.check("something"))

    def test_cbf_load_file(self):
        """test loading bloom filter from file"""
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".cbm", delete=DELETE_TEMP_FILES) as fobj:
            blm = CountingBloomFilter(est_elements=10, false_positive_rate=0.05)
            blm.add("this is a test")
            blm.export(fobj.name)

            blm2 = CountingBloomFilter(filepath=fobj.name)
            self.assertEqual("this is a test" in blm2, True)
            self.assertEqual("this is not a test" in blm2, False)

    def test_cbf_load_invalid_file(self):
        """test importing a bloom filter from an invalid filepath"""
        filename = "invalid.cbm"
        self.assertRaises(InitializationError, lambda: CountingBloomFilter(filepath=filename))

    def test_cbf_invalid_params_msg(self):
        """test importing a bloom filter from an invalid filepath msg"""
        filename = "invalid.cbm"
        msg = "Insufecient parameters to set up the Counting Bloom Filter"
        try:
            CountingBloomFilter(filepath=filename)
        except InitializationError as ex:
            self.assertEqual(str(ex), msg)

    def test_cbf_export_hex(self):
        """test the exporting of the bloom filter to a hex string"""
        h_val = (
            "01000000000000000100000002000000000000000100000001000000"
            "00000000000000000000000001000000000000000000000002000000"
            "00000000010000000200000000000000000000000000000001000000"
            "00000000000000000200000000000000010000000200000000000000"
            "00000000000000000100000000000000000000000100000000000000"
            "01000000020000000000000000000000000000000100000001000000"
            "00000000010000000000000001000000020000000000000000000000"
            "01000000000000000100000001000000010000000000000001000000"
            "03000000000000000100000001000000000000000000000001000000"
            "000000000000000a000000000000000a3d4ccccd"
        )

        blm = CountingBloomFilter(est_elements=10, false_positive_rate=0.05)
        for i in range(0, 10):
            tmp = "this is a test {0}".format(i)
            blm.add(tmp)
        hex_out = blm.export_hex()

        self.assertEqual(hex_out, h_val)

    def test_cbf_load_hex(self):
        """test importing a bloom filter from hex value"""
        h_val = (
            "01000000000000000100000002000000000000000100000001000000"
            "00000000000000000000000001000000000000000000000002000000"
            "00000000010000000200000000000000000000000000000001000000"
            "00000000000000000200000000000000010000000200000000000000"
            "00000000000000000100000000000000000000000100000000000000"
            "01000000020000000000000000000000000000000100000001000000"
            "00000000010000000000000001000000020000000000000000000000"
            "01000000000000000100000001000000010000000000000001000000"
            "03000000000000000100000001000000000000000000000001000000"
            "000000000000000a000000000000000a3d4ccccd"
        )
        blm = CountingBloomFilter(hex_string=h_val)
        self.assertEqual("this is a test 0" in blm, True)
        self.assertEqual("this is a test 1" in blm, True)
        self.assertEqual("this is a test 2" in blm, True)
        self.assertEqual("this is a test 3" in blm, True)
        self.assertEqual("this is a test 4" in blm, True)
        self.assertEqual("this is a test 5" in blm, True)
        self.assertEqual("this is a test 6" in blm, True)
        self.assertEqual("this is a test 7" in blm, True)
        self.assertEqual("this is a test 8" in blm, True)
        self.assertEqual("this is a test 9" in blm, True)

        self.assertEqual("this is a test 10" in blm, False)
        self.assertEqual("this is a test 11" in blm, False)
        # self.assertEqual("this is a test 12" in blm, False)  # This is a false positive!
        self.assertEqual("this is a test 15" in blm, False)

    def test_cbf_load_invalid_hex(self):
        """test importing a bloom filter from an invalid hex value"""
        h_val = (
            "01000300000000010002000002010102000000000000010000010000000"
            "10100020100010101000002000101000201000000020001000001010000"
            "01020002000000000000000a000000000000000a3d4ccccQ"
        )
        self.assertRaises(InitializationError, lambda: CountingBloomFilter(hex_string=h_val))

    def test_cbf_export_c_header(self):
        """test exporting a c header"""
        hex_val = (
            "01000000000000000100000002000000000000000100000001000000"
            "00000000000000000000000001000000000000000000000002000000"
            "00000000010000000200000000000000000000000000000001000000"
            "00000000000000000200000000000000010000000200000000000000"
            "00000000000000000100000000000000000000000100000000000000"
            "01000000020000000000000000000000000000000100000001000000"
            "00000000010000000000000001000000020000000000000000000000"
            "01000000000000000100000001000000010000000000000001000000"
            "03000000000000000100000001000000000000000000000001000000"
            "000000000000000a000000000000000a3d4ccccd"
        )
        blm = CountingBloomFilter(est_elements=10, false_positive_rate=0.05)
        for i in range(0, 10):
            tmp = "this is a test {0}".format(i)
            blm.add(tmp)

        with NamedTemporaryFile(dir=os.getcwd(), suffix=".blm", delete=DELETE_TEMP_FILES) as fobj:
            blm.export_c_header(fobj.name)

            # now load the file, parse it and do some tests!
            with open(fobj.name, "r") as fobj:
                data = fobj.readlines()

        data = [x.strip() for x in data]

        self.assertEqual("/* BloomFilter Export of a CountingBloomFilter */", data[0])
        self.assertEqual("#include <inttypes.h>", data[1])
        self.assertEqual("const uint64_t estimated_elements = {};".format(blm.estimated_elements), data[2])
        self.assertEqual("const uint64_t elements_added = {};".format(blm.elements_added), data[3])
        self.assertEqual("const float false_positive_rate = {};".format(blm.false_positive_rate), data[4])
        self.assertEqual("const uint64_t number_bits = {};".format(blm.number_bits), data[5])
        self.assertEqual("const unsigned int number_hashes = {};".format(blm.number_hashes), data[6])
        self.assertEqual("const unsigned char bloom[] = {", data[7])
        self.assertEqual("};", data[-1])

        # rebuild the hex version!
        new_hex = "".join([x.strip().replace("0x", "") for x in " ".join(data[8:-1]).split(",")])
        self.assertEqual(hex_val, new_hex)

    def test_cbf_export_size(self):
        """test the size of the exported file"""
        blm = CountingBloomFilter(est_elements=10, false_positive_rate=0.01)
        self.assertEqual(404, blm.export_size())

    def test_cbf_jaccard_ident(self):
        """test jaccard of two identical counting bloom filters"""
        blm1 = CountingBloomFilter(est_elements=10, false_positive_rate=0.01)
        blm1.add("this is a test", 10)
        blm2 = CountingBloomFilter(est_elements=10, false_positive_rate=0.01)
        blm2.add("this is a test", 10)
        self.assertEqual(blm1.jaccard_index(blm2), 1.0)

    def test_cbf_jaccard_ident_2(self):
        """test jaccard of two mostly identical counting bloom filters"""
        blm1 = CountingBloomFilter(est_elements=10, false_positive_rate=0.01)
        blm1.add("this is a test", 10)
        blm2 = CountingBloomFilter(est_elements=10, false_positive_rate=0.01)
        blm2.add("this is a test", 15)
        self.assertEqual(blm1.jaccard_index(blm2), 1.0)

    def test_cbf_jaccard_similar(self):
        """test jaccard of two similar counting bloom filters"""
        blm1 = CountingBloomFilter(est_elements=10, false_positive_rate=0.01)
        blm1.add("this is a test", 10)
        blm1.add("this is a different test", 10)
        blm2 = CountingBloomFilter(est_elements=10, false_positive_rate=0.01)
        blm2.add("this is a test", 10)
        blm2.add("this is also a test", 10)
        res = blm1.jaccard_index(blm2)
        self.assertGreater(res, 0.50)
        self.assertLessEqual(res, 0.60)

    def test_cbf_jaccard_similar_2(self):
        """test jaccard of two similar counting bloom filters - again"""
        blm1 = CountingBloomFilter(est_elements=100, false_positive_rate=0.01)
        blm1.add("this is a test", 10)
        blm1.add("this is a different test", 10)
        blm2 = CountingBloomFilter(est_elements=100, false_positive_rate=0.01)
        blm2.add("this is a test", 10)
        res = blm1.jaccard_index(blm2)
        self.assertLessEqual(res, 0.50)

    def test_cbf_jaccard_different(self):
        """test jaccard of two completly different counting bloom filters"""
        blm1 = CountingBloomFilter(est_elements=20, false_positive_rate=0.05)
        blm1.add("this is a test", 10)
        blm2 = CountingBloomFilter(est_elements=20, false_positive_rate=0.05)
        blm2.add("this is also a test", 10)
        self.assertEqual(blm1.jaccard_index(blm2), 0.0)

    def test_cbf_jaccard_empty(self):
        """test jaccard of an empty counting bloom filters"""
        blm1 = CountingBloomFilter(est_elements=10, false_positive_rate=0.01)
        blm1.add("this is a test", 10)
        blm2 = CountingBloomFilter(est_elements=10, false_positive_rate=0.01)
        self.assertEqual(blm1.jaccard_index(blm2), 0.0)

    def test_cbf_jaccard_empty_both(self):
        """test jaccard of an empty counting bloom filters"""
        blm1 = CountingBloomFilter(est_elements=10, false_positive_rate=0.01)
        blm2 = CountingBloomFilter(est_elements=10, false_positive_rate=0.01)
        self.assertEqual(blm1.jaccard_index(blm2), 1.0)

    def test_cbf_jaccard_different_2(self):
        """test jaccard of an mismath of counting bloom filters"""
        blm1 = CountingBloomFilter(est_elements=101, false_positive_rate=0.01)
        blm2 = CountingBloomFilter(est_elements=10, false_positive_rate=0.01)
        self.assertEqual(blm1.jaccard_index(blm2), None)

    def test_cbf_jaccard_invalid(self):
        """use an invalid type in a jaccard index"""
        blm = CountingBloomFilter(est_elements=10, false_positive_rate=0.05)
        blm.add("this is a test")
        self.assertRaises(TypeError, lambda: blm.jaccard_index(1))

    def test_cbf_jaccard_invalid_msg(self):
        """check invalid type in a jaccard index message"""
        msg = "The parameter second must be of type CountingBloomFilter"
        blm = CountingBloomFilter(est_elements=10, false_positive_rate=0.05)
        blm.add("this is another test")
        try:
            blm.jaccard_index(15)
        except TypeError as ex:
            self.assertEqual(str(ex), msg)
        else:
            self.assertEqual(True, False)

    def test_cbf_estimate_easy(self):
        """check estimate elements"""
        blm = CountingBloomFilter(est_elements=20, false_positive_rate=0.05)
        blm.add("this is a test", 10)
        blm.add("this is also a test", 5)
        self.assertEqual(blm.estimate_elements(), 2)

    def test_cbf_estimate_2(self):
        """check estimate elements - different"""
        blm = CountingBloomFilter(est_elements=20, false_positive_rate=0.05)
        blm.add("this is a test", 10)
        blm.add("this is a different test", 5)
        self.assertEqual(blm.estimate_elements(), 2)

    def test_cbf_remove(self):
        """test to see if the remove functionality works correctly"""
        blm = CountingBloomFilter(est_elements=10, false_positive_rate=0.05)
        self.assertEqual(blm.elements_added, 0)
        for i in range(0, 5):
            tmp = "this is a test {0}".format(i)
            blm.add(tmp)
        self.assertEqual(blm.elements_added, 5)
        res = blm.remove("this is a test 0")
        self.assertEqual(blm.elements_added, 4)
        self.assertEqual(res, 0)
        blm.remove("this is a test 0")
        self.assertEqual(blm.elements_added, 4)
        self.assertEqual(res, 0)

    def test_cbf_remove_mult(self):
        """test to see if the remove multiples functionality works correctly"""
        blm = CountingBloomFilter(est_elements=10, false_positive_rate=0.05)
        self.assertEqual(blm.elements_added, 0)
        blm.add("this is a test 0", 15)
        self.assertEqual(blm.elements_added, 15)
        res = blm.remove("this is a test 0", 11)
        self.assertEqual(blm.elements_added, 4)
        self.assertEqual(res, 4)
        res = blm.remove("this is a test 0", 10)
        self.assertEqual(blm.elements_added, 0)
        self.assertEqual(res, 0)

    def test_cbf_very_large_add(self):
        """test adding a very large number of elements"""
        large = 2 ** 32
        very_large = 2 ** 64
        blm = CountingBloomFilter(est_elements=10, false_positive_rate=0.05)
        self.assertEqual(blm.elements_added, 0)
        res = blm.add("this is a test 0", large)
        self.assertEqual(blm.elements_added, large)
        self.assertEqual(res, large - 1)
        res = blm.add("this is a test 0", very_large)
        self.assertEqual(blm.elements_added, very_large - 1)
        self.assertEqual(res, large - 1)

    def test_cbf_remove_from_large(self):
        """test adding a very large number of elements"""
        large = 2 ** 32
        blm = CountingBloomFilter(est_elements=10, false_positive_rate=0.05)
        self.assertEqual(blm.elements_added, 0)
        res = blm.add("this is a test 0", large)
        self.assertEqual(blm.elements_added, large)
        self.assertEqual(res, large - 1)

        res = blm.remove("this is a test 0", large)
        self.assertEqual(blm.elements_added, large)
        self.assertEqual(res, large - 1)

    def test_cbf_union(self):
        """test calculating the union between two counting bloom filters"""
        blm1 = CountingBloomFilter(est_elements=100, false_positive_rate=0.05)
        blm1.add("this is a test", 10)
        blm1.add("this is a different test", 10)
        blm2 = CountingBloomFilter(est_elements=100, false_positive_rate=0.05)
        blm2.add("this is a test", 10)
        res = blm1.union(blm2)

        self.assertEqual(res.check("this is a test"), 20)
        self.assertEqual(res.check("this is a different test"), 10)
        self.assertEqual(res.check("this is not a test"), 0)
        self.assertEqual(res.elements_added, 2)

    def test_cbf_union_error(self):
        """test union of two counting bloom filters type error"""
        blm1 = CountingBloomFilter(est_elements=10, false_positive_rate=0.01)
        self.assertRaises(TypeError, lambda: blm1.union(1))

    def test_cbf_union_error_msg(self):
        """test union of two counting bloom filters type error msg"""
        blm1 = CountingBloomFilter(est_elements=10, false_positive_rate=0.01)
        msg = "The parameter second must be of type CountingBloomFilter"
        try:
            blm1.union(1)
        except TypeError as ex:
            self.assertEqual(str(ex), msg)
        else:
            self.assertEqual(True, False)

    def test_cbf_union_diff(self):
        """test union of an mismath of counting bloom filters"""
        blm1 = CountingBloomFilter(est_elements=101, false_positive_rate=0.01)
        blm2 = CountingBloomFilter(est_elements=10, false_positive_rate=0.01)
        self.assertEqual(blm1.union(blm2), None)

    def test_cbf_inter(self):
        """test calculating the intersection between two
        counting bloom filters"""
        blm1 = CountingBloomFilter(est_elements=100, false_positive_rate=0.05)
        blm1.add("this is a test", 10)
        blm1.add("this is a different test", 10)
        blm2 = CountingBloomFilter(est_elements=100, false_positive_rate=0.05)
        blm2.add("this is a test", 10)
        res = blm1.intersection(blm2)

        self.assertEqual(res.check("this is a test"), 20)
        self.assertEqual(res.check("this is a different test"), 0)
        self.assertEqual(res.check("this is not a test"), 0)
        self.assertEqual(res.elements_added, 1)

    def test_cbf_inter_error(self):
        """test intersection of two counting bloom filters type error"""
        blm1 = CountingBloomFilter(est_elements=10, false_positive_rate=0.01)
        self.assertRaises(TypeError, lambda: blm1.intersection(1))

    def test_cbf_inter_error_msg(self):
        """test intersection of two counting bloom filters type error msg"""
        blm1 = CountingBloomFilter(est_elements=10, false_positive_rate=0.01)
        msg = "The parameter second must be of type CountingBloomFilter"
        try:
            blm1.intersection(1)
        except TypeError as ex:
            self.assertEqual(str(ex), msg)
        else:
            self.assertEqual(True, False)

    def test_cbf_inter_diff(self):
        """test intersection of an mismath of counting bloom filters"""
        blm1 = CountingBloomFilter(est_elements=101, false_positive_rate=0.01)
        blm2 = CountingBloomFilter(est_elements=10, false_positive_rate=0.01)
        self.assertEqual(blm1.intersection(blm2), None)

    def test_cbf_all_bits_set(self):
        """test inserting too many elements so that the all bits are set"""
        blm = CountingBloomFilter(est_elements=10, false_positive_rate=0.05)
        for i in range(100):
            blm.add(str(i))
        # NOTE: this causes an exception when all bits are set
        self.assertEqual(-1, blm.estimate_elements())


if __name__ == "__main__":
    unittest.main()
