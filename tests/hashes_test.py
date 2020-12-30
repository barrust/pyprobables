# -*- coding: utf-8 -*-
""" Unittest class """

import hashlib
import unittest

from probables.constants import UINT64_T_MAX
from probables.hashes import (
    default_fnv_1a,
    default_md5,
    default_sha256,
    hash_with_depth_bytes,
    hash_with_depth_int,
)


class TestHashes(unittest.TestCase):
    """ Test the different hash algorithms """

    def test_default_fnv_1a(self):
        """ test default fnv-1a algorithm """
        this_is_a_test = [
            9816036922139235588,
            2145700485193733482,
            7867438058777009799,
            2613940029162144156,
            15037760171607947637,
        ]
        this_is_also = [
            10902608370166828599,
            16977303254360886697,
            1544262284344120700,
            16848374648812395126,
            4258802402957842529,
        ]
        hashes = default_fnv_1a("this is a test", 5)
        self.assertEqual(hashes, this_is_a_test)
        hashes = default_fnv_1a("this is also a test", 5)
        self.assertEqual(hashes, this_is_also)

    def test_default_md5(self):
        """ test default md5 algorithm """
        this_is_a_test = [
            12174049463882854484,
            10455450501617390806,
            3838261292881602234,
            12102952520950148619,
            12126605867972429202,
        ]
        this_is_also = [
            8938037604889355346,
            9361632593818981393,
            15781121455678786382,
            5600686735535066561,
            1353473153840687523,
        ]
        hashes = default_md5("this is a test", 5)
        self.assertEqual(hashes, this_is_a_test)
        hashes = default_md5("this is also a test", 5)
        self.assertEqual(hashes, this_is_also)

    def test_default_sha256(self):
        """ test default sha256 algorithm """
        this_is_a_test = [
            10244166640140130606,
            5650905005272240665,
            14215057275609328422,
            5952353080197385534,
            4990779931033217093,
        ]
        this_is_also = [
            4140421647067018332,
            9306548247555387104,
            5672713771950536751,
            8501641957786831066,
            15146689942378126332,
        ]
        hashes = default_sha256("this is a test", 5)
        self.assertEqual(hashes, this_is_a_test)
        hashes = default_sha256("this is also a test", 5)
        self.assertEqual(hashes, this_is_also)

    def test_hash_bytes_decorator(self):
        """ test making bytes hashing strategy with decorator """
        results = [
            1164302962920061,
            16735493734761467723,
            18150279091576190542,
            9861778148718857663,
            14008040072978383620,
        ]

        @hash_with_depth_bytes
        def my_hash(key):
            """  my hash function """
            return hashlib.sha512(key).digest()

        self.assertEqual(my_hash("this is a test", 5), results)
        res = my_hash("this is a test", 1)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0], results[0])

    def test_hash_ints_decorator(self):
        """ test making int hashing strategy with decorator """
        results = [
            14409285476674975580,
            6203976290780191624,
            5074829385518853901,
            3953072760750514173,
            11782747630324011555,
        ]

        @hash_with_depth_int
        def my_hash(key, encoding="utf-8"):
            """  my hash function """
            max64mod = UINT64_T_MAX + 1
            val = int(hashlib.sha512(key.encode(encoding)).hexdigest(), 16)
            return val % max64mod

        self.assertEqual(my_hash("this is a test", 5), results)
        res = my_hash("this is a test", 1)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0], results[0])
