"""HyperLogLog implementation"""

import math
from array import array
from collections.abc import ByteString
from io import BytesIO, IOBase
from mmap import mmap
from pathlib import Path
from struct import Struct
from struct import error as StructError

from probables.constants import UINT64_T_MAX
from probables.exceptions import InitializationError, NotSupportedError
from probables.hashes import KeyT, SimpleHashT, hll_hash64
from probables.utilities import MMap, is_valid_file, resolve_path


class HyperLogLog:
    """HyperLogLog implementation for approximate cardinality estimation.

    Args:
        precision (int): The number of bits used to address registers
        filepath (str): Path to file to load
        hash_function (function): Hashing strategy function to use `hf(key, seed)`

    Note:
        The standard error rate is approximately `1.04 / sqrt(2 ** precision)`
    Note:
        The default hashing strategy uses a non-cryptographic 64-bit hash with strong
        avalanche behavior so the sketch can apply textbook register index / suffix splitting.
    """

    __slots__ = ("__precision", "__elements_added", "_registers", "_hash_function")

    __FOOTER_STRUCT = Struct("IQ")

    def __init__(
        self,
        precision: int = 14,
        filepath: str | Path | None = None,
        hash_function: SimpleHashT | None = None,
    ) -> None:
        self.__precision = 0
        self.__elements_added = 0
        self._registers = array("B")

        if filepath is not None:
            if not is_valid_file(filepath):
                raise InitializationError("HyperLogLog: failed to load provided file")
            filepath = resolve_path(filepath)
            self.__load(filepath)
        else:
            self._set_precision(precision)
            self._registers = array("B", [0]) * self.number_registers

        if hash_function is None:
            self._hash_function = hll_hash64
        else:
            self._hash_function = hash_function

    def __str__(self) -> str:
        """String representation of the HyperLogLog"""
        msg = (
            "HyperLogLog:\n"
            "\tPrecision: {0}\n"
            "\tNumber Registers: {1}\n"
            "\tError Rate: {2}\n"
            "\tElements Added: {3}\n"
            "\tCardinality: {4}"
        )
        return msg.format(
            self.precision,
            self.number_registers,
            self.error_rate,
            self.elements_added,
            self.cardinality(),
        )

    def __bytes__(self) -> bytes:
        """Export HyperLogLog to `bytes`"""
        with BytesIO() as filepointer:
            self.export(filepointer)
            return filepointer.getvalue()

    def __len__(self) -> int:
        """Return the estimated cardinality"""
        return self.cardinality()

    @classmethod
    def frombytes(cls, b: ByteString, hash_function: SimpleHashT | None = None) -> "HyperLogLog":
        """Create a HyperLogLog from bytes"""
        try:
            offset = cls.__FOOTER_STRUCT.size
            precision, _ = cls.__FOOTER_STRUCT.unpack_from(bytes(b[-1 * offset :]))
            hll = cls(precision=precision, hash_function=hash_function)
            hll._parse_bytes(b)
        except (StructError, ValueError) as ex:
            raise InitializationError("HyperLogLog: invalid byte stream") from ex
        return hll

    @property
    def precision(self) -> int:
        """int: The number of bits used to address the registers

        Note:
            Not settable"""
        return self.__precision

    @property
    def number_registers(self) -> int:
        """int: The number of registers in the sketch"""
        return 1 << self.precision

    @property
    def error_rate(self) -> float:
        """float: The expected standard error rate of the sketch"""
        return 1.04 / math.sqrt(self.number_registers)

    @property
    def elements_added(self) -> int:
        """int: The number of elements processed by the sketch

        Note:
            Duplicate insertions are counted here even if they do not change the estimate"""
        return self.__elements_added

    def add(self, key: KeyT) -> None:
        """Add the element `key` into the HyperLogLog"""
        self.add_alt(self._hash_function(key, 0))

    def add_alt(self, _hash: int) -> None:
        """Add the pre-hashed value into the HyperLogLog"""
        _hash &= UINT64_T_MAX
        register_idx = _hash >> (64 - self.precision)
        width = 64 - self.precision
        remaining = _hash & ((1 << width) - 1)
        rank = self._rank(remaining, width)
        if rank > self._registers[register_idx]:
            self._registers[register_idx] = rank
        self.__elements_added += 1

    def clear(self) -> None:
        """Reset the HyperLogLog to an empty state"""
        self.__elements_added = 0
        for idx, _ in enumerate(self._registers):
            self._registers[idx] = 0

    def cardinality(self) -> int:
        """Return the estimated cardinality as an integer"""
        return int(round(self.estimate()))

    def estimate(self) -> float:
        """Return the estimated cardinality as a float"""
        indicator = sum(math.pow(2.0, -1 * register) for register in self._registers)
        estimate = self._alpha_mm() / indicator

        zero_count = self._registers.count(0)
        if estimate <= (5.0 * self.number_registers) / 2.0 and zero_count > 0:
            estimate = self.number_registers * math.log(self.number_registers / zero_count)
        elif estimate > (1.0 / 30.0) * (UINT64_T_MAX + 1):
            denominator = UINT64_T_MAX + 1
            ratio = estimate / denominator
            estimate = float(denominator) if ratio >= 1.0 else -1.0 * denominator * math.log(1.0 - ratio)

        return estimate

    def merge(self, second: "HyperLogLog") -> None:
        """Merge the `second` HyperLogLog into the first"""
        if self.precision != second.precision:
            raise NotSupportedError("Unable to merge HyperLogLogs with different precision values")
        if self._hash_function("test", 0) != second._hash_function("test", 0):
            raise NotSupportedError("Hash functions do not match")

        for idx, value in enumerate(second._registers):
            if value > self._registers[idx]:
                self._registers[idx] = value
        self.__elements_added += second.elements_added

    def export(self, file: Path | str | IOBase | mmap) -> None:
        """Export the HyperLogLog to file"""
        if not isinstance(file, IOBase | mmap):
            file = resolve_path(file)
            with open(file, "wb") as filepointer:
                self.export(filepointer)  # type: ignore[arg-type]
        else:
            filepointer = file
            footer = self.__FOOTER_STRUCT.pack(self.precision, self.elements_added)
            filepointer.write(self._registers.tobytes())
            filepointer.write(footer)

    def _alpha_mm(self) -> float:
        """Return alpha * m^2 for the configured register count"""
        m = self.number_registers
        if m == 16:
            alpha = 0.673
        elif m == 32:
            alpha = 0.697
        elif m == 64:
            alpha = 0.709
        else:
            alpha = 0.7213 / (1.0 + (1.079 / m))
        return alpha * m * m

    def _set_precision(self, precision: int) -> None:
        """Set the sketch precision"""
        if precision < 4 or precision > 20:
            raise InitializationError("HyperLogLog: precision must be between 4 and 20")
        self.__precision = precision

    def _parse_bytes(self, data: ByteString) -> None:
        """Parse bytes and populate the sketch state"""
        try:
            offset = self.__FOOTER_STRUCT.size
            precision, elements_added = self.__FOOTER_STRUCT.unpack_from(bytes(data[-1 * offset :]))
            self._set_precision(precision)
            registers = array("B", bytes(data[:-offset]))
            if len(registers) != self.number_registers:
                raise InitializationError("HyperLogLog: invalid byte stream")
            self._registers = registers
            self.__elements_added = elements_added
        except StructError as ex:
            raise InitializationError("HyperLogLog: invalid byte stream") from ex

    def __load(self, file: Path | str | IOBase | mmap | bytes) -> None:
        """Load the HyperLogLog from file"""
        if not isinstance(file, IOBase | mmap | bytes):
            file = resolve_path(file)
            with MMap(file) as filepointer:
                self.__load(filepointer)
        elif isinstance(file, bytes):
            self._parse_bytes(file)
        else:
            self._parse_bytes(file.read())

    @staticmethod
    def _rank(value: int, width: int) -> int:
        """Calculate the rank of the remaining hash bits"""
        if value == 0:
            return width + 1
        return width - value.bit_length() + 1
