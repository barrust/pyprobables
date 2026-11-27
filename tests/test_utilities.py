#!/usr/bin/env python3
"""probables utilitites tests"""

import os
import subprocess
import sys
import unittest
import warnings
from unittest import mock
from pathlib import Path
from tempfile import NamedTemporaryFile

this_dir = Path(__file__).parent
sys.path.insert(0, str(this_dir))
sys.path.insert(0, str(this_dir.parent))

from probables.utilities import (  # noqa: E402
    Bitarray,
    MMap,
    deprecated,
    get_x_bits,
    is_hex_string,
    is_valid_file,
    resolve_path,
)
from tests.utilities import _version_tuple, different_hash, fail_after  # noqa: E402

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

    def test_resolve_path(self):
        """test that resolve_path returns correct"""
        p = resolve_path("~")
        self.assertTrue(p.is_absolute())

        with NamedTemporaryFile(dir=os.getcwd(), suffix=".rbf", delete=DELETE_TEMP_FILES) as fobj:
            with open(fobj.name, "w"):
                pass
            p2 = resolve_path(f"./{fobj.name}")
            self.assertTrue(p2.is_absolute())

    def test_bitarray(self):
        """test bit array basic operations"""
        ba = Bitarray(100)

        self.assertEqual(ba.size, 100)
        self.assertEqual(ba.size_bytes, 13)
        for i in range(ba.size_bytes):
            self.assertEqual(0, ba.bitarray[i])

        # test setting bits
        for i in range(33):
            ba.set_bit(i * 3)

        self.assertEqual(
            ba.as_string(),
            "1001001001001001001001001001001001001001001001001001001001001001001001001001001001001001001001001000",
        )
        self.assertEqual(ba.num_bits_set(), 33)
        self.assertTrue(ba.is_bit_set(3))
        self.assertFalse(ba.is_bit_set(4))
        self.assertEqual(ba[0], 1)
        self.assertEqual(ba[1], 0)

        # test clearing bits
        for i in range(33):
            ba.clear_bit(i * 3)

        self.assertEqual(
            ba.as_string(),
            "0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000",
        )

        for i in range(33):
            ba.set_bit(i * 3)
        self.assertEqual(
            ba.as_string(),
            "1001001001001001001001001001001001001001001001001001001001001001001001001001001001001001001001001000",
        )

        self.assertEqual(ba[2], 0)
        ba[2] = 1
        self.assertEqual(ba[2], 1)
        ba[2] = 0
        self.assertEqual(ba[2], 0)

        ba.clear()
        self.assertEqual(
            ba.as_string(),
            "0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000",
        )

    def test_bitarray_to_bytes(self):
        ba = Bitarray(100)
        for i in range(34):
            ba.set_bit(i * 3)
        b = ba.to_bytes()
        nba = Bitarray.from_bytes(b)
        self.assertEqual(nba.as_string(), ba.as_string())
        for i in range(100):
            self.assertEqual(ba[i], nba[i])
            print(i)
            self.assertEqual(nba[i], 0 if i % 3 != 0 else 1)

    def test_bitarray_export(self):
        with NamedTemporaryFile() as tmp:
            ba = Bitarray(100)
            for i in range(34):
                ba.set_bit(i * 3)
            ba.export(tmp.name)
            nba = Bitarray.from_bytes(tmp.read())
            self.assertEqual(nba.as_string(), ba.as_string())
            for i in range(100):
                self.assertEqual(ba[i], nba[i])
                print(i)
                self.assertEqual(nba[i], 0 if i % 3 != 0 else 1)

    def test_bitarray_invalid_idx(self):
        """use an invalid type in a jaccard index"""
        self.assertRaises(TypeError, lambda: Bitarray("100"))  # type: ignore
        self.assertRaises(ValueError, lambda: Bitarray(-100))
        ba = Bitarray(10)
        self.assertRaises(IndexError, lambda: ba.set_bit(12))
        self.assertRaises(IndexError, lambda: ba.set_bit(-1))
        self.assertRaises(IndexError, lambda: ba.check_bit(-1))
        self.assertRaises(IndexError, lambda: ba.check_bit(12))
        self.assertRaises(IndexError, lambda: ba.clear_bit(-1))
        self.assertRaises(IndexError, lambda: ba.clear_bit(12))

        self.assertRaises(IndexError, lambda: ba[-1])
        self.assertRaises(IndexError, lambda: ba[12])

        def test_set(idx, val):
            ba[idx] = val

        self.assertRaises(IndexError, lambda: test_set(-1, 0))
        self.assertRaises(IndexError, lambda: test_set(12, 0))
        # set as non-valid bit value
        self.assertRaises(ValueError, lambda: test_set(1, 5))
        self.assertRaises(ValueError, lambda: test_set(12, -1))

    def test_import_without_deprecation_warnings(self):
        """importing probables must not use deprecated APIs (ByteString warns on import in Python 3.15)"""
        code = "import probables, probables.blooms, probables.countminsketch, probables.cuckoo, probables.hyperloglog"
        res = subprocess.run(
            [sys.executable, "-W", "error::DeprecationWarning", "-c", code],
            cwd=str(this_dir.parent),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(res.returncode, 0, res.stderr)

    def test_frombytes_accepts_bytes_like(self):
        """every frombytes loads from bytes, bytearray, and memoryview (the BytesLike types)"""
        from probables import (  # pylint: disable=import-outside-toplevel
            BloomFilter,
            CountingBloomFilter,
            CountingCuckooFilter,
            CountMeanSketch,
            CountMinSketch,
            CuckooFilter,
            ExpandingBloomFilter,
            HeavyHitters,
            HyperLogLog,
            HyperLogLogPlusPlus,
            RotatingBloomFilter,
            StreamThreshold,
        )

        cases = [
            (BloomFilter(1000, 0.01), {}),
            (CountingBloomFilter(1000, 0.01), {}),
            (ExpandingBloomFilter(1000, 0.01), {}),
            (RotatingBloomFilter(1000, 0.01), {"max_queue_size": 10}),
            (CountMinSketch(width=100, depth=4), {}),
            (CountMeanSketch(width=100, depth=4), {}),
            (HeavyHitters(width=100, depth=4, num_hitters=5), {"num_hitters": 5}),
            (StreamThreshold(width=100, depth=4, threshold=2), {"threshold": 2}),
            (CuckooFilter(capacity=100), {}),
            (CountingCuckooFilter(capacity=100), {}),
            (HyperLogLog(precision=10), {}),
            (HyperLogLogPlusPlus(precision=12), {}),
            (HyperLogLogPlusPlus(precision=12, sparse_enabled=True), {}),
        ]
        for obj, kwargs in cases:
            for key in ("a", "b", "c", "a"):
                obj.add(key)
            data = bytes(obj)
            for convert in (bytes, bytearray, memoryview):
                with self.subTest(cls=type(obj).__name__, type=convert.__name__):
                    loaded = type(obj).frombytes(convert(data), **kwargs)
                    self.assertEqual(bytes(loaded), data)

    def test_deprecated_warns_every_call(self):
        """deprecated warns on every call, names the function, and keeps its name and docstring"""

        class Thing:
            """a class with deprecated members"""

            @deprecated("9.0.0", "use `new` instead")
            def old(self, val):
                """the old way"""
                return val * 2

            @property
            @deprecated("9.0.0")
            def prop(self):
                """an old property"""
                return 5

        thing = Thing()
        for _ in range(2):
            with self.assertWarnsRegex(
                DeprecationWarning, r"Thing\.old is deprecated and will be removed in 9\.0\.0; use `new` instead$"
            ) as ctx:
                self.assertEqual(thing.old(3), 6)
            self.assertEqual(ctx.filename, __file__)  # points at the caller
        with self.assertWarnsRegex(DeprecationWarning, r"Thing\.prop is deprecated and will be removed in 9\.0\.0$"):
            self.assertEqual(thing.prop, 5)
        self.assertEqual(Thing.old.__name__, "old")
        self.assertEqual(Thing.old.__doc__, "the old way")
        self.assertEqual(Thing.prop.__doc__, "an old property")

    def test_fail_after(self):
        """fail_after runs the test before the version and fails it from that version on, including its release
        candidates"""
        calls = []

        @fail_after("0.8.0")
        def check():
            calls.append(1)

        for version in ("0.7.2", "0.7.10", "0.7.99rc1"):
            with mock.patch("probables.__version__", version):
                check()
        self.assertEqual(len(calls), 3)
        for version in ("0.8.0rc1", "0.8.0", "0.8.1", "1.0.0"):
            with mock.patch("probables.__version__", version):
                self.assertRaisesRegex(AssertionError, "must be removed in version 0.8.0", check)
        self.assertEqual(len(calls), 3)
        self.assertEqual(_version_tuple("0.8.0rc1"), (0, 8, 0))
        self.assertEqual(_version_tuple("0.10"), (0, 10))


if __name__ == "__main__":
    unittest.main()
