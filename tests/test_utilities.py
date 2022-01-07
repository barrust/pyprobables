#!/usr/bin/env python3
""" probables utilitites tests """

import os
import sys
import unittest
from pathlib import Path
from tempfile import NamedTemporaryFile

this_dir = Path(__file__).parent
sys.path.insert(0, str(this_dir))
sys.path.insert(0, str(this_dir.parent))

from utilities import different_hash

from probables.utilities import MMap, get_x_bits, is_hex_string, is_valid_file

DELETE_TEMP_FILES = True


class TestProbablesUtilities(unittest.TestCase):
    """test the utilities for pyprobables"""

    def test_is_hex(self):
        """test the is valid hex function"""
        self.assertTrue(is_hex_string("123467890abcdef"))
        self.assertTrue(is_hex_string("123467890ABCDEF"))
        self.assertFalse(is_hex_string("123467890abcdfq"))
        self.assertFalse(is_hex_string("123467890ABCDEFQ"))

    def test_is_valid_file(self):
        """test the is valid file function"""
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".rbf", delete=DELETE_TEMP_FILES) as fobj:
            self.assertFalse(is_valid_file(None))
            self.assertFalse(is_valid_file("./file_doesnt_exist.txt"))
            with open(fobj.name, "w"):
                pass
            self.assertTrue(is_valid_file(fobj.name))

    def test_get_x_bits(self):
        """test the get x bits function"""
        for i in range(8):
            res = get_x_bits(i, 4, 2, True)
            self.assertEqual(res, i % 4)
        for i in range(8):
            res = get_x_bits(i, 4, 2, False)
            if i < 4:
                self.assertEqual(res, 0)
            else:
                self.assertEqual(res, 1)

    def test_get_x_bits_large(self):
        """test it on much larger numbers"""
        res = different_hash("this is a test", 1)[0]
        # 1010100101011011100100010101010011110000001010011010000101001011
        tmp1 = get_x_bits(res, 64, 32, True)
        tmp2 = get_x_bits(res, 64, 32, False)
        self.assertEqual(4029260107, tmp1)
        self.assertEqual(2841350484, tmp2)

        tmp1 = get_x_bits(res, 64, 16, True)
        tmp2 = get_x_bits(res, 64, 16, False)
        self.assertEqual(41291, tmp1)
        self.assertEqual(43355, tmp2)

        tmp1 = get_x_bits(res, 64, 8, True)
        tmp2 = get_x_bits(res, 64, 8, False)
        self.assertEqual(75, tmp1)
        self.assertEqual(169, tmp2)

        tmp1 = get_x_bits(res, 64, 4, True)
        tmp2 = get_x_bits(res, 64, 4, False)
        self.assertEqual(11, tmp1)
        self.assertEqual(10, tmp2)

        tmp1 = get_x_bits(res, 64, 2, True)
        tmp2 = get_x_bits(res, 64, 2, False)
        self.assertEqual(3, tmp1)
        self.assertEqual(2, tmp2)

        tmp1 = get_x_bits(res, 64, 1, True)
        tmp2 = get_x_bits(res, 64, 1, False)
        self.assertEqual(1, tmp1)
        self.assertEqual(1, tmp2)

    def test_mmap_functionality(self):
        """test some of the MMap class functionality"""
        data = b"this is a test of the MMap system!"
        with NamedTemporaryFile(dir=os.getcwd(), suffix=".rbf", delete=DELETE_TEMP_FILES) as fobj:
            with open(fobj.name, "wb") as fobj:
                fobj.write(data)
            m = MMap(fobj.name)
            self.assertFalse(m.closed)
            self.assertEqual(data, m.read())
            m.seek(0, os.SEEK_SET)
            self.assertEqual(data[:5], m.read(5))
            self.assertEqual(data[5:], m.read())
            m.close()
            self.assertTrue(m.closed)


if __name__ == "__main__":
    unittest.main()
