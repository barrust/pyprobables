"""HyperLogLog++ implementation with sparse mode and bias correction."""

import math
from array import array
from collections.abc import ByteString
from io import BytesIO, IOBase
from mmap import mmap
from pathlib import Path
from struct import Struct, pack, unpack
from struct import error as StructError

from probables.constants import UINT64_T_MAX
from probables.exceptions import InitializationError, NotSupportedError
from probables.hashes import SimpleHashT
from probables.hyperloglog.hllpp_bias_data import BIAS_DATA, LINEAR_COUNTING_THRESHOLD, RAW_ESTIMATE_DATA
from probables.hyperloglog.hyperloglog import HyperLogLog
from probables.utilities import MMap, is_valid_file, resolve_path


class HyperLogLogPlusPlus(HyperLogLog):
    """HyperLogLog++ implementation with sparse mode and bias correction.

    Args:
        precision (int): The number of bits used to address registers
        filepath (str): Path to file to load
        hash_function (function): Hashing strategy function to use `hf(key, seed)`
        bias_correction (bool): Enable HLL++ bias-correction hook
        sparse_enabled (bool): Enable sparse mode for small cardinalities
        sparse_threshold (int): Optional sparse to dense promotion threshold

    Note:
        Sparse mode provides memory efficiency for small cardinalities.
        Empirical bias correction improves accuracy especially at low cardinalities.
        Automatic promotion from sparse to dense occurs when element count or
        sparse set size exceeds configured thresholds.
    Note:
        Bias and threshold tables are provided for precisions 4 through 18.
        For precisions 19 and 20, bias correction falls back to the raw estimate
        (no empirical bias adjustment), while other HLL++ logic remains active.
    Note:
        Paper: https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/40671.pdf
    """

    __slots__ = ("_bias_correction", "_sparse_enabled", "_sparse_threshold", "_sparse_set", "_is_sparse")

    _HLLPP_HEADER = Struct("4sBB")  # magic(4) + version(1) + flags(1)
    _HLLPP_FOOTER = Struct("IQ")  # precision(4) + elements_added(8)
    _HLLPP_MAGIC = b"HLPP"
    _HLLPP_VERSION = 1
    _SPARSE_MODE_FLAG = 0x01
    _DENSE_MODE_FLAG = 0x00

    # Paper-faithful thresholds and bias calibration data (precision 4 through 18).
    _LINEAR_COUNTING_THRESHOLD = LINEAR_COUNTING_THRESHOLD

    def __init__(
        self,
        precision: int = 14,
        filepath: str | Path | None = None,
        hash_function: SimpleHashT | None = None,
        bias_correction: bool = True,
        sparse_enabled: bool = False,
        sparse_threshold: int | None = None,
    ) -> None:
        super().__init__(precision=precision, hash_function=hash_function)
        self._bias_correction = bool(bias_correction)
        self._sparse_enabled = bool(sparse_enabled)
        self._sparse_threshold = sparse_threshold
        self._sparse_set: set[tuple[int, int]] = set()
        self._is_sparse = sparse_enabled

        if filepath is not None:
            if not is_valid_file(filepath):
                raise InitializationError("HyperLogLogPlusPlus: failed to load provided file")
            filepath = resolve_path(filepath)
            with MMap(filepath) as filepointer:
                self._parse_hllpp_bytes(filepointer.read())

    @classmethod
    def frombytes(cls, b: ByteString, hash_function: SimpleHashT | None = None) -> "HyperLogLogPlusPlus":
        """Create a HyperLogLogPlusPlus from bytes"""
        hllpp = cls(hash_function=hash_function)
        hllpp._parse_hllpp_bytes(bytes(b))
        return hllpp

    @property
    def bias_correction(self) -> bool:
        """bool: Is HLL++ bias-correction enabled"""
        return self._bias_correction

    @property
    def sparse_enabled(self) -> bool:
        """bool: Is sparse mode enabled"""
        return self._sparse_enabled

    @property
    def sparse_threshold(self) -> int | None:
        """int|None: Sparse mode threshold when configured"""
        return self._sparse_threshold

    @property
    def is_sparse(self) -> bool:
        """bool: Is sketch currently using sparse representation"""
        return self._is_sparse

    def __str__(self) -> str:
        """String representation of HyperLogLog++"""
        msg = (
            "HyperLogLog++:\n"
            "\tPrecision: {0}\n"
            "\tNumber Registers: {1}\n"
            "\tError Rate: {2}\n"
            "\tElements Added: {3}\n"
            "\tBias Correction: {4}\n"
            "\tSparse Enabled: {5}\n"
            "\tSparse Mode: {6}\n"
            "\tCardinality: {7}"
        )
        return msg.format(
            self.precision,
            self.number_registers,
            self.error_rate,
            self.elements_added,
            self.bias_correction,
            self.sparse_enabled,
            self.is_sparse,
            self.cardinality(),
        )

    def __bytes__(self) -> bytes:
        """Export HyperLogLog++ to bytes"""
        with BytesIO() as filepointer:
            self.export(filepointer)  # type: ignore[arg-type]
            return filepointer.getvalue()

    def add(self, key: str | bytes | bytearray | int) -> None:
        """Add element to sketch. Automatically promotes sparse to dense if needed."""
        if self._is_sparse:
            self._add_sparse(key)
        else:
            super().add(key)

    def add_alt(self, value: int) -> None:
        """Add pre-hashed element. Automatically promotes sparse to dense if needed."""
        if self._is_sparse:
            self._add_alt_sparse(value)
        else:
            super().add_alt(value)

    def _add_sparse(self, key: str | bytes | bytearray | int) -> None:
        """Add element to sparse representation"""
        raw_hash = self._hash_function(key, 0)
        self._add_alt_sparse(raw_hash)

    def _add_alt_sparse(self, value: int) -> None:
        """Add pre-hashed element to sparse representation"""
        value &= UINT64_T_MAX
        width = 64 - self.precision
        idx = int(value >> width)
        suffix = value & ((1 << width) - 1)
        rho = self._rank(suffix, width)

        self._sparse_set.discard((idx, None))
        existing = next(((i, r) for i, r in self._sparse_set if i == idx), None)
        if existing:
            self._sparse_set.discard(existing)
            rho = max(rho, existing[1])

        self._sparse_set.add((idx, rho))
        self._HyperLogLog__elements_added += 1

        threshold = self._sparse_threshold or max(int(1.5 * self.number_registers), 128)
        if len(self._sparse_set) > threshold:
            self._promote_to_dense()

    def _promote_to_dense(self) -> None:
        """Promote from sparse to dense representation"""
        for idx, rho in self._sparse_set:
            self._registers[idx] = max(self._registers[idx], rho)
        self._sparse_set.clear()
        self._is_sparse = False

    def merge(self, other: "HyperLogLogPlusPlus | HyperLogLog") -> None:
        """Merge another sketch into this one"""
        if not isinstance(other, (HyperLogLog, HyperLogLogPlusPlus)):
            raise NotSupportedError("Unable to merge with provided type")
        if self.precision != other.precision:
            raise NotSupportedError("Unable to merge HyperLogLogPlusPlus with different precision values")
        if self._hash_function("test", 0) != other._hash_function("test", 0):
            raise NotSupportedError("Hash functions do not match")

        if isinstance(other, HyperLogLogPlusPlus) and other.is_sparse:
            if self._is_sparse:
                self._merge_sparse_sparse(other)
            else:
                self._merge_dense_sparse(other)
        else:
            if self._is_sparse:
                for idx, rho in self._sparse_set:
                    self._registers[idx] = rho
                self._sparse_set.clear()
                self._is_sparse = False
            super().merge(other)

    def _merge_sparse_sparse(self, other: "HyperLogLogPlusPlus") -> None:
        """Merge two sparse sketches"""
        combined: dict[int, int] = {}
        for idx, rho in self._sparse_set:
            combined[idx] = rho
        for idx, rho in other._sparse_set:
            combined[idx] = max(combined.get(idx, 0), rho)

        self._sparse_set = {(idx, rho) for idx, rho in combined.items()}
        self._HyperLogLog__elements_added += other.elements_added

        threshold = self._sparse_threshold or max(int(1.5 * self.number_registers), 128)
        if len(self._sparse_set) > threshold:
            self._promote_to_dense()

    def _merge_dense_sparse(self, other: "HyperLogLogPlusPlus") -> None:
        """Merge sparse sketch into dense sketch"""
        for idx, rho in other._sparse_set:
            self._registers[idx] = max(self._registers[idx], rho)
        self._HyperLogLog__elements_added += other.elements_added

    def estimate(self) -> float:
        """Return the estimated cardinality as a float"""
        if self._is_sparse:
            return self._estimate_sparse()

        raw_estimate = self._raw_estimate_dense()
        m = self.number_registers
        zero_count = self._registers.count(0)

        # Paper-faithful ordering: bias-correct the raw estimator in the small-range regime.
        if raw_estimate <= (5.0 * m):
            corrected = self._apply_bias_correction(raw_estimate) if self.bias_correction else raw_estimate

            # Use linear counting only under precision-specific thresholds.
            if zero_count > 0:
                linear_count = m * math.log(m / zero_count)
                threshold = self._LINEAR_COUNTING_THRESHOLD.get(self.precision, 0)
                if linear_count <= threshold:
                    return linear_count

            return corrected

        return self._apply_large_range_correction(raw_estimate)

    def _raw_estimate_dense(self) -> float:
        """Return raw HLL estimate without small-range or large-range correction."""
        indicator = sum(math.pow(2.0, -1 * register) for register in self._registers)
        return self._alpha_mm() / indicator

    def _apply_large_range_correction(self, estimate: float) -> float:
        """Apply the large-range correction used by the base HLL implementation."""
        if estimate > (1.0 / 30.0) * (UINT64_T_MAX + 1):
            denominator = UINT64_T_MAX + 1
            ratio = estimate / denominator
            if ratio >= 1.0:
                return float(denominator)
            return -1.0 * denominator * math.log(1.0 - ratio)
        return estimate

    def _estimate_sparse(self) -> float:
        """Estimate cardinality in sparse mode"""
        if len(self._sparse_set) == 0:
            return 0.0
        threshold = self.number_registers / 2
        if len(self._sparse_set) < threshold:
            return self.number_registers * math.log(
                self.number_registers / (self.number_registers - len(self._sparse_set))
            )
        return super().estimate()

    def clear(self) -> None:
        """Clear the sketch"""
        super().clear()
        self._sparse_set.clear()
        self._is_sparse = self._sparse_enabled

    def export(self, file: Path | str | IOBase | mmap) -> None:
        """Export HyperLogLog++ to file"""
        if not isinstance(file, IOBase | mmap):
            file = resolve_path(file)
            with open(file, "wb") as filepointer:
                self.export(filepointer)  # type: ignore[arg-type]
        else:
            filepointer = file
            flags = self._SPARSE_MODE_FLAG if self._is_sparse else self._DENSE_MODE_FLAG
            header = self._HLLPP_HEADER.pack(self._HLLPP_MAGIC, self._HLLPP_VERSION, flags)
            footer = self._HLLPP_FOOTER.pack(self.precision, self.elements_added)

            filepointer.write(header)

            if self._is_sparse:
                num_entries = len(self._sparse_set)
                filepointer.write(pack("H", num_entries))
                for idx, rho in sorted(self._sparse_set):
                    filepointer.write(pack("HB", idx, rho))
            else:
                filepointer.write(self._registers.tobytes())

            filepointer.write(footer)

    def _apply_bias_correction(self, estimate: float) -> float:
        """Apply nearest-neighbor empirical bias correction from HLL++ paper."""
        # The original HLL++ dataset provides bias tables up to precision 18.
        if self.precision > 18:
            return estimate

        raw_points = RAW_ESTIMATE_DATA.get(self.precision, ())
        bias_points = BIAS_DATA.get(self.precision, ())
        if len(raw_points) == 0 or len(raw_points) != len(bias_points):
            return estimate

        # Paper-style nearest-neighbor bias estimation (k=6 in the paper).
        k_neighbors = min(6, len(raw_points))
        nearest = sorted(range(len(raw_points)), key=lambda i: abs(raw_points[i] - estimate))[:k_neighbors]
        mean_bias = sum(bias_points[i] for i in nearest) / float(k_neighbors)
        corrected = estimate - mean_bias
        return max(0.0, corrected)

    def _parse_hllpp_bytes(self, data: ByteString) -> None:
        """Parse HyperLogLog++ bytes and populate state"""
        try:
            header_size = self._HLLPP_HEADER.size
            magic, version, flags = self._HLLPP_HEADER.unpack_from(bytes(data[:header_size]))
            if magic != self._HLLPP_MAGIC or version != self._HLLPP_VERSION:
                raise InitializationError("HyperLogLogPlusPlus: invalid byte stream")

            is_sparse = (flags & self._SPARSE_MODE_FLAG) != 0
            data = bytes(data[header_size:])

            if is_sparse:
                self._parse_hllpp_sparse_bytes(data)
            else:
                self._parse_hllpp_dense_bytes(data)

        except (StructError, ValueError) as ex:
            raise InitializationError("HyperLogLogPlusPlus: invalid byte stream") from ex

    def _parse_hllpp_dense_bytes(self, data: ByteString) -> None:
        """Parse HyperLogLog++ dense format"""
        footer_size = self._HLLPP_FOOTER.size
        register_data = bytes(data[:-footer_size])
        footer_data = bytes(data[-footer_size:])

        precision, elements_added = self._HLLPP_FOOTER.unpack(footer_data)
        self._set_precision(precision)
        self._HyperLogLog__elements_added = elements_added
        self._registers = array("B", register_data)

        if len(self._registers) != self.number_registers:
            raise InitializationError("HyperLogLogPlusPlus: register length mismatch")

    def _parse_hllpp_sparse_bytes(self, data: ByteString) -> None:
        """Parse HyperLogLog++ sparse format"""
        footer_size = self._HLLPP_FOOTER.size
        sparse_data = bytes(data[:-footer_size])
        footer_data = bytes(data[-footer_size:])

        precision, elements_added = self._HLLPP_FOOTER.unpack(footer_data)
        self._set_precision(precision)
        self._HyperLogLog__elements_added = elements_added
        self._is_sparse = True

        num_entries = unpack("H", sparse_data[:2])[0]
        offset = 2
        for _ in range(num_entries):
            idx, rho = unpack("HB", sparse_data[offset : offset + 3])
            self._sparse_set.add((idx, rho))
            offset += 3
