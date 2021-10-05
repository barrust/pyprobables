# -*- coding: utf-8 -*-
""" Unittest class """

import hashlib
import os
import unittest

from probables import BloomFilter, BloomFilterOnDisk
from probables.constants import UINT64_T_MAX
from probables.exceptions import InitializationError, NotSupportedError
from probables.hashes import hash_with_depth_int

from .utilities import calc_file_md5, different_hash


class TestBloomFilter(unittest.TestCase):
    """ Test the default bloom filter implementation """

    def test_bf_init(self):
        """ test version information """
        blm = BloomFilter(est_elements=10, false_positive_rate=0.05)
        self.assertEqual(blm.false_positive_rate, 0.05000000074505806)
        self.assertEqual(blm.estimated_elements, 10)
        self.assertEqual(blm.number_hashes, 4)
        self.assertEqual(blm.number_bits, 63)
        self.assertEqual(blm.elements_added, 0)
        self.assertEqual(blm.is_on_disk, False)
        self.assertEqual(blm.bloom_length, 63 // 8 + 1)

    def test_bf_ea(self):
        """ test elements added is correct """
        blm = BloomFilter(est_elements=10, false_positive_rate=0.05)
        self.assertEqual(blm.elements_added, 0)
        blm.add("this is a test")
        self.assertEqual(blm.elements_added, 1)

    def test_bf_add(self):
        """ test estimate elements is correct """
        blm = BloomFilter(est_elements=10, false_positive_rate=0.05)
        res1 = blm.estimate_elements()
        blm.add("this is a test")
        res2 = blm.estimate_elements()
        self.assertNotEqual(res1, res2)
        self.assertEqual(res1, 0)
        self.assertEqual(res2, 1)
        self.assertEqual(blm.elements_added, 1)

    def test_bf_check(self):
        """ ensure that checking the bloom filter works """
        blm = BloomFilter(est_elements=10, false_positive_rate=0.05)
        blm.add("this is a test")
        blm.add("this is another test")
        self.assertEqual(blm.check("this is a test"), True)
        self.assertEqual(blm.check("this is another test"), True)
        self.assertEqual(blm.check("this is yet another test"), False)
        self.assertEqual(blm.check("this is not another test"), False)

    def test_bf_in_check(self):
        """ check that the in construct works """
        blm = BloomFilter(est_elements=10, false_positive_rate=0.05)
        blm.add("this is a test")
        blm.add("this is another test")
        self.assertEqual("this is a test" in blm, True)
        self.assertEqual("this is another test" in blm, True)
        self.assertEqual("this is yet another test" in blm, False)
        self.assertEqual("this is not another test" in blm, False)

    def test_bf_union(self):
        """ test the union of two bloom filters """
        blm = BloomFilter(est_elements=10, false_positive_rate=0.05)
        blm.add("this is a test")
        blm.add("this is another test")
        blm2 = BloomFilter(est_elements=10, false_positive_rate=0.05)
        blm2.add("this is yet another test")

        blm3 = blm.union(blm2)
        self.assertEqual(blm3.estimate_elements(), 3)
        self.assertEqual(blm3.elements_added, 3)
        self.assertEqual(blm3.check("this is a test"), True)
        self.assertEqual(blm3.check("this is another test"), True)
        self.assertEqual(blm3.check("this is yet another test"), True)
        self.assertEqual(blm3.check("this is not another test"), False)

    def test_bf_union_diff(self):
        """ make sure checking for different bloom filters works union """
        blm = BloomFilter(est_elements=10, false_positive_rate=0.05)
        blm.add("this is a test")
        blm2 = BloomFilter(est_elements=10, false_positive_rate=0.05, hash_function=different_hash)

        blm3 = blm.union(blm2)
        self.assertEqual(blm3, None)

    def test_bf_intersection(self):
        """ test the union of two bloom filters """
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
        """ test the union of two bloom filters - issue 57 """
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
        """ test C version logl compatibility """
        blm = BloomFilter(est_elements=16000000, false_positive_rate=0.0010)
        # in g++ using log instead of logl would give a different number of
        # bits and bloom length!
        self.assertEqual(28755175, blm.bloom_length)
        self.assertEqual(230041400, blm.number_bits)

    def test_bf_intersection_diff(self):
        """make sure checking for different bloom filters works
        intersection"""
        blm = BloomFilter(est_elements=10, false_positive_rate=0.05)
        blm.add("this is a test")
        blm2 = BloomFilter(est_elements=100, false_positive_rate=0.05)

        blm3 = blm.intersection(blm2)
        self.assertEqual(blm3, None)

    def test_bf_jaccard(self):
        """ test the jaccard index of two bloom filters """
        blm = BloomFilter(est_elements=10, false_positive_rate=0.05)
        blm.add("this is a test")
        blm.add("this is another test")
        blm2 = BloomFilter(est_elements=10, false_positive_rate=0.05)
        blm2.add("this is another test")
        blm2.add("this is yet another test")

        res = blm.jaccard_index(blm2)
        self.assertGreater(res, 0.33)
        self.assertLess(res, 0.50)

    def test_bf_jaccard_diff(self):
        """ make sure checking for different bloom filters works jaccard """
        blm = BloomFilter(est_elements=10, false_positive_rate=0.05)
        blm.add("this is a test")
        blm2 = BloomFilter(est_elements=100, false_positive_rate=0.05)

        blm3 = blm.jaccard_index(blm2)
        self.assertEqual(blm3, None)

    def test_bf_jaccard_invalid(self):
        """ use an invalid type in a jaccard index """
        blm = BloomFilter(est_elements=10, false_positive_rate=0.05)
        blm.add("this is a test")
        self.assertRaises(TypeError, lambda: blm.jaccard_index(1))

    def test_bf_jaccard_invalid_msg(self):
        """ check invalid type in a jaccard index message """
        msg = "The parameter second must be of type BloomFilter or " "a BloomFilterOnDisk"
        blm = BloomFilter(est_elements=10, false_positive_rate=0.05)
        blm.add("this is a test")
        try:
            blm.jaccard_index(1)
        except TypeError as ex:
            self.assertEqual(str(ex), msg)
        else:
            self.assertEqual(True, False)

    def test_bf_union_invalid(self):
        """ use an invalid type in a union """
        blm = BloomFilter(est_elements=10, false_positive_rate=0.05)
        blm.add("this is a test")
        self.assertRaises(TypeError, lambda: blm.jaccard_index(1))

    def test_bf_union_invalid_msg(self):
        """ check invalid type in a union message """
        msg = "The parameter second must be of type BloomFilter or " "a BloomFilterOnDisk"
        blm = BloomFilter(est_elements=10, false_positive_rate=0.05)
        blm.add("this is a test")
        try:
            blm.union(1)
        except TypeError as ex:
            self.assertEqual(str(ex), msg)
        else:
            self.assertEqual(True, False)

    def test_bf_intersection_invalid(self):
        """ use an invalid type in a intersection """
        blm = BloomFilter(est_elements=10, false_positive_rate=0.05)
        blm.add("this is a test")
        self.assertRaises(TypeError, lambda: blm.jaccard_index(1))

    def test_bf_intersec_invalid_msg(self):
        """ check invalid type in a intersection message """
        msg = "The parameter second must be of type BloomFilter or " "a BloomFilterOnDisk"
        blm = BloomFilter(est_elements=10, false_positive_rate=0.05)
        blm.add("this is a test")
        try:
            blm.intersection(1)
        except TypeError as ex:
            self.assertEqual(str(ex), msg)
        else:
            self.assertEqual(True, False)

    def test_bf_jaccard_empty(self):
        """ make sure checking for different bloom filters works jaccard """
        blm = BloomFilter(est_elements=10, false_positive_rate=0.05)
        blm2 = BloomFilter(est_elements=10, false_positive_rate=0.05)

        blm3 = blm.jaccard_index(blm2)
        self.assertEqual(blm3, 1.0)

    def test_bf_stats(self):
        """ test that the information in the stats is correct """
        msg = (
            "BloomFilter:\n"
            "\tbits: 63\n"
            "\testimated elements: 10\n"
            "\tnumber hashes: 4\n"
            "\tmax false positive rate: 0.050000\n"
            "\tbloom length (8 bits): 8\n"
            "\telements added: 10\n"
            "\testimated elements added: 9\n"
            "\tcurrent false positive rate: 0.048806\n"
            "\texport size (bytes): 28\n"
            "\tnumber bits set: 28\n"
            "\tis on disk: no\n"
        )
        blm = BloomFilter(est_elements=10, false_positive_rate=0.05)
        for i in range(0, 10):
            tmp = "this is a test {0}".format(i)
            blm.add(tmp)
        stats = str(blm)
        self.assertEqual(stats, msg)

    def test_bf_export_hex(self):
        """ test the exporting of the bloom filter to a hex string """
        hex_val = "ab749caa12683303000000000000000a000000000000000a3d4ccccd"
        blm = BloomFilter(est_elements=10, false_positive_rate=0.05)
        for i in range(0, 10):
            tmp = "this is a test {0}".format(i)
            blm.add(tmp)
        hex_out = blm.export_hex()

        self.assertEqual(hex_out, hex_val)

    def test_bf_load_hex(self):
        """ test importing a bloom filter from hex value """
        hex_val = "ab749caa12683303000000000000000a000000000000000a3d4ccccd"
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

    def test_bf_load_invalid_hex(self):
        """ test importing a bloom filter from an invalid hex value """
        hex_val = "85f240623b6d9459000000000000000a000000000000000a3d4ccccQ"
        self.assertRaises(InitializationError, lambda: BloomFilter(hex_string=hex_val))

    def test_bf_export_file(self):
        """ test exporting bloom filter to file """
        filename = "test.blm"
        md5_val = "f964432791d3fe72c8fe9c24dfd577ae"
        blm = BloomFilter(est_elements=10, false_positive_rate=0.05)
        blm.add("this is a test")
        blm.export(filename)

        md5_out = calc_file_md5(filename)
        self.assertEqual(md5_out, md5_val)
        os.remove(filename)

    def test_bf_load_file(self):
        """ test loading bloom filter from file """
        filename = "test.blm"

        blm = BloomFilter(est_elements=10, false_positive_rate=0.05)
        blm.add("this is a test")
        blm.export(filename)

        blm2 = BloomFilter(filepath=filename)
        self.assertEqual("this is a test" in blm2, True)
        self.assertEqual("this is not a test" in blm2, False)
        os.remove(filename)

    def test_bf_load_invalid_file(self):
        """ test importing a bloom filter from an invalid filepath """
        filename = "invalid.blm"
        self.assertRaises(InitializationError, lambda: BloomFilter(filepath=filename))

    def test_bf_invalid_params_msg(self):
        """ test importing a bloom filter from an invalid filepath msg """
        filename = "invalid.blm"
        msg = "Insufecient parameters to set up the Bloom Filter"
        try:
            BloomFilter(filepath=filename)
        except InitializationError as ex:
            self.assertEqual(str(ex), msg)
        else:
            self.assertEqual(True, False)

    def test_invalid_fpr(self):
        """ test if invalid false positive rate provided """

        def runner():
            """ runner """
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
        """ test if invalid estimated elements provided """

        def runner():
            """ runner """
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
        """ test if invalid false positive rate provided is non numeric """

        def runner():
            """ runner """
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
        """ test if invalid estimated elements provided is non numeric """

        def runner():
            """ runner """
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
        """ test if invalid estimated elements provided """

        def runner():
            """ runner """
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
        """ test clearing out the bloom filter """
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
        """ test that the different hash works as intended """
        md5_val = "7f590086f9b962387e145899dd001256"  # for default hash used
        filename = "test.blm"
        results = [
            14409285476674975580,
            6203976290780191624,
            5074829385518853901,
            3953072760750514173,
            11782747630324011555,
        ]

        @hash_with_depth_int
        def my_hash(key, depth=1, encoding="utf-8"):
            """ my hash function """
            max64mod = UINT64_T_MAX + 1
            val = int(hashlib.sha512(key.encode(encoding)).hexdigest(), 16)
            return val % max64mod

        blm = BloomFilter(est_elements=10, false_positive_rate=0.05, hash_function=my_hash)
        self.assertEqual(blm.elements_added, 0)
        blm.add("this is a test")
        blm.export(filename)

        md5_out = calc_file_md5(filename)
        self.assertNotEqual(md5_out, md5_val)
        os.remove(filename)

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
        """ test defining a completely different hashing strategy """
        md5_val = "7f590086f9b962387e145899dd001256"  # for default hash used
        filename = "test.blm"
        results = [
            14409285476674975580,
            1383622036369840193,
            10825905054403519891,
            3456253732347153957,
            1494124715262089992,
        ]

        def my_hash(key, depth, encoding="utf-8"):
            """ my hashing strategy """
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
        blm.export(filename)

        md5_out = calc_file_md5(filename)
        self.assertNotEqual(md5_out, md5_val)
        os.remove(filename)

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
    """ Test the Bloom Filter on disk implementation """

    def test_bfod_init(self):
        """ test the initalization of the on disk version """
        filename = "tmp.blm"
        blmd = BloomFilterOnDisk(filename, 10, 0.05)
        self.assertEqual(blmd.false_positive_rate, 0.05000000074505806)
        self.assertEqual(blmd.estimated_elements, 10)
        self.assertEqual(blmd.number_hashes, 4)
        self.assertEqual(blmd.number_bits, 63)
        self.assertEqual(blmd.elements_added, 0)
        self.assertEqual(blmd.is_on_disk, True)
        self.assertEqual(blmd.bloom_length, 63 // 8 + 1)
        blmd.close()
        os.remove(filename)

    def test_bfod_ea(self):
        """ test on disk elements added is correct """
        filename = "tmp.blm"
        blmd = BloomFilterOnDisk(filename, 10, 0.05)
        self.assertEqual(blmd.elements_added, 0)
        blmd.add("this is a test")
        self.assertEqual(blmd.elements_added, 1)
        blmd.close()
        os.remove(filename)

    def test_bfod_ee(self):
        """ test on disk estimate elements is correct on disk """
        filename = "tmp.blm"
        blmd = BloomFilterOnDisk(filename, 10, 0.05)
        res1 = blmd.estimate_elements()
        blmd.add("this is a test")
        res2 = blmd.estimate_elements()
        self.assertNotEqual(res1, res2)
        self.assertEqual(res1, 0)
        self.assertEqual(res2, 1)
        blmd.close()
        os.remove(filename)

    def test_bfod_check(self):
        """ ensure the use of check works on disk bloom """
        filename = "tmp.blm"
        blm = BloomFilterOnDisk(filename, 10, 0.05)
        blm.add("this is a test")
        blm.add("this is another test")
        self.assertEqual(blm.check("this is a test"), True)
        self.assertEqual(blm.check("this is another test"), True)
        self.assertEqual(blm.check("this is yet another test"), False)
        self.assertEqual(blm.check("this is not another test"), False)
        blm.close()
        os.remove(filename)

    def test_bfod_union(self):
        """ test the union of two bloom filters on disk """
        filename = "tmp.blm"
        blm = BloomFilterOnDisk(filename, 10, 0.05)
        blm.add("this is a test")
        blm.add("this is another test")
        blm2 = BloomFilter(10, 0.05)
        blm2.add("this is yet another test")

        blm3 = blm.union(blm2)
        self.assertEqual(blm3.estimate_elements(), 3)
        self.assertEqual(blm3.elements_added, 3)
        self.assertEqual(blm3.check("this is a test"), True)
        self.assertEqual(blm3.check("this is another test"), True)
        self.assertEqual(blm3.check("this is yet another test"), True)
        self.assertEqual(blm3.check("this is not another test"), False)
        blm.close()
        os.remove(filename)

    def test_bfod_intersection(self):
        """ test the intersection of two bloom filters on disk """
        filename = "tmp.blm"
        blm = BloomFilterOnDisk(filename, 10, 0.05)
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
        os.remove(filename)

    def test_bfod_jaccard(self):
        """ test the on disk jaccard index of two bloom filters """
        filename = "tmp.blm"
        blm = BloomFilterOnDisk(filename, 10, 0.05)
        blm.add("this is a test")
        blm.add("this is another test")
        blm2 = BloomFilter(10, 0.05)
        blm2.add("this is another test")
        blm2.add("this is yet another test")

        res = blm.jaccard_index(blm2)
        self.assertGreater(res, 0.33)
        self.assertLess(res, 0.50)
        blm.close()
        os.remove(filename)

    def test_bfod_load_on_disk(self):
        """ test loading a previously saved blm on disk """
        filename = "tmp.blm"

        blm = BloomFilter(10, 0.05)
        blm.add("this is a test")
        blm.export(filename)

        blmd = BloomFilterOnDisk(filename)
        self.assertEqual("this is a test" in blmd, True)
        self.assertEqual("this is not a test" in blmd, False)
        blmd.close()
        os.remove(filename)

    def test_bfod_load_invalid_file(self):
        """ test importing a bloom filter on disk from an invalid filepath """
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
        """ close an on disk bloom using the del syntax """
        filename = "tmp.blm"
        blm = BloomFilterOnDisk(filename, 10, 0.05)
        blm.add("this is a test")
        del blm
        try:
            self.assertEqual(True, blm)
        except UnboundLocalError as ex:
            msg = "local variable 'blm' referenced before assignment"
            self.assertEqual(str(ex), msg)
        else:
            self.assertEqual(True, False)
        os.remove(filename)

    # export to new file
    def test_bfod_export(self):
        """ export to on disk to new file """
        filename = "tmp.blm"
        filename2 = "tmp2.blm"
        blm = BloomFilterOnDisk(filename, 10, 0.05)
        blm.add("this is a test")

        blm.export(filename2)
        blm.close()

        md5_1 = calc_file_md5(filename)
        md5_2 = calc_file_md5(filename2)
        self.assertEqual(md5_1, md5_2)
        os.remove(filename)
        os.remove(filename2)

    def test_bfod_export_hex(self):
        """ test that page error is thrown correctly """

        def runner():
            """ runner """
            blm = BloomFilterOnDisk(filename, 10, 0.05)
            blm.export_hex()

        filename = "tmp.blm"
        self.assertRaises(NotSupportedError, runner)
        os.remove(filename)

    def test_bfod_export_hex_msg(self):
        """ test that page error is thrown correctly """
        filename = "tmp.blm"
        blm = BloomFilterOnDisk(filename, 10, 0.05)
        try:
            blm.export_hex()
        except NotSupportedError as ex:
            msg = "`export_hex` is currently not supported by the on disk " "Bloom Filter"
            self.assertEqual(str(ex), msg)
        else:
            self.assertEqual(True, False)
        os.remove(filename)

    def test_bfod_load_hex(self):
        """ test that page error is thrown correctly """
        filename = "tmp.blm"
        hex_val = "85f240623b6d9459000000000000000a000000000000000a3d4ccccd"
        self.assertRaises(
            NotSupportedError,
            lambda: BloomFilterOnDisk(filepath=filename, hex_string=hex_val),
        )

    def test_bfod_load_hex_msg(self):
        """ test that page error is thrown correctly """
        hex_val = "85f240623b6d9459000000000000000a000000000000000a3d4ccccd"
        filename = "tmp.blm"
        try:
            BloomFilterOnDisk(filepath=filename, hex_string=hex_val)
        except NotSupportedError as ex:
            msg = "Loading from hex_string is currently not supported by " "the on disk Bloom Filter"
            self.assertEqual(str(ex), msg)
        else:
            self.assertEqual(True, False)

    def test_bfod_clear(self):
        """ test clearing out the bloom filter on disk """
        filename = "tmp.blm"
        blm = BloomFilterOnDisk(filepath=filename, est_elements=10, false_positive_rate=0.05)
        self.assertEqual(blm.elements_added, 0)
        for i in range(0, 10):
            tmp = "this is a test {0}".format(i)
            blm.add(tmp)
        self.assertEqual(blm.elements_added, 10)

        blm.clear()
        self.assertEqual(blm.elements_added, 0)
        for idx in range(blm.bloom_length):
            self.assertEqual(blm._get_element(idx), 0)

        os.remove(filename)

    def test_bfod_union_diff(self):
        """make sure checking for different bloom filters on disk works union"""
        filename = "tmp.blm"
        blm = BloomFilterOnDisk(filename, est_elements=10, false_positive_rate=0.05)
        blm.add("this is a test")
        blm2 = BloomFilter(est_elements=10, false_positive_rate=0.05, hash_function=different_hash)

        blm3 = blm.union(blm2)
        self.assertEqual(blm3, None)
        os.remove(filename)

    def test_bfod_intersection_diff(self):
        """make sure checking for different bloom filters on disk works
        intersection
        """
        filename = "tmp.blm"
        blm = BloomFilterOnDisk(filename, est_elements=10, false_positive_rate=0.05)
        blm.add("this is a test")
        blm2 = BloomFilter(est_elements=10, false_positive_rate=0.05, hash_function=different_hash)

        blm3 = blm.intersection(blm2)
        self.assertEqual(blm3, None)
        os.remove(filename)

    def test_bfod_jaccard_diff(self):
        """make sure checking for different bloom filters on disk works
        jaccard
        """
        filename = "tmp.blm"
        blm = BloomFilterOnDisk(filename, est_elements=10, false_positive_rate=0.05)
        blm.add("this is a test")
        blm2 = BloomFilter(est_elements=10, false_positive_rate=0.05, hash_function=different_hash)

        blm3 = blm.jaccard_index(blm2)
        self.assertEqual(blm3, None)
        os.remove(filename)

    def test_cbf_jaccard_invalid(self):
        """ use an invalid type in a jaccard index cbf """
        filename = "tmp.blm"
        blm = BloomFilterOnDisk(filename, est_elements=10, false_positive_rate=0.05)
        blm.add("this is a test")
        self.assertRaises(TypeError, lambda: blm.jaccard_index(1))

    def test_cbf_jaccard_invalid_msg(self):
        """ check invalid type in a jaccard index message cbf """
        msg = "The parameter second must be of type BloomFilter or " "a BloomFilterOnDisk"
        filename = "tmp.blm"
        blm = BloomFilterOnDisk(filename, est_elements=10, false_positive_rate=0.05)
        blm.add("this is a test")
        try:
            blm.jaccard_index(1)
        except TypeError as ex:
            self.assertEqual(str(ex), msg)
        else:
            self.assertEqual(True, False)
        os.remove(filename)

    def test_cbf_union_invalid(self):
        """ use an invalid type in a union cbf """
        filename = "tmp.blm"
        blm = BloomFilterOnDisk(filename, est_elements=10, false_positive_rate=0.05)
        blm.add("this is a test")
        self.assertRaises(TypeError, lambda: blm.jaccard_index(1))
        os.remove(filename)

    def test_cbf_union_invalid_msg(self):
        """ check invalid type in a union message cbf """
        msg = "The parameter second must be of type BloomFilter or " "a BloomFilterOnDisk"
        filename = "tmp.blm"
        blm = BloomFilterOnDisk(filename, est_elements=10, false_positive_rate=0.05)
        blm.add("this is a test")
        try:
            blm.union(1)
        except TypeError as ex:
            self.assertEqual(str(ex), msg)
        else:
            self.assertEqual(True, False)
        os.remove(filename)

    def test_cbf_intersection_invalid(self):
        """ use an invalid type in a intersection cbf """
        filename = "tmp.blm"
        blm = BloomFilterOnDisk(filename, est_elements=10, false_positive_rate=0.05)
        blm.add("this is a test")
        self.assertRaises(TypeError, lambda: blm.jaccard_index(1))
        os.remove(filename)

    def test_cbf_intersec_invalid_msg(self):
        """ check invalid type in a intersection message cbf """
        msg = "The parameter second must be of type BloomFilter or " "a BloomFilterOnDisk"
        filename = "tmp.blm"
        blm = BloomFilterOnDisk(filename, est_elements=10, false_positive_rate=0.05)
        blm.add("this is a test")
        try:
            blm.intersection(1)
        except TypeError as ex:
            self.assertEqual(str(ex), msg)
        os.remove(filename)
