""" probables utilitites tests """

import os
import unittest

from probables.utilities import get_x_bits, is_hex_string, is_valid_file

from .utilities import different_hash


class TestProbablesUtilities(unittest.TestCase):
    """ test the utilities for pyprobables """

    def test_is_hex(self):
        """ test the is valid hex function """
        self.assertTrue(is_hex_string("1234678909abcdef"))
        self.assertTrue(is_hex_string("1234678909ABCDEF"))
        self.assertFalse(is_hex_string("1234678909abcdfq"))
        self.assertFalse(is_hex_string("1234678909ABCDEFQ"))

    def test_is_valid_file(self):
        """ test the is valid file function """
        self.assertFalse(is_valid_file(None))
        self.assertFalse(is_valid_file("./file_doesnt_exist.txt"))
        filename = "./create_this_file.txt"
        with open(filename, "w"):
            pass
        self.assertTrue(is_valid_file(filename))
        os.remove(filename)

    def test_get_x_bits(self):
        """ test the get x bits function """
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
        """ test it on much larger numbers """
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
