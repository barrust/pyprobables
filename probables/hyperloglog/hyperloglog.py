"""HyperLogLog implementation"""

import math
from array import array
from io import BytesIO, IOBase
from mmap import mmap
from pathlib import Path
from struct import Struct
from struct import error as StructError

from probables.constants import UINT64_T_MAX
from probables.exceptions import InitializationError, NotSupportedError
from probables.hashes import KeyT, SimpleHashT, _fmix64, hll_hash64
from probables.utilities import BytesLike, MMap, is_valid_file, resolve_path

# 2^-rank for every possible register value, so the estimate sums table lookups in C
INVERSE_POWERS_OF_TWO = tuple(math.ldexp(1.0, -rank) for rank in range(256))


class HyperLogLog:
    """HyperLogLog implementation for approximate cardinality estimation.

    Args:
        precision (int): The number of bits used to address registers
        filepath (str): Path to file to load
        hash_function (function): Hashing strategy function to use `hf(key, seed)`; its result \
            is mixed to 64 bits, so shorter hashes (such as `fnv_1a_32`) still use every register

    Note:
        The standard error rate is approximately `1.04 / sqrt(2 ** precision)`
    Note:
        The default hashing strategy uses a non-cryptographic 64-bit hash with strong
        avalanche behavior so the sketch can apply textbook register index / suffix splitting.
    Note:
        `add_alt()` uses its value as is, so it should be a well mixed 64-bit hash.
    """

    __slots__ = ("__precision", "_elements_added", "_registers", "_hash_function")

    # header: magic(4) + version(1); registers follow, then the footer: precision(4) + elements_added(8)
    __HEADER_STRUCT = Struct("<4sB")
    __FOOTER_STRUCT = Struct("<IQ")
    _HLL_MAGIC = b"PHLL"
    _HLL_VERSION = 1

    def __init__(
        self,
        precision: int = 14,
        filepath: str | Path | None = None,
        hash_function: SimpleHashT | None = None,
    ) -> None:
        self.__precision = 0
        self._elements_added = 0
        self._registers = array("B")
        self._hash_function: SimpleHashT = hll_hash64 if hash_function is None else hash_function
        if filepath is not None:
            if not is_valid_file(filepath):
                raise InitializationError(f"{self.__class__.__name__}: failed to load provided file")
            self.__load(resolve_path(filepath))
        else:
            self._set_precision(precision)
            self._registers = self._new_registers()

    def _new_registers(self) -> array:
        """array: the registers for a new, empty sketch"""
        return array("B", [0]) * self.number_registers

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
    def frombytes(cls, b: BytesLike, hash_function: SimpleHashT | None = None) -> "HyperLogLog":
        """Create a HyperLogLog from bytes"""
        # the smallest precision, so the registers it allocates (16 bytes) cost nothing to replace
        hll = cls(precision=4, hash_function=hash_function)
        hll._parse_bytes(b)
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
        return self._elements_added

    def add(self, key: KeyT) -> None:
        """Add the element `key` into the HyperLogLog"""
        self.add_alt(self._hash(key))

    def _hash(self, key: KeyT) -> int:
        """int: the 64-bit hash of `key`

        The default hash is already mixed; any other hash is mixed with a 64-bit finalizer, since
        the register index uses the top bits and a 32-bit hash would leave them all zero."""
        if self._hash_function is hll_hash64:
            return self._hash_function(key, 0)
        return _fmix64(self._hash_function(key, 0))

    def add_alt(self, _hash: int) -> None:
        """Add the pre-hashed value into the HyperLogLog"""
        _hash &= UINT64_T_MAX
        register_idx = _hash >> (64 - self.precision)
        width = 64 - self.precision
        remaining = _hash & ((1 << width) - 1)
        rank = self._rank(remaining, width)
        if rank > self._registers[register_idx]:
            self._registers[register_idx] = rank
        self._elements_added += 1

    def clear(self) -> None:
        """Reset the HyperLogLog to an empty state"""
        self._elements_added = 0
        self._registers = array("B", [0]) * self.number_registers

    def cardinality(self) -> int:
        """Return the estimated cardinality as an integer"""
        return int(round(self.estimate()))

    def estimate(self) -> float:
        """Return the estimated cardinality as a float"""
        estimate = self._raw_estimate()
        zero_count = self._zero_registers()
        if estimate <= (5.0 * self.number_registers) / 2.0 and zero_count > 0:
            return self.number_registers * math.log(self.number_registers / zero_count)
        return self._apply_large_range_correction(estimate)

    @staticmethod
    def _apply_large_range_correction(estimate: float) -> float:
        """Correct for 64-bit hash collisions and keep the estimate at or below 2^64

        Note:
            Only register states far beyond any real input (such as loaded or `add_alt` values with
            maximal ranks) reach this; it keeps the estimate finite and meaningful for those."""
        if estimate > (1.0 / 30.0) * (UINT64_T_MAX + 1):
            denominator = UINT64_T_MAX + 1
            ratio = estimate / denominator
            if ratio >= 1.0:
                return float(denominator)
            return -1.0 * denominator * math.log(1.0 - ratio)
        return estimate

    def _zero_registers(self) -> int:
        """int: the number of empty dense registers (counted on the bytes, which is done in C)"""
        return self._registers.tobytes().count(0)

    def _raw_estimate(self) -> float:
        """Return the raw HyperLogLog estimate of the dense registers, without corrections"""
        indicator = sum(map(INVERSE_POWERS_OF_TWO.__getitem__, self._registers))
        return self._alpha_mm() / indicator

    def merge(self, second: "HyperLogLog") -> None:
        """Merge the `second` HyperLogLog into the first"""
        if self.precision != second.precision:
            raise NotSupportedError("Unable to merge HyperLogLogs with different precision values")
        if self._hash_function("test", 0) != second._hash_function("test", 0):
            raise NotSupportedError("Hash functions do not match")

        for idx, value in second._register_items():
            if value > self._registers[idx]:
                self._registers[idx] = value
        self._elements_added += second.elements_added

    def _register_items(self):
        """Iterate over the (index, rank) of the registers that are set"""
        return ((idx, value) for idx, value in enumerate(self._registers) if value)

    def export(self, file: Path | str | IOBase | mmap) -> None:
        """Export the HyperLogLog to file"""
        if not isinstance(file, IOBase | mmap):
            file = resolve_path(file)
            with open(file, "wb") as filepointer:
                self.export(filepointer)  # type: ignore[arg-type]
        else:
            file.write(self.__HEADER_STRUCT.pack(self._HLL_MAGIC, self._HLL_VERSION))
            file.write(self._registers.tobytes())
            file.write(self.__FOOTER_STRUCT.pack(self.precision, self.elements_added))

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

    def _parse_bytes(self, data: BytesLike | mmap) -> None:
        """Parse bytes and populate the sketch state"""
        payload = bytes(data)
        header_size, footer_size = self.__HEADER_STRUCT.size, self.__FOOTER_STRUCT.size
        if len(payload) < header_size + footer_size:
            raise InitializationError("HyperLogLog: invalid byte stream")
        magic, version = self.__HEADER_STRUCT.unpack_from(payload)
        if magic != self._HLL_MAGIC or version != self._HLL_VERSION:
            raise InitializationError("HyperLogLog: invalid byte stream; not an exported HyperLogLog")
        try:
            precision, elements_added = self.__FOOTER_STRUCT.unpack_from(payload, len(payload) - footer_size)
            self._set_precision(precision)
        except (InitializationError, StructError, ValueError) as ex:
            raise InitializationError("HyperLogLog: invalid byte stream") from ex
        self._load_registers(payload[header_size:-footer_size], elements_added)

    def _load_registers(self, register_data: bytes, elements_added: int) -> None:
        """Validate and set the dense registers for the current precision

        Raises:
            InitializationError: If the length, a rank, or the element count is invalid"""
        name = self.__class__.__name__
        if len(register_data) != self.number_registers:
            raise InitializationError(f"{name}: register length mismatch")
        registers = array("B", register_data)
        max_rank = 64 - self.precision + 1
        occupied = self.number_registers - register_data.count(0)
        if max(registers) > max_rank or elements_added < occupied or (elements_added == 0) != (occupied == 0):
            raise InitializationError(f"{name}: invalid register data")
        self._registers = registers
        self._elements_added = elements_added

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
