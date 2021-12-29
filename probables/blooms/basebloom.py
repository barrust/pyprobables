""" BloomFilter, python implementation
    License: MIT
    Author: Tyler Barrus (barrust@gmail.com)
"""

import math
import os
import typing
from abc import abstractmethod
from binascii import hexlify, unhexlify
from collections.abc import ByteString
from io import BytesIO, IOBase
from itertools import chain
from mmap import mmap
from numbers import Number
from pathlib import Path
from struct import Struct, calcsize, pack, unpack
from textwrap import wrap

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
    ]

    def __init__(
        self,
        blm_type: str,
        est_elements: typing.Optional[int] = None,
        false_positive_rate: typing.Optional[float] = None,
        filepath: typing.Optional[str] = None,
        hex_string: typing.Optional[str] = None,
        hash_function: typing.Optional[HashFuncT] = None,
    ) -> None:
        """setup the basic values needed"""
        self._bloom = None
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

        if blm_type in ["regular", "reg-ondisk", "expanding"]:
            msg = "Insufecient parameters to set up the Bloom Filter"
        else:
            msg = "Insufecient parameters to set up the Counting Bloom Filter"

        if is_valid_file(filepath):
            assert filepath is not None
            self.__load(blm_type, filepath, hash_function)
        elif is_hex_string(hex_string):
            assert hex_string is not None
            self._load_hex(hex_string, hash_function)
        elif est_elements is not None and false_positive_rate is not None:
            vals = self._set_optimized_params(est_elements, float(false_positive_rate), hash_function)
            self.__hash_func = vals[0]  # type: ignore
            self.__fpr = vals[1]
            self.__number_hashes = vals[2]
            self.__num_bits = vals[3]
            if blm_type in ["regular", "reg-ondisk"]:
                self.__bloom_length = int(math.ceil(self.__num_bits / 8.0))
            else:
                self.__bloom_length = self.number_bits
            if blm_type not in ["reg-ondisk"]:
                self._bloom = [0] * self.bloom_length
        else:
            raise InitializationError(msg)

    def __contains__(self, key: KeyT) -> typing.Union[int, bool]:
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
    def bloom(self) -> typing.List[int]:
        """list(int): The bit/int array"""
        return self._bloom  # type: ignore

    @property
    def hash_function(self) -> HashFuncT:
        """function: The hash function used

        Note:
            Not settable"""
        return self.__hash_func  # type: ignore

    def hashes(self, key: KeyT, depth: typing.Optional[int] = None) -> HashResultsT:
        """ Return the hashes based on the provided key

            Args:
                key (str): Description of arg1
                depth (int): Number of permutations of the hash to generate; \
                if None, generate `number_hashes`
            Returns:
                List(int): A list of the hashes for the key in int form """
        tmp = depth if depth is not None else self.number_hashes
        return self.__hash_func(key, tmp)

    @staticmethod
    def _set_optimized_params(
        estimated_elements: int, false_positive_rate: float, hash_function: typing.Optional[HashFuncT]
    ) -> typing.Tuple[HashFuncT, float, int, int]:
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

        fpr = pack("f", float(false_positive_rate))
        t_fpr = unpack("f", fpr)[0]  # to mimic the c version!
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

    HEADER_STRUCT_FORMAT = "QQf"
    HEADER_STRUCT = Struct(HEADER_STRUCT_FORMAT)
    HEADER_STRUCT_BE = Struct(">" + HEADER_STRUCT_FORMAT)

    def __load(
        self,
        blm_type: str,
        file: typing.Union[Path, str, IOBase, mmap],
        hash_function: typing.Optional[HashFuncT] = None,
    ) -> None:
        """load the Bloom Filter from file"""
        # read in the needed information, and then call _set_optimized_params
        # to set everything correctly
        if not isinstance(file, (IOBase, mmap)):
            file = Path(file)
            with MMap(file) as filepointer:
                self.__load(blm_type, filepointer, hash_function)
        else:
            offset = self.__class__.HEADER_STRUCT.size
            file.seek(offset * -1, os.SEEK_END)
            fpr = self._parse_footer(self.__class__.HEADER_STRUCT, file.read(offset))
            vals = self._set_optimized_params(self.__est_elements, fpr, hash_function)
            self.__hash_func = vals[0]  # type: ignore
            self.__fpr = vals[1]
            self.__number_hashes = vals[2]
            self.__num_bits = vals[3]
            if blm_type in ["regular", "reg-ondisk"]:
                self.__bloom_length = int(math.ceil(self.__num_bits / 8.0))
            else:
                self.__bloom_length = self.number_bits
            # now read in the bit array!
            file.seek(0, os.SEEK_SET)
            offset = calcsize(self.__impt_type) * self.bloom_length
            rep = self.__impt_type * self.bloom_length
            self._bloom = list(unpack(rep, file.read(offset)))

    def _parse_footer(self, stct: Struct, d: ByteString) -> float:
        tmp_data = stct.unpack_from(bytearray(d))
        self.__est_elements = tmp_data[0]
        self._els_added = tmp_data[1]
        fpr = float(tmp_data[2])
        return fpr

    def _load_hex(self, hex_string: str, hash_function: typing.Optional[HashFuncT] = None) -> None:
        """placeholder for loading from hex string"""
        offset = self.__class__.HEADER_STRUCT_BE.size * 2
        fpr = self._parse_footer(self.__class__.HEADER_STRUCT_BE, unhexlify(hex_string[-offset:]))
        vals = self._set_optimized_params(self.__est_elements, fpr, hash_function)
        self.__hash_func = vals[0]  # type: ignore
        self.__fpr = vals[1]
        self.__number_hashes = vals[2]
        self.__num_bits = vals[3]
        if self.__blm_type in ["regular", "reg-ondisk"]:
            self.__bloom_length = int(math.ceil(self.__num_bits / 8.0))
        else:
            self.__bloom_length = self.number_bits

        tmp_bloom = unhexlify(hex_string[:-offset])
        rep = self.__impt_type * self.bloom_length
        self._bloom = list(unpack(rep, tmp_bloom))

    def export_hex(self) -> str:
        """Export the Bloom Filter as a hex string

        Return:
            str: Hex representation of the Bloom Filter"""
        mybytes = self.__class__.HEADER_STRUCT_BE.pack(
            self.estimated_elements,
            self.elements_added,
            self.false_positive_rate,
        )
        if self.__blm_type in ["regular", "reg-ondisk"]:
            bytes_string = hexlify(bytearray(self.bloom[: self.bloom_length])) + hexlify(mybytes)
        else:
            bytes_string = b""
            for val in self.bloom:
                bytes_string += hexlify(pack(self.__impt_type, val))
            bytes_string += hexlify(mybytes)
        return str(bytes_string, "utf-8")

    def export(self, file: typing.Union[Path, str, IOBase, mmap]) -> None:
        """ Export the Bloom Filter to disk

            Args:
                filename (str): The filename to which the Bloom Filter will \
                be written. """

        if not isinstance(file, (IOBase, mmap)):
            with open(file, "wb") as filepointer:
                self.export(filepointer)  # type:ignore
        else:
            rep = self.__impt_type * self.bloom_length
            file.write(pack(rep, *self.bloom))
            file.write(
                self.__class__.HEADER_STRUCT.pack(
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

    def export_c_header(self, filename: str) -> None:
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
        tmp_b = calcsize(self.__impt_type)
        return (self.bloom_length * tmp_b) + self.__class__.HEADER_STRUCT.size

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

    def check(self, key: KeyT) -> typing.Union[bool, int]:
        """Check if the key is likely in the Bloom Filter

        Args:
            key (str): The element to be checked
        Returns:
            bool: True if likely encountered, False if definately not"""
        hashes = self.hashes(key)
        return self.check_alt(hashes)

    def check_alt(self, hashes: HashResultsT) -> typing.Union[bool, int]:
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

    @abstractmethod
    def union(self, second) -> typing.Optional["BaseBloom"]:
        """Return a new Bloom Filter that contains the typing.Union of the two"""
        pass

    @abstractmethod
    def intersection(self, second) -> typing.Optional["BaseBloom"]:
        """Return a new Bloom Filter that contains the intersection of the
        two"""
        pass

    @abstractmethod
    def jaccard_index(self, second) -> typing.Optional[float]:
        """Return a the Jaccard Similarity score between two bloom filters"""
        pass

    def _verify_bloom_similarity(self, second: "BaseBloom") -> bool:
        """can the blooms be used in intersection, typing.Union, or jaccard index"""
        hash_match = self.number_hashes != second.number_hashes
        same_bits = self.number_bits != second.number_bits
        next_hash = self.hashes("test") != second.hashes("test")
        if hash_match or same_bits or next_hash:
            return False
        return True
