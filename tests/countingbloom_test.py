#!/usr/bin/env python3
"""Unittest class"""

import hashlib
import os
import sys
import unittest
from pathlib import Path
from tempfile import NamedTemporaryFile

this_dir = Path(__file__).parent
sys.path.insert(0, str(this_dir))
sys.path.insert(0, str(this_dir.parent))

from probables import CountingBloomFilter  # noqa: E402
from probables.exceptions import InitializationError, SimilarityError  # noqa: E402
from tests.utilities import calc_file_md5, different_hash  # noqa: E402

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
            "\tindex fullness: 0.492063\n"  # 31 of 63 slots in use (it reported the sum of counts, 40 / 63)
            "\tmax index usage: 3\n"
            "\tmax index id: 56\n"
            "\tcalculated elements: 10\n"
        )
        blm = CountingBloomFilter(est_elements=10, false_positive_rate=0.05)
        for i in range(0, 10):
            blm.add(f"this is a test {i}")
        stats = str(blm)
        self.assertEqual(stats, msg)

    def test_cbf_clear(self):
        """test clearing out the bloom filter"""
        blm = CountingBloomFilter(est_elements=10, false_positive_rate=0.05)
        self.assertEqual(blm.elements_added, 0)
        for i in range(0, 10):
            blm.add(f"this is a test {i}")
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
            tmp = f"this is a test {i}"
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
            tmp = f"this is a test {i}"
            blm.add(tmp)

        with NamedTemporaryFile(dir=os.getcwd(), suffix=".blm", delete=DELETE_TEMP_FILES) as fobj:
            blm.export_c_header(fobj.name)

            # now load the file, parse it and do some tests!
            with open(fobj.name) as fobj:
                data = fobj.readlines()

        data = [x.strip() for x in data]

        self.assertEqual("/* BloomFilter Export of a CountingBloomFilter */", data[0])
        self.assertEqual("#include <inttypes.h>", data[1])
        self.assertEqual(f"const uint64_t estimated_elements = {blm.estimated_elements};", data[2])
        self.assertEqual(f"const uint64_t elements_added = {blm.elements_added};", data[3])
        self.assertEqual(f"const float false_positive_rate = {blm.false_positive_rate};", data[4])
        self.assertEqual(f"const uint64_t number_bits = {blm.number_bits};", data[5])
        self.assertEqual(f"const unsigned int number_hashes = {blm.number_hashes};", data[6])
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
        self.assertRaises(SimilarityError, lambda: blm1.jaccard_index(blm2))

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
            tmp = f"this is a test {i}"
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
        large = 2**32
        very_large = 2**64
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
        large = 2**32
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
        self.assertRaises(SimilarityError, lambda: blm1.union(blm2))

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
        self.assertRaises(SimilarityError, lambda: blm1.intersection(blm2))

    def test_cbf_all_bits_set(self):
        """test inserting too many elements so that the all bits are set"""
        blm = CountingBloomFilter(est_elements=10, false_positive_rate=0.05)
        for i in range(100):
            blm.add(str(i))
        # NOTE: this causes an exception when all bits are set
        self.assertEqual(-1, blm.estimate_elements())


class TestCountingBloomFilterReviewFixes(unittest.TestCase):
    """Regression tests for issues found in code review"""

    @staticmethod
    def _key_with_repeated_index(blm: CountingBloomFilter) -> tuple[str, list[int]]:
        """a key two of whose hashes land on the same index, and its indexes"""
        for i in range(100000):
            key = str(i)
            indexes = [h % blm.number_bits for h in blm.hashes(key)]
            if len(set(indexes)) < len(indexes):
                return key, indexes
        raise AssertionError("no key with a repeated index")  # pragma: no cover

    def test_remove_with_repeated_index(self):
        """removing a key whose index repeats never goes below zero (it raised OverflowError)"""
        blm = CountingBloomFilter(10, 0.05)
        key, indexes = self._key_with_repeated_index(blm)
        repeated = next(k for k in indexes if indexes.count(k) > 1)
        for k in set(indexes):
            blm.bloom[k] = 5
        blm.bloom[repeated] = 1  # present, but too low to remove the key once
        before = list(blm.bloom)
        self.assertEqual(1, blm.remove(key))
        self.assertEqual(before, list(blm.bloom))  # nothing was changed

        blm = CountingBloomFilter(10, 0.05)
        blm.add(key)
        self.assertEqual(2, blm.bloom[repeated])  # incremented once per hash, as in the C version
        self.assertEqual(0, blm.remove(key))
        self.assertEqual(0, sum(blm.bloom))
        self.assertEqual(0, blm.elements_added)

    def test_add_with_repeated_index_at_cap(self):
        """adding near the 32-bit cap stops at the cap (it raised OverflowError)"""
        blm = CountingBloomFilter(10, 0.05)
        key, indexes = self._key_with_repeated_index(blm)
        repeated = next(k for k in indexes if indexes.count(k) > 1)
        blm.bloom[repeated] = 2**32 - 2
        self.assertEqual(1, blm.add(key))
        self.assertEqual(2**32 - 1, blm.bloom[repeated])
        for k in set(indexes) - {repeated}:
            self.assertEqual(indexes.count(k), blm.bloom[k])

    def test_remove_more_than_added(self):
        """removing more times than added removes what is there"""
        blm = CountingBloomFilter(100, 0.05)
        blm.add("key", 3)
        self.assertEqual(0, blm.remove("key", 10))
        self.assertEqual(0, blm.check("key"))
        self.assertEqual(0, blm.elements_added)
        self.assertEqual(0, blm.remove("key"))

    def test_saturated_indexes_not_removed(self):
        """a key whose indexes are all at the cap cannot be removed"""
        blm = CountingBloomFilter(100, 0.05)
        for h in blm.hashes("key"):
            blm.bloom[h % blm.number_bits] = 2**32 - 1
        self.assertEqual(2**32 - 1, blm.remove("key"))
        self.assertEqual(2**32 - 1, blm.check("key"))

    def test_check_alt_uses_number_hashes(self):
        """extra hashes passed to check_alt are ignored, as add_alt ignores them"""
        blm = CountingBloomFilter(100, 0.05)
        blm.add("key", 4)
        self.assertEqual(4, blm.check_alt(blm.hashes("key", depth=blm.number_hashes + 6)))

    def test_index_fullness_at_most_one(self):
        """index fullness is the share of indexes in use (it summed the counts)"""
        blm = CountingBloomFilter(10, 0.05)
        blm.add("a", 100)
        in_use = sum(1 for x in blm.bloom if x > 0)
        self.assertIn(f"\tindex fullness: {in_use / blm.number_bits:.6}\n", str(blm))


if __name__ == "__main__":
    unittest.main()
