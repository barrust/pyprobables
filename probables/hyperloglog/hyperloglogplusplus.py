"""HyperLogLog++ implementation with sparse mode and bias correction."""

import math
import sys
from array import array
from bisect import bisect_left
from collections.abc import ByteString
from io import BytesIO, IOBase
from itertools import chain
from mmap import mmap
from pathlib import Path
from struct import Struct
from struct import error as StructError

from probables.constants import UINT64_T_MAX
from probables.exceptions import InitializationError, NotSupportedError
from probables.hashes import KeyT, SimpleHashT
from probables.hyperloglog.hllpp_bias_data import (
    BIAS_DATA,
    LINEAR_COUNTING_THRESHOLD,
    RAW_ESTIMATE_DATA,
)
from probables.hyperloglog.hyperloglog import HyperLogLog
from probables.utilities import resolve_path

# Sparse entries hold a register index at SPARSE_PRECISION bits and its rank, packed as
# (index << 6) | rank in an unsigned 32-bit integer (Heule et al. 2013, Section 5.3).
SPARSE_PRECISION = 25
_SPARSE_WIDTH = 64 - SPARSE_PRECISION  # hash bits after the sparse index; ranks are at most 40
_SPARSE_SUFFIX_MASK = (1 << _SPARSE_WIDTH) - 1
_RANK_BITS = 6
_RANK_MASK = (1 << _RANK_BITS) - 1
_UINT32_TYPECODE = next(code for code in "IL" if array(code).itemsize == 4)
_BIG_ENDIAN = sys.byteorder == "big"


def _largest_rank_per_index(entries) -> list[int]:
    """list(int): packed entries sorted by index, with only the largest rank for each index"""
    # sorted by index then rank, so the last entry for each index has the largest rank
    combined = sorted(entries)
    unique = [
        entry
        for entry, after in zip(combined, combined[1:], strict=False)
        if entry >> _RANK_BITS != after >> _RANK_BITS
    ]
    return unique + combined[-1:]


class HyperLogLogPlusPlus(HyperLogLog):
    """HyperLogLog++ implementation with sparse mode and bias correction.

    Args:
        precision (int): The number of bits used to address registers
        filepath (str): Path to file to load
        hash_function (function): Hashing strategy function to use `hf(key, seed)`; its result \
            is mixed to 64 bits, so shorter hashes (such as `fnv_1a_32`) still use every register
        bias_correction (bool): Enable HLL++ empirical bias correction; when disabled the estimate \
            matches the original HyperLogLog
        sparse_enabled (bool): Start in sparse mode, for small cardinalities
        sparse_threshold (int): The number of sparse entries at which to switch to dense \
            registers; by default `number_registers // 4`, where both use the same memory

    Note:
        Empirical bias correction improves accuracy for small and medium cardinalities.
    Note:
        Sparse mode follows the paper: it stores only the registers that are set, each as a
        4-byte entry with its index at precision 25, and estimates with linear counting over
        2^25 registers, so small cardinalities are nearly exact. It switches to dense
        registers once the entries would use as much memory as the registers, converting
        each entry to the sketch's precision.
    Note:
        Bias and threshold tables are provided for precisions 4 through 18.
        For precisions 19 and 20 there is no empirical bias adjustment, and linear counting
        is used below `2.5 * number_registers` as in the original HyperLogLog. The same rule
        is used when bias correction is disabled.
    Note:
        When loading from a file the precision, bias_correction, sparse_enabled and
        sparse_threshold are read from the file; the arguments are not used.
    Note:
        Paper: https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/40671.pdf
    """

    __slots__ = (
        "_bias_correction",
        "_sparse_enabled",
        "_sparse_threshold",
        "_sparse",
        "_sparse_buffer",
        "_is_sparse",
    )

    # magic(4) + version(1) + flags(1) + sparse_threshold(4, 0 if not set)
    _HLLPP_HEADER = Struct("<4sBBI")
    _HLLPP_FOOTER = Struct("<IQ")  # precision(4) + elements_added(8)
    _SPARSE_COUNT = Struct("<I")
    _HLLPP_MAGIC = b"HLPP"
    _HLLPP_VERSION = 3
    _SPARSE_MODE_FLAG = 0x01
    _DENSE_MODE_FLAG = 0x00
    _BIAS_CORRECTION_FLAG = 0x02
    _SPARSE_ENABLED_FLAG = 0x04
    _KNOWN_FLAGS = _SPARSE_MODE_FLAG | _BIAS_CORRECTION_FLAG | _SPARSE_ENABLED_FLAG

    # Paper-faithful thresholds and bias calibration data (precision 4 through 18).
    _LINEAR_COUNTING_THRESHOLD = LINEAR_COUNTING_THRESHOLD

    def __init__(
        self,
        precision: int = 14,
        filepath: str | Path | None = None,
        hash_function: SimpleHashT | None = None,
        *,
        bias_correction: bool = True,
        sparse_enabled: bool = False,
        sparse_threshold: int | None = None,
    ) -> None:
        # set before the base __init__, which uses them to allocate (`_new_registers`) or load
        # (`_parse_bytes`); loading replaces them with the settings stored in the file
        self._bias_correction = bool(bias_correction)
        self._sparse_enabled = bool(sparse_enabled)
        self._sparse_threshold: int | None = None
        # sorted, packed entries (one per index), and new packed entries not yet merged into them
        self._sparse = array(_UINT32_TYPECODE)
        self._sparse_buffer = array(_UINT32_TYPECODE)
        self._is_sparse = self._sparse_enabled
        super().__init__(precision=precision, filepath=filepath, hash_function=hash_function)
        if filepath is None:
            self._check_sparse_threshold(sparse_threshold)
            self._sparse_threshold = sparse_threshold

    def _new_registers(self) -> array:
        """array: no dense registers while sparse, otherwise a full set"""
        return array("B") if self._is_sparse else super()._new_registers()

    def _parse_bytes(self, data: ByteString | mmap) -> None:
        """Parse HyperLogLog++ bytes and populate the sketch state"""
        self._parse_hllpp_bytes(data)

    def _check_sparse_threshold(self, sparse_threshold: int | None) -> None:
        """Raise if `sparse_threshold` is not None or between 1 and the number of registers"""
        if sparse_threshold is not None and (
            isinstance(sparse_threshold, bool)
            or not isinstance(sparse_threshold, int)
            or not 1 <= sparse_threshold <= self.number_registers
        ):
            raise InitializationError(
                "HyperLogLogPlusPlus: sparse_threshold must be between 1 and the number of registers"
            )

    @classmethod
    def frombytes(cls, b: ByteString, hash_function: SimpleHashT | None = None) -> "HyperLogLogPlusPlus":
        """Create a HyperLogLogPlusPlus from bytes"""
        # sparse at the smallest precision, so nothing is allocated before the data is parsed
        hllpp = cls(precision=4, hash_function=hash_function, sparse_enabled=True)
        hllpp._parse_bytes(b)
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

    def add(self, key: KeyT) -> None:
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

    def _add_sparse(self, key: KeyT) -> None:
        """Add element to sparse representation"""
        self._add_alt_sparse(self._hash(key))

    def _add_alt_sparse(self, value: int) -> None:
        """Add pre-hashed element to sparse representation"""
        value &= UINT64_T_MAX
        self._sparse_update(value >> _SPARSE_WIDTH, self._rank(value & _SPARSE_SUFFIX_MASK, _SPARSE_WIDTH))
        self._elements_added += 1
        # entries plus buffer is an upper bound (the buffer may repeat an index); check exactly when reached
        threshold = self._sparse_promotion_threshold()
        if len(self._sparse) + len(self._sparse_buffer) >= threshold and self._sparse_count() >= threshold:
            self._promote_to_dense()

    def _sparse_update(self, idx: int, rank: int) -> None:
        """Keep the larger rank for a sparse index"""
        entries = self._sparse
        position = bisect_left(entries, idx << _RANK_BITS)
        if position < len(entries) and entries[position] >> _RANK_BITS == idx:
            if rank > entries[position] & _RANK_MASK:
                entries[position] = (idx << _RANK_BITS) | rank
            return
        # a new index: buffer it, and merge the buffer into the entries in batches, since merging
        # costs a pass over the entries; the buffer is 4-byte entries too, so it stays compact
        self._sparse_buffer.append((idx << _RANK_BITS) | rank)
        if len(self._sparse_buffer) >= max(64, len(entries) // 8):
            self._flush_sparse()

    def _flush_sparse(self) -> None:
        """Merge the buffered entries into the sorted entries, keeping the largest rank per index

        Buffered indexes are never in the sorted entries (an index found there is updated in place),
        so only the buffer is sorted; each buffered entry is then placed by binary search, and the
        sorted entries between them are copied in C."""
        if not self._sparse_buffer:
            return
        entries = self._sparse
        merged = array(_UINT32_TYPECODE)
        start = 0
        for entry in _largest_rank_per_index(self._sparse_buffer):
            position = bisect_left(entries, entry, start)
            merged.extend(entries[start:position])
            merged.append(entry)
            start = position
        merged.extend(entries[start:])
        self._sparse = merged
        self._sparse_buffer = array(_UINT32_TYPECODE)

    def _sparse_count(self) -> int:
        """int: the number of distinct sparse indexes"""
        self._flush_sparse()
        return len(self._sparse)

    def _sparse_entries(self) -> array:
        """array: the sorted, packed sparse entries"""
        self._flush_sparse()
        return self._sparse

    def _sparse_register_items(self):
        """Iterate over the sparse entries as (index, rank) at the sketch's precision

        An index at precision 25 starts with the index at precision p. If any of the bits after
        those are set, the rank is the position of the first one; otherwise it is the number of
        those bits plus the stored rank."""
        shift = SPARSE_PRECISION - self.precision
        low_mask = (1 << shift) - 1
        for entry in self._sparse_entries():
            sparse_idx = entry >> _RANK_BITS
            low = sparse_idx & low_mask
            rank = shift - low.bit_length() + 1 if low else shift + (entry & _RANK_MASK)
            yield sparse_idx >> shift, rank

    def _promote_to_dense(self) -> None:
        """Promote from sparse to dense representation"""
        registers = array("B", [0]) * self.number_registers
        for idx, rank in self._sparse_register_items():
            if rank > registers[idx]:
                registers[idx] = rank
        self._registers = registers
        self._sparse = array(_UINT32_TYPECODE)
        self._sparse_buffer = array(_UINT32_TYPECODE)
        self._is_sparse = False

    def merge(self, second: "HyperLogLogPlusPlus | HyperLogLog") -> None:
        """Merge another sketch into this one"""
        if not isinstance(second, (HyperLogLog, HyperLogLogPlusPlus)):
            raise NotSupportedError("Unable to merge with provided type")
        if self.precision != second.precision:
            raise NotSupportedError("Unable to merge HyperLogLogPlusPlus with different precision values")
        if self._hash_function("test", 0) != second._hash_function("test", 0):
            raise NotSupportedError("Hash functions do not match")

        if isinstance(second, HyperLogLogPlusPlus) and second.is_sparse:
            if self._is_sparse:
                self._merge_sparse_sparse(second)
            else:
                self._merge_dense_sparse(second)
        else:
            if self._is_sparse:
                self._promote_to_dense()
            super().merge(second)

    def _register_items(self):
        """Iterate over the (index, rank) of the registers that are set, in either representation"""
        if self._is_sparse:
            return self._sparse_register_items()
        return super()._register_items()

    def _merge_sparse_sparse(self, other: "HyperLogLogPlusPlus") -> None:
        """Merge two sparse sketches"""
        merged = _largest_rank_per_index(chain(self._sparse_entries(), other._sparse_entries()))
        self._sparse = array(_UINT32_TYPECODE, merged)
        self._elements_added += other.elements_added
        if self._sparse_count() >= self._sparse_promotion_threshold():
            self._promote_to_dense()

    def _merge_dense_sparse(self, other: "HyperLogLogPlusPlus") -> None:
        """Merge sparse sketch into dense sketch"""
        for idx, rank in other._sparse_register_items():
            if rank > self._registers[idx]:
                self._registers[idx] = rank
        self._elements_added += other.elements_added

    def estimate(self) -> float:
        """Return the estimated cardinality as a float"""
        if self._is_sparse:
            return self._estimate_sparse()

        return self._correct_estimate(self._raw_estimate(), self._zero_registers())

    def _correct_estimate(self, raw_estimate: float, zero_count: int) -> float:
        """Apply HLL++ corrections to a raw estimate and register zero count."""
        m = self.number_registers
        # Paper-faithful ordering: bias-correct the raw estimator in the small-range regime.
        if raw_estimate <= (5.0 * m):
            corrected = self._apply_bias_correction(raw_estimate) if self.bias_correction else raw_estimate

            # The paper's linear counting thresholds switch to the raw estimate early, where it is
            # still biased, so they only apply when bias correction fixes it. Without bias
            # correction, or a threshold (precisions 19 and 20), use the original HyperLogLog rule.
            if zero_count > 0:
                linear_count = m * math.log(m / zero_count)
                threshold = self._LINEAR_COUNTING_THRESHOLD.get(self.precision) if self.bias_correction else None
                if threshold is None:
                    if raw_estimate <= 2.5 * m:
                        return linear_count
                elif linear_count <= threshold:
                    return linear_count

            return corrected

        return self._apply_large_range_correction(raw_estimate)

    def _estimate_sparse(self) -> float:
        """Estimate cardinality with linear counting over the 2^25 sparse registers"""
        used = self._sparse_count()
        if used == 0:
            return 0.0
        registers = 1 << SPARSE_PRECISION
        return registers * math.log(registers / (registers - used))

    def _sparse_promotion_threshold(self) -> int:
        """int: the number of sparse entries at which to switch to dense registers"""
        if self._sparse_threshold is not None:
            return self._sparse_threshold
        # 4-byte entries use as much memory as the 1-byte registers at a quarter of them
        return max(1, self.number_registers // 4)

    def clear(self) -> None:
        """Clear the sketch"""
        if self._sparse_enabled:
            self._registers = array("B")
            self._elements_added = 0
        else:
            super().clear()
        self._sparse = array(_UINT32_TYPECODE)
        self._sparse_buffer = array(_UINT32_TYPECODE)
        self._is_sparse = self._sparse_enabled

    def export(self, file: Path | str | IOBase | mmap) -> None:
        """Export HyperLogLog++ to file"""
        if not isinstance(file, IOBase | mmap):
            file = resolve_path(file)
            with open(file, "wb") as filepointer:
                self.export(filepointer)  # type: ignore[arg-type]
        else:
            flags = self._SPARSE_MODE_FLAG if self._is_sparse else self._DENSE_MODE_FLAG
            if self._bias_correction:
                flags |= self._BIAS_CORRECTION_FLAG
            if self._sparse_enabled:
                flags |= self._SPARSE_ENABLED_FLAG
            threshold = 0 if self._sparse_threshold is None else self._sparse_threshold
            header = self._HLLPP_HEADER.pack(self._HLLPP_MAGIC, self._HLLPP_VERSION, flags, threshold)
            footer = self._HLLPP_FOOTER.pack(self.precision, self.elements_added)

            file.write(header)

            if self._is_sparse:
                entries = self._sparse_entries()
                file.write(self._SPARSE_COUNT.pack(len(entries)))
                if _BIG_ENDIAN:  # pragma: no cover
                    entries = array(_UINT32_TYPECODE, entries)
                    entries.byteswap()
                file.write(entries.tobytes())
            else:
                file.write(self._registers.tobytes())

            file.write(footer)

    def _apply_bias_correction(self, estimate: float) -> float:
        """Apply nearest-neighbor empirical bias correction from HLL++ paper."""
        # The original HLL++ dataset provides bias tables up to precision 18.
        if self.precision > 18:
            return estimate

        raw_points = RAW_ESTIMATE_DATA.get(self.precision, ())
        bias_points = BIAS_DATA.get(self.precision, ())
        if len(raw_points) == 0 or len(raw_points) != len(bias_points):
            return estimate

        # Paper-style nearest-neighbor bias estimation (k=6 in the paper). The raw estimates are
        # sorted apart from a few tiny inversions (precisions 5 and 6), so the nearest points are
        # within a few places of the insertion point; sort only that window by distance.
        k_neighbors = min(6, len(raw_points))
        position = bisect_left(raw_points, estimate)
        window = range(max(0, position - k_neighbors - 2), min(len(raw_points), position + k_neighbors + 2))
        nearest = sorted(window, key=lambda i: abs(raw_points[i] - estimate))[:k_neighbors]
        mean_bias = sum(bias_points[i] for i in nearest) / float(k_neighbors)
        corrected = estimate - mean_bias
        return max(0.0, corrected)

    def _parse_hllpp_bytes(self, data: ByteString | mmap) -> None:
        """Parse HyperLogLog++ bytes and populate state"""
        try:
            data = bytes(data)
            if len(data) < self._HLLPP_HEADER.size:
                raise InitializationError("HyperLogLogPlusPlus: invalid byte stream")
            magic, version, flags, threshold = self._HLLPP_HEADER.unpack_from(data)
            sparse_mode = bool(flags & self._SPARSE_MODE_FLAG)
            sparse_enabled = bool(flags & self._SPARSE_ENABLED_FLAG)
            if magic != self._HLLPP_MAGIC or flags & ~self._KNOWN_FLAGS or (sparse_mode and not sparse_enabled):
                raise InitializationError("HyperLogLogPlusPlus: invalid byte stream")
            if version != self._HLLPP_VERSION:
                raise InitializationError("HyperLogLogPlusPlus: invalid byte stream")

            payload = data[self._HLLPP_HEADER.size :]
            if sparse_mode:
                self._parse_hllpp_sparse_bytes(payload, self._HLLPP_FOOTER, self._SPARSE_COUNT)
            else:
                self._parse_hllpp_dense_bytes(payload, self._HLLPP_FOOTER)
            self._check_sparse_threshold(threshold or None)
            self._sparse_threshold = threshold or None
            self._bias_correction = bool(flags & self._BIAS_CORRECTION_FLAG)
            self._sparse_enabled = sparse_enabled
            if self._is_sparse and self._sparse_count() >= self._sparse_promotion_threshold():
                self._promote_to_dense()
        except (StructError, ValueError) as ex:
            raise InitializationError("HyperLogLogPlusPlus: invalid byte stream") from ex

    def _parse_hllpp_dense_bytes(self, data: ByteString, footer_struct: Struct) -> None:
        """Parse HyperLogLog++ dense format"""
        footer_size = footer_struct.size
        if len(data) < footer_size:
            raise InitializationError("HyperLogLogPlusPlus: invalid byte stream")
        precision, elements_added = footer_struct.unpack(bytes(data[-footer_size:]))
        self._set_precision(precision)
        self._load_registers(bytes(data[:-footer_size]), elements_added)
        self._sparse = array(_UINT32_TYPECODE)
        self._sparse_buffer = array(_UINT32_TYPECODE)
        self._is_sparse = False

    def _parse_hllpp_sparse_bytes(self, data: ByteString, footer_struct: Struct, count_struct: Struct) -> None:
        """Parse HyperLogLog++ sparse format"""
        footer_size = footer_struct.size
        if len(data) < footer_size + count_struct.size:
            raise InitializationError("HyperLogLogPlusPlus: invalid sparse byte stream")
        sparse_data = bytes(data[:-footer_size])

        precision, elements_added = footer_struct.unpack(bytes(data[-footer_size:]))
        self._set_precision(precision)
        entries = self._parse_sparse_entries(sparse_data, count_struct)
        if elements_added < len(entries) or (elements_added == 0) != (len(entries) == 0):
            raise InitializationError("HyperLogLogPlusPlus: invalid sparse element count")

        self._sparse = entries
        self._sparse_buffer = array(_UINT32_TYPECODE)
        self._registers = array("B")
        self._elements_added = elements_added
        self._is_sparse = True
        self._sparse_enabled = True

    def _parse_sparse_entries(self, sparse_data: bytes, count_struct: Struct) -> array:
        """Parse and validate the packed sparse entries: increasing indexes and valid ranks"""
        num_entries = count_struct.unpack_from(sparse_data)[0]
        if len(sparse_data) != count_struct.size + 4 * num_entries or num_entries > self.number_registers:
            raise InitializationError("HyperLogLogPlusPlus: invalid sparse byte stream")

        entries = array(_UINT32_TYPECODE)
        entries.frombytes(sparse_data[count_struct.size :])
        if _BIG_ENDIAN:  # pragma: no cover
            entries.byteswap()
        previous = -1
        for entry in entries:
            idx, rank = entry >> _RANK_BITS, entry & _RANK_MASK
            if idx >= 1 << SPARSE_PRECISION or not 1 <= rank <= _SPARSE_WIDTH + 1 or idx <= previous:
                raise InitializationError("HyperLogLogPlusPlus: invalid sparse register")
            previous = idx
        return entries
