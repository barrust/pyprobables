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

from probables import BloomFilter, BloomFilterOnDisk
from probables.constants import UINT64_T_MAX
from probables.exceptions import InitializationError, NotSupportedError
from probables.hashes import hash_with_depth_int

DELETE_TEMP_FILES = True


class TestBloomFilter(unittest.TestCase):
    """Test the default bloom filter implementation"""

    def test_bf_init(self):
        """test version information"""
        blm = BloomFilter(est_elements=10, false_positive_rate=0.05)
        self.assertEqual(blm.false_positive_rate, 0.05000000074505806)
        self.assertEqual(blm.estimated_elements, 10)
        self.assertEqual(blm.number_hashes, 4)
        self.assertEqual(blm.number_bits, 63)
        self.assertEqual(blm.elements_added, 0)
        self.assertEqual(blm.is_on_disk, False)
        self.assertEqual(blm.bloom_length, 63 // 8 + 1)

    def test_bf_ea(self):
        """test elements added is correct"""
        blm = BloomFilter(est_elements=10, false_positive_rate=0.05)
        self.assertEqual(blm.elements_added, 0)
        blm.add("this is a test")
        self.assertEqual(blm.elements_added, 1)

    def test_bf_add(self):
        """test estimate elements is correct"""
        blm = BloomFilter(est_elements=20, false_positive_rate=0.05)
        res1 = blm.estimate_elements()
        blm.add("this is a test")
        res2 = blm.estimate_elements()
        self.assertNotEqual(res1, res2)
        self.assertEqual(res1, 0)
        self.assertEqual(res2, 1)
        self.assertEqual(blm.elements_added, 1)

    def test_bf_check(self):
        """ensure that checking the bloom filter works"""
        blm = BloomFilter(est_elements=10, false_positive_rate=0.05)
        blm.add("this is a test")
        blm.add("this is another test")
        self.assertEqual(blm.check("this is a test"), True)
        self.assertEqual(blm.check("this is another test"), True)
        self.assertEqual(blm.check("this is yet another test"), False)
        self.assertEqual(blm.check("this is not another test"), False)

    def test_bf_in_check(self):
        """check that the in construct works"""
        blm = BloomFilter(est_elements=10, false_positive_rate=0.05)
        blm.add("this is a test")
        blm.add("this is another test")
        self.assertEqual("this is a test" in blm, True)
        self.assertEqual("this is another test" in blm, True)
        self.assertEqual("this is yet another test" in blm, False)
        self.assertEqual("this is not another test" in blm, False)

    def test_bf_union(self):
        """test the union of two bloom filters"""
        blm = BloomFilter(est_elements=20, false_positive_rate=0.05)
        blm.add("this is a test")
        blm.add("this is another test")
        blm2 = BloomFilter(est_elements=20, false_positive_rate=0.05)
        blm2.add("this is yet another test")

        blm3 = blm.union(blm2)
        self.assertEqual(blm3.estimate_elements(), 3)
        self.assertEqual(blm3.elements_added, 3)
        self.assertEqual(blm3.check("this is a test"), True)
        self.assertEqual(blm3.check("this is another test"), True)
        self.assertEqual(blm3.check("this is yet another test"), True)
        self.assertEqual(blm3.check("this is not another test"), False)

    def test_bf_union_diff(self):
        """make sure checking for different bloom filters works union"""
        blm = BloomFilter(est_elements=10, false_positive_rate=0.05)
        blm.add("this is a test")
        blm2 = BloomFilter(est_elements=10, false_positive_rate=0.05, hash_function=different_hash)

        blm3 = blm.union(blm2)
        self.assertEqual(blm3, None)

    def test_bf_intersection(self):
        """test the union of two bloom filters"""
        blm = BloomFilter(est_elements=10, false_positive_rate=0.05)
        blm.add("this is a test")
        blm.add("this is another test")
        blm2 = BloomFilter(est_elements=10, false_positive_rate=0.05)
        blm2.add("this is another test")
        blm2.add("this is yet another test")

        blm3 = blm.intersection(blm2)
        self.assertEqual(blm3.estimate_elements(), 1)
        self.assertEqual(blm3.elements_added, 1)
        self.assertEqual(blm3.check("this is a test"), False)
        self.assertEqual(blm3.check("this is another test"), True)
        self.assertEqual(blm3.check("this is yet another test"), False)
        self.assertEqual(blm3.check("this is not another test"), False)

    def test_bf_intersection_issue_57(self):
        """test the union of two bloom filters - issue 57"""
        blm = BloomFilter(est_elements=6425, false_positive_rate=0.001)
        blm.add("this is a test")
        blm.add("this is another test")
        blm2 = BloomFilter(est_elements=6425, false_positive_rate=0.001)
        blm2.add("this is another test")
        blm2.add("this is yet another test")

        blm3 = blm.intersection(blm2)
        self.assertEqual(blm3.estimate_elements(), 1)
        self.assertEqual(blm3.elements_added, 1)
        self.assertEqual(blm3.check("this is a test"), False)
        self.assertEqual(blm3.check("this is another test"), True)
        self.assertEqual(blm3.check("this is yet another test"), False)
        self.assertEqual(blm3.check("this is not another test"), False)

    def test_large_one_off_logl_compatibility(self):
        """test C version logl compatibility"""
        blm = BloomFilter(est_elements=16000000, false_positive_rate=0.0010)
        # in g++ using log instead of logl would give a different number of
        # bits and bloom length!
        self.assertEqual(28755175, blm.bloom_length)
        self.assertEqual(230041400, blm.number_bits)

    def test_bf_intersection_diff(self):
        """make sure checking for different bloom filters works intersection"""
        blm = BloomFilter(est_elements=10, false_positive_rate=0.05)
        blm.add("this is a test")
        blm2 = BloomFilter(est_elements=100, false_positive_rate=0.05)

        blm3 = blm.intersection(blm2)
        self.assertEqual(blm3, None)

    def test_bf_jaccard(self):
        """test the jaccard index of two bloom filters"""
        blm = BloomFilter(est_elements=10, false_positive_rate=0.05)
        blm.add("this is a test")
        blm.add("this is another test")
        blm2 = BloomFilter(est_elements=10, false_positive_rate=0.05)
        blm2.add("this is another test")
        blm2.add("this is yet another test")

        res = blm.jaccard_index(blm2)
        self.assertGreater(res, 0.50)
        self.assertLess(res, 0.75)

    def test_bf_jaccard_diff(self):
        """make sure checking for different bloom filters works jaccard"""
        blm = BloomFilter(est_elements=10, false_positive_rate=0.05)
        blm.add("this is a test")
        blm2 = BloomFilter(est_elements=100, false_positive_rate=0.05)

        blm3 = blm.jaccard_index(blm2)
        self.assertEqual(blm3, None)

    def test_bf_jaccard_invalid(self):
        """use an invalid type in a jaccard index"""
        blm = BloomFilter(est_elements=10, false_positive_rate=0.05)
        blm.add("this is a test")
        self.assertRaises(TypeError, lambda: blm.jaccard_index(1))

    def test_bf_jaccard_invalid_msg(self):
        """check invalid type in a jaccard index message"""
        msg = "The parameter second must be of type BloomFilter or a BloomFilterOnDisk"
        blm = BloomFilter(est_elements=10, false_positive_rate=0.05)
        blm.add("this is a test")
        try:
            blm.jaccard_index(1)
        except TypeError as ex:
            self.assertEqual(str(ex), msg)
        else:
            self.assertEqual(True, False)

    def test_bf_union_invalid(self):
        """use an invalid type in a union"""
        blm = BloomFilter(est_elements=10, false_positive_rate=0.05)
        blm.add("this is a test")
        self.assertRaises(TypeError, lambda: blm.jaccard_index(1))

    def test_bf_union_invalid_msg(self):
        """check invalid type in a union message"""
        msg = "The parameter second must be of type BloomFilter or a BloomFilterOnDisk"
        blm = BloomFilter(est_elements=10, false_positive_rate=0.05)
        blm.add("this is a test")
        try:
            blm.union(1)
        except TypeError as ex:
            self.assertEqual(str(ex), msg)
        else:
            self.assertEqual(True, False)

    def test_bf_intersection_invalid(self):
        """use an invalid type in a intersection"""
        blm = BloomFilter(est_elements=10, false_positive_rate=0.05)
        blm.add("this is a test")
        self.assertRaises(TypeError, lambda: blm.jaccard_index(1))

    def test_bf_intersec_invalid_msg(self):
        """check invalid type in a intersection message"""
        msg = "The parameter second must be of type BloomFilter or a BloomFilterOnDisk"
        blm = BloomFilter(est_elements=10, false_positive_rate=0.05)
        blm.add("this is a test")
        try:
            blm.intersection(1)
        except TypeError as ex:
            self.assertEqual(str(ex), msg)
        else:
            self.assertEqual(True, False)

    def test_bf_jaccard_empty(self):
        """make sure checking for different bloom filters works jaccard"""
        blm = BloomFilter(est_elements=10, false_positive_rate=0.05)
        blm2 = BloomFilter(est_elements=10, false_positive_rate=0.05)

        blm3 = blm.jaccard_index(blm2)
        self.assertEqual(blm3, 1.0)

    def test_bf_stats(self):
        """test that the information in the stats is correct"""
        msg = (
            "BloomFilter:\n"
            "\tbits: 63\n"
            "\testimated elements: 10\n"
            "\tnumber hashes: 4\n"
            "\tmax false positive rate: 0.050000\n"
            "\tbloom length (8 bits): 8\n"
            "\telements added: 10\n"
            "\testimated elements added: 10\n"
            "\tcurrent false positive rate: 0.048806\n"
            "\texport size (bytes): 28\n"
            "\tnumber bits set: 31\n"
            "\tis on disk: no\n"
        )
        blm = BloomFilter(est_elements=10, false_positive_rate=0.05)
        for i in range(0, 10):
            tmp = "this is a test {0}".format(i)
            blm.add(tmp)
        stats = str(blm)
        self.assertEqual(stats, msg)

    def test_bf_export_hex(self):
        """test the exporting of the bloom filter to a hex string"""
        hex_val = "6da491461a6bba4d000000000000000a000000000000000a3d4ccccd"
        blm = BloomFilter(est_elements=10, false_positive_rate=0.05)
        for i in range(0, 10):
            tmp = "this is a test {0}".format(i)
            blm.add(tmp)
        hex_out = blm.export_hex()

        self.assertEqual(hex_out, hex_val)

    def test_bf_load_hex(self):
        """test importing a bloom filter from hex value"""
        hex_val = "6da491461a6bba4d000000000000000a000000000000000a3d4ccccd"
        blm = BloomFilter(hex_string=hex_val)

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

    def test_bf_export_c_header(self):
        """test exporting a c header"""

        hex_val = "6da491461a6bba4d000000000000000a000000000000000a3d4ccccd"
        blm = BloomFilter(est_elements=10, false_positive_rate=0.05)
        for i in range(0, 10):
            tmp = "this is a test {0}".format(i)
            blm.add(tmp)
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".blm", delete=DELETE_TEMP_FILES) as fobj:
            blm.export_c_header(fobj.name)

            # now load the file, parse it and do some tests!
            with open(fobj.name, "r") as fobj:
                data = fobj.readlines()
        data = [x.strip() for x in data]

        self.assertEqual("/* BloomFilter Export of a standard BloomFilter */", data[0])
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

    def test_bf_load_invalid_hex(self):
        """test importing a bloom filter from an invalid hex value"""
        hex_val = "85f240623b6d9459000000000000000a000000000000000a3d4ccccQ"
        self.assertRaises(InitializationError, lambda: BloomFilter(hex_string=hex_val))

    def test_bf_export_file(self):
        """test exporting bloom filter to file"""
        md5_val = "8d27e30e1c5875b0edcf7413c7bdb221"
        blm = BloomFilter(est_elements=10, false_positive_rate=0.05)
        blm.add("this is a test")

        with NamedTemporaryFile(dir=os.getcwd(), suffix=".blm", delete=DELETE_TEMP_FILES) as fobj:
            blm.export(fobj.name)
            md5_out = calc_file_md5(fobj.name)
        self.assertEqual(md5_out, md5_val)

    def test_bf_bytes(self):
        """test exporting BloomFilter to bytes"""
        md5_val = "8d27e30e1c5875b0edcf7413c7bdb221"
        blm = BloomFilter(est_elements=10, false_positive_rate=0.05)
        blm.add("this is a test")
        b = bytes(blm)
        md5_out = hashlib.md5(b).hexdigest()
        self.assertEqual(md5_out, md5_val)

    def test_bf_frombytes(self):
        """test loading BloomFilter from bytes"""
        blm = BloomFilter(est_elements=10, false_positive_rate=0.05)
        blm.add("this is a test")
        bytes_out = bytes(blm)

        blm2 = BloomFilter.frombytes(bytes_out)

        self.assertEqual(blm2.false_positive_rate, 0.05000000074505806)
        self.assertEqual(blm2.estimated_elements, 10)
        self.assertEqual(blm2.number_hashes, 4)
        self.assertEqual(blm2.number_bits, 63)
        self.assertEqual(blm2.elements_added, 1)
        self.assertEqual(blm2.is_on_disk, False)
        self.assertEqual(blm2.bloom_length, 63 // 8 + 1)

    def test_bf_load_file(self):
        """test loading bloom filter from file"""
        blm = BloomFilter(est_elements=10, false_positive_rate=0.05)
        blm.add("this is a test")

        with NamedTemporaryFile(dir=os.getcwd(), suffix=".blm", delete=DELETE_TEMP_FILES) as fobj:
            blm.export(fobj.name)
            blm2 = BloomFilter(filepath=fobj.name)

        self.assertEqual("this is a test" in blm2, True)
        self.assertEqual("this is not a test" in blm2, False)

    def test_bf_all_bits_set(self):
        """test inserting too many elements so that the all bits are set"""
        blm = BloomFilter(est_elements=10, false_positive_rate=0.05)
        for i in range(100):
            blm.add(str(i))
        # NOTE: this causes an exception when all bits are set
        self.assertEqual(-1, blm.estimate_elements())

    def test_bf_load_invalid_file(self):
        """test importing a bloom filter from an invalid filepath"""
        filename = "invalid.blm"
        self.assertRaises(InitializationError, lambda: BloomFilter(filepath=filename))

    def test_bf_invalid_params_msg(self):
        """test importing a bloom filter from an invalid filepath msg"""
        filename = "invalid.blm"
        msg = "Insufecient parameters to set up the Bloom Filter"
        try:
            BloomFilter(filepath=filename)
        except InitializationError as ex:
            self.assertEqual(str(ex), msg)
        else:
            self.assertEqual(True, False)

    def test_invalid_fpr(self):
        """test if invalid false positive rate provided"""

        def runner():
            """runner"""
            BloomFilter(est_elements=100, false_positive_rate=1.1)

        self.assertRaises(InitializationError, runner)
        try:
            runner()
        except InitializationError as ex:
            msg = "Bloom: false positive rate must be between 0.0 and 1.0"
            self.assertEqual(str(ex), msg)
        else:
            self.assertEqual(True, False)

    def test_invalid_estimated_els(self):
        """test if invalid estimated elements provided"""

        def runner():
            """runner"""
            BloomFilter(est_elements=0, false_positive_rate=0.1)

        self.assertRaises(InitializationError, runner)
        try:
            runner()
        except InitializationError as ex:
            msg = "Bloom: estimated elements must be greater than 0"
            self.assertEqual(str(ex), msg)
        else:
            self.assertEqual(True, False)

    def test_invalid_fpr_2(self):
        """test if invalid false positive rate provided is non numeric"""

        def runner():
            """runner"""
            BloomFilter(est_elements=100, false_positive_rate="1.1")

        self.assertRaises(InitializationError, runner)
        try:
            runner()
        except InitializationError as ex:
            msg = "Bloom: false positive rate must be between 0.0 and 1.0"
            self.assertEqual(str(ex), msg)
        else:
            self.assertEqual(True, False)

    def test_invalid_estimated_els_2(self):
        """test if invalid estimated elements provided is non numeric"""

        def runner():
            """runner"""
            BloomFilter(est_elements=[0], false_positive_rate=0.1)

        self.assertRaises(InitializationError, runner)
        try:
            runner()
        except InitializationError as ex:
            msg = "Bloom: estimated elements must be greater than 0"
            self.assertEqual(str(ex), msg)
        else:
            self.assertEqual(True, False)

    def test_invalid_number_hashes(self):
        """test if invalid estimated elements provided"""

        def runner():
            """runner"""
            BloomFilter(est_elements=10, false_positive_rate=0.999)

        self.assertRaises(InitializationError, runner)
        try:
            runner()
        except InitializationError as ex:
            msg = "Bloom: Number hashes is zero; unusable parameters provided"
            self.assertEqual(str(ex), msg)
        else:
            self.assertEqual(True, False)

    def test_bf_clear(self):
        """test clearing out the bloom filter"""
        blm = BloomFilter(est_elements=10, false_positive_rate=0.05)
        self.assertEqual(blm.elements_added, 0)
        for i in range(0, 10):
            tmp = "this is a test {0}".format(i)
            blm.add(tmp)
        self.assertEqual(blm.elements_added, 10)

        blm.clear()
        self.assertEqual(blm.elements_added, 0)
        for idx in range(blm.bloom_length):
            self.assertEqual(blm._get_element(idx), 0)

    def test_bf_use_different_hash(self):
        """test that the different hash works as intended"""
        md5_val = "7f590086f9b962387e145899dd001256"  # for default hash used
        results = [
            14409285476674975580,
            6203976290780191624,
            5074829385518853901,
            3953072760750514173,
            11782747630324011555,
        ]

        @hash_with_depth_int
        def my_hash(key, depth=1, encoding="utf-8"):
            """my hash function"""
            max64mod = UINT64_T_MAX + 1
            val = int(hashlib.sha512(key.encode(encoding)).hexdigest(), 16)
            return val % max64mod

        blm = BloomFilter(est_elements=10, false_positive_rate=0.05, hash_function=my_hash)
        self.assertEqual(blm.elements_added, 0)
        blm.add("this is a test")
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".blm", delete=DELETE_TEMP_FILES) as fobj:
            blm.export(fobj.name)

            md5_out = calc_file_md5(fobj.name)
        self.assertNotEqual(md5_out, md5_val)

        for i in range(0, 10):
            tmp = "this is a test {0}".format(i)
            blm.add(tmp)

        self.assertEqual(blm.elements_added, 11)

        for i in range(0, 10):
            tmp = "this is a test {0}".format(i)
            self.assertTrue(blm.check(tmp))

        self.assertEqual(blm.hashes("this is a test", 5), results)
        res = blm.hashes("this is a test", 1)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0], results[0])

    def test_another_hashing_algo(self):
        """test defining a completely different hashing strategy"""
        md5_val = "7f590086f9b962387e145899dd001256"  # for default hash used
        results = [
            14409285476674975580,
            1383622036369840193,
            10825905054403519891,
            3456253732347153957,
            1494124715262089992,
        ]

        def my_hash(key, depth, encoding="utf-8"):
            """my hashing strategy"""
            max64mod = UINT64_T_MAX + 1
            results = list()
            for i in range(0, depth):
                tmp = key[i:] + key[:i]
                val = int(hashlib.sha512(tmp.encode(encoding)).hexdigest(), 16)
                results.append(val % max64mod)
            return results

        blm = BloomFilter(est_elements=10, false_positive_rate=0.05, hash_function=my_hash)

        self.assertEqual(blm.elements_added, 0)
        blm.add("this is a test")
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".blm", delete=DELETE_TEMP_FILES) as fobj:
            blm.export(fobj.name)
            md5_out = calc_file_md5(fobj.name)
        self.assertNotEqual(md5_out, md5_val)

        for i in range(0, 10):
            tmp = "this is a test {0}".format(i)
            blm.add(tmp)

        self.assertEqual(blm.elements_added, 11)

        for i in range(0, 10):
            tmp = "this is a test {0}".format(i)
            self.assertTrue(blm.check(tmp))

        self.assertEqual(blm.hashes("this is a test", 5), results)
        res = blm.hashes("this is a test", 1)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0], results[0])


class TestBloomFilterOnDisk(unittest.TestCase):
    """Test the Bloom Filter on disk implementation"""

    def test_bfod_init(self):
        """test the initalization of the on disk version"""
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".blm", delete=DELETE_TEMP_FILES) as fobj:
            blmd = BloomFilterOnDisk(fobj.name, 10, 0.05)
            self.assertEqual(blmd.false_positive_rate, 0.05000000074505806)
            self.assertEqual(blmd.estimated_elements, 10)
            self.assertEqual(blmd.number_hashes, 4)
            self.assertEqual(blmd.number_bits, 63)
            self.assertEqual(blmd.elements_added, 0)
            self.assertEqual(blmd.is_on_disk, True)
            self.assertEqual(blmd.bloom_length, 63 // 8 + 1)
            blmd.close()

    def test_bfod_ea(self):
        """test on disk elements added is correct"""
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".blm", delete=DELETE_TEMP_FILES) as fobj:
            blmd = BloomFilterOnDisk(fobj.name, 10, 0.05)
            self.assertEqual(blmd.elements_added, 0)
            blmd.add("this is a test")
            self.assertEqual(blmd.elements_added, 1)
            blmd.close()

    def test_bfod_ee(self):
        """test on disk estimate elements is correct on disk"""
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".blm", delete=DELETE_TEMP_FILES) as fobj:
            blmd = BloomFilterOnDisk(fobj.name, 20, 0.05)
            res1 = blmd.estimate_elements()
            blmd.add("this is a test")
            res2 = blmd.estimate_elements()
            self.assertNotEqual(res1, res2)
            self.assertEqual(res1, 0)
            self.assertEqual(res2, 1)
            blmd.close()

    def test_bfod_check(self):
        """ensure the use of check works on disk bloom"""
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".blm", delete=DELETE_TEMP_FILES) as fobj:
            blm = BloomFilterOnDisk(fobj.name, 10, 0.05)
            blm.add("this is a test")
            blm.add("this is another test")
            self.assertEqual(blm.check("this is a test"), True)
            self.assertEqual(blm.check("this is another test"), True)
            self.assertEqual(blm.check("this is yet another test"), False)
            self.assertEqual(blm.check("this is not another test"), False)
            blm.close()

    def test_bfod_union(self):
        """test the union of two bloom filters on disk"""
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".blm", delete=DELETE_TEMP_FILES) as fobj:
            blm = BloomFilterOnDisk(fobj.name, 20, 0.05)
            blm.add("this is a test")
            blm.add("this is another test")
            blm2 = BloomFilter(20, 0.05)
            blm2.add("this is yet another test")

            blm3 = blm.union(blm2)
            self.assertEqual(blm3.estimate_elements(), 3)
            self.assertEqual(blm3.elements_added, 3)
            self.assertEqual(blm3.check("this is a test"), True)
            self.assertEqual(blm3.check("this is another test"), True)
            self.assertEqual(blm3.check("this is yet another test"), True)
            self.assertEqual(blm3.check("this is not another test"), False)
            blm.close()

    def test_bfod_intersection(self):
        """test the intersection of two bloom filters on disk"""
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".blm", delete=DELETE_TEMP_FILES) as fobj:
            blm = BloomFilterOnDisk(fobj.name, 10, 0.05)
            blm.add("this is a test")
            blm.add("this is another test")
            blm2 = BloomFilter(10, 0.05)
            blm2.add("this is another test")
            blm2.add("this is yet another test")

            blm3 = blm.intersection(blm2)
            self.assertEqual(blm3.estimate_elements(), 1)
            self.assertEqual(blm3.elements_added, 1)
            self.assertEqual(blm3.check("this is a test"), False)
            self.assertEqual(blm3.check("this is another test"), True)
            self.assertEqual(blm3.check("this is yet another test"), False)
            self.assertEqual(blm3.check("this is not another test"), False)
            blm.close()

    def test_bfod_jaccard(self):
        """test the on disk jaccard index of two bloom filters"""
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".blm", delete=DELETE_TEMP_FILES) as fobj:
            blm = BloomFilterOnDisk(fobj.name, 20, 0.05)
            blm.add("this is a test")
            blm.add("this is another test")
            blm2 = BloomFilter(20, 0.05)
            blm2.add("this is another test")
            blm2.add("this is yet another test")

            res = blm.jaccard_index(blm2)
            self.assertGreater(res, 0.33)
            self.assertLess(res, 0.50)
            blm.close()

    def test_bfod_load_on_disk(self):
        """test loading a previously saved blm on disk"""
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".blm", delete=DELETE_TEMP_FILES) as fobj:
            blm = BloomFilter(10, 0.05)
            blm.add("this is a test")
            blm.export(fobj.name)

            blmd = BloomFilterOnDisk(fobj.name)
            self.assertEqual("this is a test" in blmd, True)
            self.assertEqual("this is not a test" in blmd, False)
            blmd.close()

    def test_bfod_load_invalid_file(self):
        """test importing a bloom filter on disk from an invalid filepath"""
        filename = "invalid.blm"
        self.assertRaises(InitializationError, lambda: BloomFilterOnDisk(filepath=filename))

    def test_bfod_invalid_params_msg(self):
        """test importing a bloom filter on disk from an invalid filepath msg"""
        filename = "invalid.blm"
        msg = "Insufecient parameters to set up the On Disk Bloom Filter"
        try:
            BloomFilterOnDisk(filepath=filename)
        except InitializationError as ex:
            self.assertEqual(str(ex), msg)
        else:
            self.assertEqual(True, False)

    def test_bfod_close_del(self):
        """close an on disk bloom using the del syntax"""
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".blm", delete=DELETE_TEMP_FILES) as fobj:
            blm = BloomFilterOnDisk(fobj.name, 10, 0.05)
            blm.add("this is a test")
            del blm
            try:
                self.assertEqual(True, blm)
            except UnboundLocalError as ex:
                msg = "local variable 'blm' referenced before assignment"
                self.assertEqual(str(ex), msg)
            else:
                self.assertEqual(True, False)

    # export to new file
    def test_bfod_export(self):
        """export to on disk to new file"""
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".blm", delete=DELETE_TEMP_FILES) as fobj:
            with NamedTemporaryFile(dir=os.getcwd(), suffix=".blm", delete=DELETE_TEMP_FILES) as fobj1:
                blm = BloomFilterOnDisk(fobj.name, 10, 0.05)
                blm.add("this is a test")

                blm.export(fobj1.name)
                blm.close()

                md5_1 = calc_file_md5(fobj.name)
                md5_2 = calc_file_md5(fobj1.name)
                self.assertEqual(md5_1, md5_2)

    def test_bfod_bytes(self):
        """test exporting an on disk Bloom Filter to bytes"""
        md5_val = "8d27e30e1c5875b0edcf7413c7bdb221"
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".blm", delete=DELETE_TEMP_FILES) as fobj:
            blm = BloomFilterOnDisk(fobj.name, 10, 0.05)
            blm.add("this is a test")
            b = bytes(blm)
            md5_out = hashlib.md5(b).hexdigest()
            self.assertEqual(md5_out, md5_val)

    def test_bfod_frombytes(self):
        """test loading an on disk BloomFilter from bytes (raises exception)"""
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".blm", delete=DELETE_TEMP_FILES) as fobj:
            blm = BloomFilterOnDisk(fobj.name, 10, 0.05)
            blm.add("this is a test")
            bytes_out = bytes(blm)
        self.assertRaises(NotSupportedError, lambda: BloomFilterOnDisk.frombytes(bytes_out))

    def test_bfod_frombytes_msg(self):
        """test loading an on disk BloomFilter from bytes (message)"""
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".blm", delete=DELETE_TEMP_FILES) as fobj:
            blm = BloomFilterOnDisk(fobj.name, 10, 0.05)
            blm.add("this is a test")
            bytes_out = bytes(blm)
        try:
            BloomFilterOnDisk.frombytes(bytes_out)
        except NotSupportedError as ex:
            msg = "Loading from bytes is currently not supported by the on disk Bloom Filter"
            self.assertEqual(str(ex), msg)
        else:
            self.assertEqual(True, False)

    def test_bfod_export_hex(self):
        """test that page error is thrown correctly"""
        hex_val = "6da491461a6bba4d000000000000000a000000000000000a3d4ccccd"
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".blm", delete=DELETE_TEMP_FILES) as fobj:
            blm = BloomFilterOnDisk(fobj.name, est_elements=10, false_positive_rate=0.05)
            for i in range(0, 10):
                tmp = "this is a test {0}".format(i)
                blm.add(tmp)
            hex_out = blm.export_hex()
            self.assertEqual(hex_out, hex_val)

    def test_bfod_load_hex(self):
        """test that page error is thrown correctly"""
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".blm", delete=DELETE_TEMP_FILES) as fobj:
            hex_val = "85f240623b6d9459000000000000000a000000000000000a3d4ccccd"
            self.assertRaises(
                NotSupportedError,
                lambda: BloomFilterOnDisk(filepath=fobj.name, hex_string=hex_val),
            )

    def test_bfod_load_hex_msg(self):
        """test that page error is thrown correctly"""
        hex_val = "85f240623b6d9459000000000000000a000000000000000a3d4ccccd"
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".blm", delete=DELETE_TEMP_FILES) as fobj:
            try:
                BloomFilterOnDisk(filepath=fobj.name, hex_string=hex_val)
            except NotSupportedError as ex:
                msg = "Loading from hex_string is currently not supported by the on disk Bloom Filter"
                self.assertEqual(str(ex), msg)
            else:
                self.assertEqual(True, False)

    def test_bfod_export_c_header(self):
        """test exporting a c header"""
        hex_val = "6da491461a6bba4d000000000000000a000000000000000a3d4ccccd"
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".blm", delete=DELETE_TEMP_FILES) as fobj:
            blm = BloomFilterOnDisk(fobj.name, est_elements=10, false_positive_rate=0.05)
            for i in range(0, 10):
                tmp = "this is a test {0}".format(i)
                blm.add(tmp)
            with NamedTemporaryFile(dir=os.getcwd(), suffix=".blm", delete=DELETE_TEMP_FILES) as fobj:
                blm.export_c_header(fobj.name)

                # now load the file, parse it and do some tests!
                with open(fobj.name, "r") as fobj:
                    data = fobj.readlines()

        data = [x.strip() for x in data]

        self.assertEqual("/* BloomFilter Export of a standard BloomFilter */", data[0])
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

    def test_bfod_clear(self):
        """test clearing out the bloom filter on disk"""
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".blm", delete=DELETE_TEMP_FILES) as fobj:
            blm = BloomFilterOnDisk(filepath=fobj.name, est_elements=10, false_positive_rate=0.05)
            self.assertEqual(blm.elements_added, 0)
            for i in range(0, 10):
                tmp = "this is a test {0}".format(i)
                blm.add(tmp)
            self.assertEqual(blm.elements_added, 10)

            blm.clear()
            self.assertEqual(blm.elements_added, 0)
            for idx in range(blm.bloom_length):
                self.assertEqual(blm._get_element(idx), 0)

    def test_bfod_union_diff(self):
        """make sure checking for different bloom filters on disk works union"""
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".blm", delete=DELETE_TEMP_FILES) as fobj:
            blm = BloomFilterOnDisk(fobj.name, est_elements=10, false_positive_rate=0.05)
            blm.add("this is a test")
            blm2 = BloomFilter(est_elements=10, false_positive_rate=0.05, hash_function=different_hash)

            blm3 = blm.union(blm2)
            self.assertEqual(blm3, None)

    def test_bfod_intersection_diff(self):
        """make sure checking for different bloom filters on disk works intersection"""
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".blm", delete=DELETE_TEMP_FILES) as fobj:
            blm = BloomFilterOnDisk(fobj.name, est_elements=10, false_positive_rate=0.05)
            blm.add("this is a test")
            blm2 = BloomFilter(est_elements=10, false_positive_rate=0.05, hash_function=different_hash)

            blm3 = blm.intersection(blm2)
            self.assertEqual(blm3, None)

    def test_bfod_jaccard_diff(self):
        """make sure checking for different bloom filters on disk works jaccard"""
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".blm", delete=DELETE_TEMP_FILES) as fobj:
            blm = BloomFilterOnDisk(fobj.name, est_elements=10, false_positive_rate=0.05)
            blm.add("this is a test")
            blm2 = BloomFilter(est_elements=10, false_positive_rate=0.05, hash_function=different_hash)

            blm3 = blm.jaccard_index(blm2)
            self.assertEqual(blm3, None)

    def test_bfod_jaccard_invalid(self):
        """use an invalid type in a jaccard index cbf"""
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".blm", delete=DELETE_TEMP_FILES) as fobj:
            blm = BloomFilterOnDisk(fobj.name, est_elements=10, false_positive_rate=0.05)
            blm.add("this is a test")
            self.assertRaises(TypeError, lambda: blm.jaccard_index(1))

    def test_bfod_jaccard_invalid_msg(self):
        """check invalid type in a jaccard index message cbf"""
        msg = "The parameter second must be of type BloomFilter or a BloomFilterOnDisk"
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".blm", delete=DELETE_TEMP_FILES) as fobj:
            blm = BloomFilterOnDisk(fobj.name, est_elements=10, false_positive_rate=0.05)
            blm.add("this is a test")
            try:
                blm.jaccard_index(1)
            except TypeError as ex:
                self.assertEqual(str(ex), msg)
            else:
                self.assertEqual(True, False)

    def test_bfod_union_invalid(self):
        """use an invalid type in a union cbf"""
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".blm", delete=DELETE_TEMP_FILES) as fobj:
            blm = BloomFilterOnDisk(fobj.name, est_elements=10, false_positive_rate=0.05)
            blm.add("this is a test")
            self.assertRaises(TypeError, lambda: blm.jaccard_index(1))

    def test_bfod_union_invalid_msg(self):
        """check invalid type in a union message cbf"""
        msg = "The parameter second must be of type BloomFilter or a BloomFilterOnDisk"
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".blm", delete=DELETE_TEMP_FILES) as fobj:
            blm = BloomFilterOnDisk(fobj.name, est_elements=10, false_positive_rate=0.05)
            blm.add("this is a test")
            try:
                blm.union(1)
            except TypeError as ex:
                self.assertEqual(str(ex), msg)
            else:
                self.assertEqual(True, False)

    def test_bfod_intersection_invalid(self):
        """use an invalid type in a intersection cbf"""
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".blm", delete=DELETE_TEMP_FILES) as fobj:
            blm = BloomFilterOnDisk(fobj.name, est_elements=10, false_positive_rate=0.05)
            blm.add("this is a test")
            self.assertRaises(TypeError, lambda: blm.jaccard_index(1))

    def test_cbf_intersec_invalid_msg(self):
        """check invalid type in a intersection message cbf"""
        msg = "The parameter second must be of type BloomFilter or a BloomFilterOnDisk"
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".blm", delete=DELETE_TEMP_FILES) as fobj:
            blm = BloomFilterOnDisk(fobj.name, est_elements=10, false_positive_rate=0.05)
            blm.add("this is a test")
            try:
                blm.intersection(1)
            except TypeError as ex:
                self.assertEqual(str(ex), msg)

    def test_bfod_all_bits_set(self):
        """test inserting too many elements so that the all bits are set"""
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".blm", delete=DELETE_TEMP_FILES) as fobj:
            blm = BloomFilterOnDisk(fobj.name, est_elements=10, false_positive_rate=0.05)
            for i in range(100):
                blm.add(str(i))
        # NOTE: this causes an exception when all bits are set
        self.assertEqual(-1, blm.estimate_elements())


if __name__ == "__main__":
    unittest.main()
