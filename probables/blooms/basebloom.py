""" BloomFilter, python implementation
    License: MIT
    Author: Tyler Barrus (barrust@gmail.com)
"""

import array
import math
from binascii import hexlify, unhexlify
from collections.abc import ByteString
from io import BytesIO, IOBase
from mmap import mmap
from numbers import Number
from pathlib import Path
from struct import Struct
from textwrap import wrap
from typing import List, Tuple, Union

from ..exceptions import InitializationError
from ..hashes import HashFuncT, HashResultsT, KeyT, default_fnv_1a
from ..utilities import MMap, is_hex_string, is_valid_file


class BaseBloom(object):
    """basic bloom filter object"""

    __slots__ = [
        "_bloom",
        "__num_bits",
        "__est_elements",
        "__fpr",
        "__number_hashes",
        "__hash_func",
        "_els_added",
        "_on_disk",
        "__impt_type",
        "__blm_type",
        "__bloom_length",
        "__impt_struct",
    ]

    def __init__(
        self,
        blm_type: str,
        est_elements: Union[int, None] = None,
        false_positive_rate: Union[float, None] = None,
        filepath: Union[str, Path, None] = None,
        hex_string: Union[str, None] = None,
        hash_function: Union[HashFuncT, None] = None,
    ) -> None:
        """setup the basic values needed"""
        self._bloom = []
        self.__num_bits = 0  # number of bits
        self.__est_elements = est_elements
        self.__fpr = 0.0
        self.__number_hashes = 0
        self.__hash_func = default_fnv_1a
        self._els_added = 0
        self._on_disk = False  # not on disk
        self.__blm_type = blm_type
        if self.__blm_type in ["regular", "reg-ondisk", "expanding"]:
            self.__impt_type = "B"
        else:
            self.__impt_type = "I"
        self.__impt_struct = Struct(self.__impt_type)

        if blm_type in ["regular", "reg-ondisk", "expanding"]:
            msg = "Insufecient parameters to set up the Bloom Filter"
        else:
            msg = "Insufecient parameters to set up the Counting Bloom Filter"

        if is_valid_file(filepath):
            assert filepath is not None
            self._load(filepath, hash_function)
        elif is_hex_string(hex_string):
            assert hex_string is not None
            self._load_hex(hex_string, hash_function)
        elif est_elements is not None and false_positive_rate is not None:
            h_func, fpr, n_hashes, n_bits = self._set_optimized_params(
                est_elements, float(false_positive_rate), hash_function
            )
            self.__hash_func = h_func  # type: ignore
            self.__fpr = fpr
            self.__number_hashes = n_hashes
            self.__num_bits = n_bits
            if blm_type in ["regular", "reg-ondisk"]:
                self.__bloom_length = int(math.ceil(self.__num_bits / 8.0))
            else:
                self.__bloom_length = self.number_bits
            if blm_type not in ["reg-ondisk"]:
                self._bloom = [0] * self.bloom_length
        else:
            raise InitializationError(msg)

    def __contains__(self, key: KeyT) -> Union[int, bool]:
        """setup the `in` keyword"""
        return self.check(key)

    def clear(self) -> None:
        """Clear or reset the Counting Bloom Filter"""
        self._els_added = 0
        for idx in range(self.bloom_length):
            self._bloom[idx] = 0

    @property
    def false_positive_rate(self) -> float:
        """float: The maximum desired false positive rate

        Note:
            Not settable"""
        return self.__fpr

    @property
    def estimated_elements(self) -> int:
        """int: The maximum number of elements estimated to be added at setup

        Note:
            Not settable"""
        return self.__est_elements  # type: ignore

    @property
    def number_hashes(self) -> int:
        """int: The number of hashes required for the Bloom Filter hashing
        strategy

        Note:
            Not settable"""
        return self.__number_hashes

    @property
    def number_bits(self) -> int:
        """int: Number of bits in the Bloom Filter

        Note:
            Not settable"""
        return self.__num_bits

    @property
    def elements_added(self) -> int:
        """ int: Number of elements added to the Bloom Filter

        Note:
            Changing this can cause the current false positive rate to \
            be reported incorrectly """
        return self._els_added

    @elements_added.setter
    def elements_added(self, val: int):
        """set the els added"""
        self._els_added = val

    @property
    def is_on_disk(self) -> bool:
        """bool: Is the Bloom Filter on Disk or not

        Note:
            Not settable"""
        return self._on_disk

    @property
    def bloom_length(self) -> int:
        """int: Length of the Bloom Filter array

        Note:
            Not settable"""
        return self.__bloom_length

    @property
    def bloom(self) -> List[int]:
        """list(int): The bit/int array"""
        return self._bloom  # type: ignore

    @property
    def hash_function(self) -> HashFuncT:
        """function: The hash function used

        Note:
            Not settable"""
        return self.__hash_func  # type: ignore

    def hashes(self, key: KeyT, depth: Union[int, None] = None) -> HashResultsT:
        """ Return the hashes based on the provided key

            Args:
                key (str): Description of arg1
                depth (int): Number of permutations of the hash to generate; \
                if None, generate `number_hashes`
            Returns:
                List(int): A list of the hashes for the key in int form """
        tmp = depth if depth is not None else self.number_hashes
        return self.__hash_func(key, tmp)

    @classmethod
    def _set_optimized_params(
        cls, estimated_elements: int, false_positive_rate: float, hash_function: Union[HashFuncT, None]
    ) -> Tuple[HashFuncT, float, int, int]:
        """set the parameters to the optimal sizes"""
        tmp_hash = hash_function
        if hash_function is None:
            tmp_hash = default_fnv_1a

        valid_prms = isinstance(estimated_elements, Number) and estimated_elements > 0
        if not valid_prms:
            msg = "Bloom: estimated elements must be greater than 0"
            raise InitializationError(msg)
        valid_prms = isinstance(false_positive_rate, Number) and 0.0 <= false_positive_rate < 1.0
        if not valid_prms:
            msg = "Bloom: false positive rate must be between 0.0 and 1.0"
            raise InitializationError(msg)
        fpr = cls.__FPR_STRUCT.pack(float(false_positive_rate))
        t_fpr = float(cls.__FPR_STRUCT.unpack(fpr)[0])  # to mimic the c version!
        # optimal caluclations
        n_els = estimated_elements
        m_bt = math.ceil((-n_els * math.log(t_fpr)) / 0.4804530139182)  # ln(2)^2
        number_hashes = int(round(0.6931471805599453 * m_bt / n_els))  # math.log(2.0)

        if number_hashes <= 0:  # this should never happen...
            msg = "Bloom: Number hashes is zero; unusable parameters provided"
            raise InitializationError(msg)

        # some assertions to make mypy happy
        assert tmp_hash is not None

        return tmp_hash, t_fpr, number_hashes, int(m_bt)

    __HEADER_STRUCT_FORMAT = "QQf"
    __HEADER_STRUCT = Struct(__HEADER_STRUCT_FORMAT)
    __HEADER_STRUCT_BE = Struct(">" + __HEADER_STRUCT_FORMAT)
    __FPR_STRUCT = Struct("f")

    def _load(
        self,
        file: Union[Path, str, IOBase, mmap, ByteString],
        hash_function: Union[HashFuncT, None] = None,
    ) -> None:
        """load the Bloom Filter from file"""
        if not isinstance(file, (IOBase, mmap, ByteString)):
            file = Path(file)
            with MMap(file) as filepointer:
                self._load(filepointer, hash_function)
        else:
            offset = self.__HEADER_STRUCT.size
            self._parse_footer_set(self.__HEADER_STRUCT, file[-offset:], hash_function)  # type: ignore
            self._set_bloom_length()
            # now read in the bit array!
            self._parse_bloom_array(file)  # type: ignore

    @classmethod
    def _parse_footer(
        cls, stct: Struct, d: ByteString, hash_function: Union[HashFuncT, None] = None
    ) -> Tuple[int, int, float, HashFuncT, int, int]:
        """parse footer returning the data: estimated elements, elements added,
        false positive rate, hash function, number hashes, number bits"""
        e_elms, e_added, fpr = stct.unpack_from(bytearray(d))
        est_elements = int(e_elms)
        els_added = int(e_added)
        fpr = float(fpr)
        h_func, fpr, n_hashes, n_bits = cls._set_optimized_params(est_elements, fpr, hash_function)

        return est_elements, els_added, float(fpr), h_func, int(n_hashes), int(n_bits)

    def _parse_footer_set(self, stct: Struct, d: ByteString, hash_function: Union[HashFuncT, None] = None) -> None:
        est_elms, els_added, fpr, hash_func, num_hashes, num_bits = self._parse_footer(stct, d, hash_function)
        self.__est_elements = est_elms
        self._els_added = els_added
        self.__hash_func = hash_func  # type: ignore
        self.__fpr = fpr
        self.__number_hashes = num_hashes
        self.__num_bits = num_bits

    def _parse_bloom_array(self, b: ByteString):
        offset = self.__impt_struct.size * self.bloom_length
        self._bloom = array.ArrayType(self.__impt_type, bytes(b[:offset])).tolist()

    def _set_bloom_length(self) -> None:
        """House setting the bloom length based on the bloom filter itself"""
        if self.__blm_type in ["regular", "reg-ondisk"]:
            self.__bloom_length = int(math.ceil(self.__num_bits / 8.0))
        else:
            self.__bloom_length = self.number_bits

    def _load_hex(self, hex_string: str, hash_function: Union[HashFuncT, None] = None) -> None:
        """placeholder for loading from hex string"""
        offset = self.__HEADER_STRUCT_BE.size * 2
        self._parse_footer_set(self.__HEADER_STRUCT_BE, unhexlify(hex_string[-offset:]), hash_function)
        self._set_bloom_length()
        tmp_bloom = unhexlify(hex_string[:-offset])
        self._bloom = array.ArrayType(self.__impt_type, tmp_bloom).tolist()

    def export_hex(self) -> str:
        """Export the Bloom Filter as a hex string

        Return:
            str: Hex representation of the Bloom Filter"""
        mybytes = self.__HEADER_STRUCT_BE.pack(
            self.estimated_elements,
            self.elements_added,
            self.false_positive_rate,
        )
        if self.__blm_type in ["regular", "reg-ondisk"]:
            bytes_string = hexlify(bytearray(self.bloom[: self.bloom_length])) + hexlify(mybytes)
        else:
            bytes_string = hexlify(array.ArrayType(self.__impt_type, self.bloom).tobytes()) + hexlify(mybytes)
        return str(bytes_string, "utf-8")

    def export(self, file: Union[Path, str, IOBase, mmap]) -> None:
        """ Export the Bloom Filter to disk

            Args:
                filename (str): The filename to which the Bloom Filter will \
                be written. """

        if not isinstance(file, (IOBase, mmap)):
            with open(file, "wb") as filepointer:
                self.export(filepointer)  # type:ignore
        else:
            file.write(array.ArrayType(self.__impt_type, self.bloom).tobytes())
            file.write(
                self.__HEADER_STRUCT.pack(
                    self.estimated_elements,
                    self.elements_added,
                    self.false_positive_rate,
                )
            )

    def __bytes__(self) -> bytes:
        """Export bloom filter to `bytes`"""
        with BytesIO() as f:
            self.export(f)
            return f.getvalue()

    def export_c_header(self, filename: Union[str, Path]) -> None:
        """ Export the Bloom Filter to disk as a C header file.

            Args:
                filename (str): The filename to which the Bloom Filter will \
                be written. """
        data = (
            "  " + line
            for line in wrap(", ".join(("0x{:02x}".format(e) for e in bytearray.fromhex(self.export_hex()))), 80)
        )
        bloom_type = "standard BloomFilter" if self.__blm_type in ("regular", "reg-ondisk") else "CountingBloomFilter"
        with open(filename, "w") as file:
            print("/* BloomFilter Export of a {} */".format(bloom_type), file=file)
            print("#include <inttypes.h>", file=file)
            print("const uint64_t estimated_elements = ", self.estimated_elements, ";", sep="", file=file)
            print("const uint64_t elements_added = ", self.elements_added, ";", sep="", file=file)
            print("const float false_positive_rate = ", self.false_positive_rate, ";", sep="", file=file)
            print("const uint64_t number_bits = ", self.number_bits, ";", sep="", file=file)
            print("const unsigned int number_hashes = ", self.number_hashes, ";", sep="", file=file)
            print("const unsigned char bloom[] = {", *data, "};", sep="\n", file=file)

    def export_size(self) -> int:
        """Calculate the size of the bloom on disk

        Returns:
            int: Size of the Bloom Filter when exported to disk"""
        return (self.bloom_length * self.__impt_struct.size) + self.__HEADER_STRUCT.size

    def current_false_positive_rate(self) -> float:
        """Calculate the current false positive rate based on elements added

        Return:
            float: The current false positive rate"""
        num = self.number_hashes * -1 * self.elements_added
        dbl = num / float(self.number_bits)
        exp = math.exp(dbl)
        return math.pow((1 - exp), self.number_hashes)

    def estimate_elements(self) -> int:
        """Estimate the number of unique elements added

        Returns:
            int: Number of elements estimated to be inserted"""
        setbits = self._cnt_number_bits_set()
        log_n = math.log(1 - (float(setbits) / float(self.number_bits)))
        tmp = float(self.number_bits) / float(self.number_hashes)
        return int(-1 * tmp * log_n)

    @staticmethod
    def __cnt_set_bits(i: int) -> int:
        """count number of bits set in this int"""
        return bin(i).count("1")

    def _cnt_number_bits_set(self) -> int:
        """calculate the total number of set bits in the bloom"""
        setbits = 0
        for i in list(range(0, self.bloom_length)):
            setbits += self.__cnt_set_bits(self._get_element(i))
        return setbits

    def _get_element(self, idx: int) -> int:
        """wrappper for getting an element from the Bloom Filter!"""
        return self._bloom[idx]  # type: ignore

    def add(self, key: KeyT) -> None:
        """Add the key to the Bloom Filter

        Args:
            key (str): The element to be inserted"""
        hashes = self.hashes(key)
        self.add_alt(hashes)

    def add_alt(self, hashes: HashResultsT) -> None:
        """ Add the element represented by hashes into the Bloom Filter

            Args:
                hashes (list): A list of integers representing the key to \
                insert """
        for i in list(range(0, self.number_hashes)):
            k = int(hashes[i]) % self.number_bits
            idx = k // 8
            j = self._get_element(idx)
            tmp_bit = int(j) | int((1 << (k % 8)))
            self._bloom[idx] = tmp_bit  # type: ignore
        self._els_added += 1

    def check(self, key: KeyT) -> Union[bool, int]:
        """Check if the key is likely in the Bloom Filter

        Args:
            key (str): The element to be checked
        Returns:
            bool: True if likely encountered, False if definately not"""
        hashes = self.hashes(key)
        return self.check_alt(hashes)

    def check_alt(self, hashes: HashResultsT) -> Union[bool, int]:
        """ Check if the element represented by hashes is in the Bloom Filter

            Args:
                hashes (list): A list of integers representing the key to \
                check
            Returns:
                bool: True if likely encountered, False if definately not """
        for i in list(range(0, self.number_hashes)):
            k = int(hashes[i]) % self.number_bits
            if (int(self._get_element(k // 8)) & int((1 << (k % 8)))) == 0:
                return False
        return True

    def _verify_bloom_similarity(self, second: "BaseBloom") -> bool:
        """can the blooms be used in intersection, union, or jaccard index"""
        hash_match = self.number_hashes != second.number_hashes
        same_bits = self.number_bits != second.number_bits
        next_hash = self.hashes("test") != second.hashes("test")
        if hash_match or same_bits or next_hash:
            return False
        return True
