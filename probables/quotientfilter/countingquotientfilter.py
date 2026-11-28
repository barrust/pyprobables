"""Counting Quotient Filter, python implementation
License: MIT
Author: Tyler Barrus (barrust@gmail.com)

The counter encoding follows the counting quotient filter of Pandey, Bender, Johnson, and Patro,
"A General-Purpose Counting Filter: Making Every Bit Count" (SIGMOD 2017), and its reference
implementation, https://github.com/saltsystemslab/cqf
"""

import copy
from array import array
from collections.abc import Iterator

from probables.exceptions import QuotientFilterError
from probables.hashes import KeyT, SimpleHashT, fnv_1a_32
from probables.quotientfilter.quotientfilter import _check_quotient, _remainder_storage
from probables.utilities import Bitarray

_HASH_MASK = 0xFFFFFFFF  # the quotient and remainder together use 32 bits of the hash
_MAX_QUOTIENT = 30  # the counter encoding needs at least 2 remainder bits
_STATE_ATTRS = (
    "_q",
    "_r",
    "_size",
    "_elements_added",
    "_unique_elements",
    "_slots_used",
    "_auto_resize",
    "_int_type_code",
    "_bits_per_elm",
    "_is_occupied",
    "_is_continuation",
    "_is_shifted",
    "_filter",
)


def _encode_counter(rem: int, count: int, r_bits: int) -> list[int]:
    """Encode an entry: its remainder followed by its count, in remainder-sized slots

    For a remainder x: 1 is `x`; 2 is `x x`; 3 is `x 0 x` (`0 0 0` for x = 0); more than 3 is
    `x [0] digits x` for x > 0, the digits of count - 3 in base 2^r - 2 skipping 0 and x, with a 0
    first when the first digit is larger than x; and `0 digits 0 0` for x = 0, the digits of count - 4
    in base 2^r - 1 skipping 0"""
    if count < 1:
        raise ValueError(f"a count must be at least 1; {count} was provided")
    if count == 1:
        return [rem]
    if count == 2:
        return [rem, rem]
    if count == 3:
        return [0, 0, 0] if rem == 0 else [rem, 0, rem]

    digits = []
    if rem == 0:
        base = (1 << r_bits) - 1
        val = count - 4
        while True:
            digits.append(val % base + 1)
            val //= base
            if not val:
                break
        return [0, *reversed(digits), 0, 0]

    base = (1 << r_bits) - 2
    val = count - 3
    while True:
        digit = val % base + 1
        if digit >= rem:
            digit += 1
        digits.append(digit)
        val //= base
        if not val:
            break
    # the slot after the remainder must be smaller than it, so a decoder knows a counter follows
    marker = [0] if digits[-1] > rem else []
    return [rem, *marker, *reversed(digits), rem]


def _decode_short_counter(slots: list[int], idx: int) -> tuple[int, int, int] | None:
    """Decode an entry with a count of 1, 2, or 3; None if its count is larger"""
    rem = slots[idx]
    last = len(slots) - 1
    if idx == last:
        return rem, 1, idx + 1
    digit = slots[idx + 1]
    if idx + 1 == last or 0 < rem <= digit:  # the run ends, or the next slot is a repeat or a larger remainder
        return (rem, 2, idx + 2) if digit == rem else (rem, 1, idx + 1)
    if digit == 0 and slots[idx + 2] == rem:  # x 0 x, or 0 0 0
        return rem, 3, idx + 3
    if digit == 0 == rem:  # 0 0, then a larger remainder
        return 0, 2, idx + 2
    return None


def _decode_counter(slots: list[int], idx: int, r_bits: int) -> tuple[int, int, int]:
    """Decode the entry starting at slots[idx] of a run; returns (remainder, count, index of the next entry)"""
    short = _decode_short_counter(slots, idx)
    if short is not None:
        return short

    rem = slots[idx]
    last = len(slots) - 1
    base = (1 << r_bits) - (2 if rem else 1)
    cnt = 0
    end = idx + 1
    digit = slots[end]
    while digit != rem and end != last:
        if digit > rem:
            digit -= 1
        if digit and rem:
            digit -= 1
        cnt = cnt * base + digit
        end += 1
        digit = slots[end]

    if rem:
        return rem, cnt + 3, end + 1
    if end == last or slots[end + 1] != 0:
        return 0, 1, idx + 1  # a single 0 followed by larger remainders
    return 0, cnt + 4, end + 2


def _decode_run(slots: list[int], r_bits: int) -> list[list[int]]:
    """Decode a run into its [remainder, count] entries, in remainder order"""
    entries = []
    idx = 0
    while idx < len(slots):
        rem, count, idx = _decode_counter(slots, idx, r_bits)
        entries.append([rem, count])
    return entries


def _encode_run(entries: list[list[int]], r_bits: int) -> list[int]:
    """Encode [remainder, count] entries, in remainder order, into the slots of a run"""
    slots: list[int] = []
    for rem, count in entries:
        slots.extend(_encode_counter(rem, count, r_bits))
    return slots


class CountingQuotientFilter:
    """Counting Quotient Filter: a quotient filter that counts how many times each element was added

    Args:
        quotient (int): The size of the quotient to use, from 3 to 30
        auto_expand (bool): Automatically expand or not
        hash_function (function): Hashing strategy function to use `hf(key, number)`;
            only the lower 32 bits of the hash are used
    Returns:
        CountingQuotientFilter: The initialized filter
    Raises:
        QuotientFilterError: Raised when unable to initialize
    Note:
        The size of the CountingQuotientFilter will be 2**q
    Note:
        Each count is stored in the remainder slots after its element, so a large count takes a few slots,
        not one per copy (Pandey et al., SIGMOD 2017). Like `QuotientFilter`, it stores 32 bits of each
        hash, so two elements with the same 32-bit hash share a count"""

    __slots__ = (
        "_q",
        "_r",
        "_size",
        "_elements_added",
        "_unique_elements",
        "_slots_used",
        "_hash_func",
        "_int_type_code",
        "_bits_per_elm",
        "_is_occupied",
        "_is_continuation",
        "_is_shifted",
        "_filter",
        "_max_load_factor",
        "_auto_resize",
    )

    def __init__(self, quotient: int = 20, auto_expand: bool = True, hash_function: SimpleHashT | None = None):
        quotient = _check_quotient(quotient, _MAX_QUOTIENT)
        self._max_load_factor: float = 0.85
        self.__set_params(quotient, auto_expand, hash_function)

    def __set_params(self, quotient: int, auto_expand: bool, hash_function: SimpleHashT | None):
        self._q: int = quotient
        self._r: int = 32 - quotient
        self._size: int = 1 << self._q
        self._elements_added: int = 0
        self._unique_elements: int = 0
        self._slots_used: int = 0
        self._auto_resize: bool = auto_expand
        self._hash_func: SimpleHashT = fnv_1a_32 if hash_function is None else hash_function  # type: ignore

        self._bits_per_elm, self._int_type_code = _remainder_storage(self._r)

        self._is_occupied = Bitarray(self._size)
        self._is_continuation = Bitarray(self._size)
        self._is_shifted = Bitarray(self._size)
        self._filter = array(self._int_type_code, [0]) * self._size

    def __contains__(self, key: KeyT) -> bool:
        """setup the `in` keyword"""
        return self.check(key) > 0

    def __len__(self) -> int:
        """The number of elements in the filter, counting each time an element was added"""
        return self._elements_added

    @property
    def quotient(self) -> int:
        """int: The size of the quotient, in bits"""
        return self._q

    @property
    def remainder(self) -> int:
        """int: The size of the remainder, in bits"""
        return self._r

    @property
    def size(self) -> int:
        """int: The number of slots in the filter (2**quotient)"""
        return self._size

    @property
    def elements_added(self) -> int:
        """int: The number of elements in the filter, counting each time an element was added"""
        return self._elements_added

    @property
    def unique_elements(self) -> int:
        """int: The number of distinct elements (hashes) in the filter"""
        return self._unique_elements

    @property
    def slots_used(self) -> int:
        """int: The number of slots holding remainders or counts"""
        return self._slots_used

    @property
    def bits_per_elm(self) -> int:
        """int: The number of bits used per slot"""
        return self._bits_per_elm

    @property
    def load_factor(self) -> float:
        """float: The share of slots in use"""
        return self._slots_used / self._size

    @property
    def auto_expand(self) -> bool:
        """bool: Will the counting quotient filter automatically expand"""
        return self._auto_resize

    @auto_expand.setter
    def auto_expand(self, val: bool):
        """change the auto expand property"""
        self._auto_resize = bool(val)

    @property
    def max_load_factor(self) -> float:
        """float: The maximum allowed load factor after which auto expanding should occur"""
        return self._max_load_factor

    @max_load_factor.setter
    def max_load_factor(self, val: float):
        """set the maximum load factor"""
        val = float(val)
        if not 0 < val <= 1:
            raise QuotientFilterError(
                f"Invalid max load factor; it must be greater than 0 and at most 1; {val} was provided"
            )
        self._max_load_factor = val

    def add(self, key: KeyT, num_els: int = 1) -> int:
        """Add the key to the counting quotient filter

        Args:
            key (str|bytes): The element to add
            num_els (int): The number of times to add it
        Returns:
            int: The count of the element after adding it
        Raises:
            QuotientFilterError: Raised when no locations are available in which to insert"""
        return self.add_alt(self._hash_func(key, 0), num_els)

    def add_alt(self, _hash: int, num_els: int = 1) -> int:
        """Add the pre-hashed value to the counting quotient filter

        Args:
            _hash (int): The hash of the element to add
            num_els (int): The number of times to add it
        Returns:
            int: The count of the element after adding it
        Raises:
            QuotientFilterError: Raised when no locations are available in which to insert"""
        self.__check_num_els(num_els)
        return self._update(_hash & _HASH_MASK, num_els)

    def check(self, key: KeyT) -> int:
        """Check how many times the key was likely added

        Args:
            key (str|bytes): The element to check
        Returns:
            int: The count of the element; 0 if it was definitely not added"""
        return self.check_alt(self._hash_func(key, 0))

    def check_alt(self, _hash: int) -> int:
        """Check how many times the pre-hashed value was likely added

        Args:
            _hash (int): The hash of the element to check
        Returns:
            int: The count of the element; 0 if it was definitely not added"""
        _hash &= _HASH_MASK
        quot, rem = _hash >> self._r, _hash & ((1 << self._r) - 1)
        if self._is_occupied[quot] == 0:
            return 0
        slots = self._read_run(self._run_start(quot))
        idx = 0
        while idx < len(slots):
            entry_rem, count, idx = _decode_counter(slots, idx, self._r)
            if entry_rem == rem:
                return count
            if entry_rem > rem:
                break
        return 0

    def remove(self, key: KeyT, num_els: int = 1) -> int:
        """Remove the key from the counting quotient filter

        Args:
            key (str|bytes): The element to remove
            num_els (int): The number of times to remove it; removing more than its count removes it
        Returns:
            int: The count of the element after removing it"""
        return self.remove_alt(self._hash_func(key, 0), num_els)

    def remove_alt(self, _hash: int, num_els: int = 1) -> int:
        """Remove the pre-hashed value from the counting quotient filter

        Args:
            _hash (int): The hash of the element to remove
            num_els (int): The number of times to remove it; removing more than its count removes it
        Returns:
            int: The count of the element after removing it"""
        self.__check_num_els(num_els)
        _hash &= _HASH_MASK
        if self._is_occupied[_hash >> self._r] == 0:
            return 0
        return self._update(_hash, -num_els)

    def hashes(self) -> Iterator[tuple[int, int]]:
        """A generator over the hashes in the filter and their counts

        Yields:
            tuple(int, int): The next hash stored in the filter and its count"""
        start = next((i for i in range(self._size) if self._is_empty(i)), None)
        if start is None:  # pragma: no cover - an empty slot is always kept
            return
        pos = start + 1
        while pos < start + self._size:
            if self._is_empty(pos % self._size):
                pos += 1
                continue
            runs, pos = self._decode_block(pos)
            for quot, slots in runs:
                for rem, count in _decode_run(slots, self._r):
                    yield (quot << self._r) | rem, count

    def get_hashes(self) -> list[tuple[int, int]]:
        """Get the hashes in the filter and their counts, sorted by hash

        Returns:
            list(tuple(int, int)): The (hash, count) pairs"""
        return sorted(self.hashes())

    def resize(self, quotient: int | None = None) -> None:
        """Resize the counting quotient filter to use the new quotient size

        Args:
            quotient (int): The new quotient to use
        Note:
            If `None` is provided, the filter will double in size (quotient + 1)
        Raises:
            QuotientFilterError: When the elements already added, with their counts, will not fit in the new
                quotient, or when expanding a filter that already has a quotient of 30; the filter is unchanged
        Note:
            The filter has exactly the new quotient afterwards, even if that is over its `max_load_factor`;
            with `auto_expand`, the next add that needs more slots expands it"""
        if quotient is None:
            if self._q == _MAX_QUOTIENT:
                raise QuotientFilterError(
                    f"Unable to expand; the counting quotient filter is at its largest size "
                    f"(quotient of {_MAX_QUOTIENT})"
                )
            quotient = self._q + 1
        quotient = _check_quotient(quotient, _MAX_QUOTIENT)

        entries = list(self.hashes())
        needed = self._slots_needed(entries, quotient)
        if needed > (1 << quotient) - 1:
            raise QuotientFilterError(
                f"Unable to resize; the elements need {needed} slots and a quotient of {quotient} holds "
                f"{(1 << quotient) - 1}"
            )

        state = self.__save_state()
        auto_expand = self._auto_resize
        try:
            self.__set_params(quotient, False, self._hash_func)  # re-adding fits, so it never expands
            for _hash, count in entries:
                self._update(_hash, count)
        except BaseException:
            self.__restore_state(state)
            raise
        self._auto_resize = auto_expand

    def merge(self, second: "CountingQuotientFilter") -> None:
        """Merge the `second` counting quotient filter into this one, adding the counts

        Args:
            second (CountingQuotientFilter): The filter to merge
        Raises:
            TypeError: When `second` is not a CountingQuotientFilter
            QuotientFilterError: When the hash functions do not match, or the merged elements do not fit and
                the filter does not expand; the filter is unchanged
        Note:
            The hashing function between the two filters should match"""
        if not isinstance(second, CountingQuotientFilter):
            raise TypeError("The parameter second must be of type CountingQuotientFilter")
        if self._hash_func("test", 0) != second._hash_func("test", 0):
            raise QuotientFilterError("Hash functions do not match")
        entries = list(second.hashes())
        state = self.__save_state(copy_arrays=True)
        try:
            for _hash, count in entries:
                self._update(_hash, count)
        except BaseException:
            self.__restore_state(state)
            raise

    def clear(self) -> None:
        """Remove every element from the filter, keeping its current size and settings"""
        self.__set_params(self._q, self._auto_resize, self._hash_func)

    def validate_metadata(self) -> bool:
        """Check that the metadata bits, the runs, and the element counts are all consistent

        Returns:
            bool: True if the filter is valid; False otherwise"""
        try:
            return self._check_layout()
        except (ValueError, IndexError):
            return False

    def _check_layout(self) -> bool:
        """Walk every block and check its bits, the place and encoding of each run, and the totals"""
        empty = next((i for i in range(self._size) if self._is_empty(i)), None)
        if empty is None:
            return False  # an empty slot is always kept
        totals = [0, 0, 0]  # elements added, unique elements, slots used
        pos = empty + 1
        while pos < empty + self._size:
            if self._is_empty(pos % self._size):
                pos += 1
                continue
            pos = self._check_block(pos, totals)
            if pos < 0:
                return False
        return tuple(totals) == (self._elements_added, self._unique_elements, self._slots_used)

    def _check_block(self, pos: int, totals: list[int]) -> int:
        """Check the block starting at `pos` (unwrapped), adding its counts to `totals`

        Returns:
            The unwrapped position of the empty slot after the block, or -1 if the block is invalid"""
        size = self._size
        block_start = pos
        homes: list[int] = []
        run_starts: list[int] = []
        while not self._is_empty(pos % size):
            idx = pos % size
            if self._is_continuation[idx] == 1 and self._is_shifted[idx] == 0:  # 0-1-0 and 1-1-0
                return -1
            if self._is_occupied[idx] == 1:
                homes.append(pos)
            if self._is_continuation[idx] == 0:
                run_starts.append(pos)
            pos += 1
        if len(homes) != len(run_starts) or self._is_continuation[block_start % size] == 1:
            return -1
        run_ends = [*run_starts[1:], pos]
        for home, run_start, run_end in zip(homes, run_starts, run_ends, strict=True):
            # runs are packed in quotient order, so each starts at its home or after it, shifted if not home
            if run_start < home or self._is_shifted[run_start % size] != (run_start != home):
                return -1
            slots = [self._filter[j % size] for j in range(run_start, run_end)]
            entries = _decode_run(slots, self._r)
            rems = [rem for rem, _ in entries]
            if rems != sorted(set(rems)) or _encode_run(entries, self._r) != slots:
                return -1
            totals[0] += sum(count for _, count in entries)
            totals[1] += len(entries)
            totals[2] += len(slots)
        return pos

    @staticmethod
    def __check_num_els(num_els: int) -> None:
        if not isinstance(num_els, int) or isinstance(num_els, bool) or num_els < 1:
            raise QuotientFilterError(f"num_els must be a positive integer; {num_els!r} was provided")

    def _slots_needed(self, entries: list[tuple[int, int]], quotient: int) -> int:
        """The number of slots the (hash, count) entries take in a filter with `quotient`"""
        r_bits = 32 - quotient
        runs: dict[int, list[list[int]]] = {}
        for _hash, count in entries:
            runs.setdefault(_hash >> r_bits, []).append([_hash & ((1 << r_bits) - 1), count])
        return sum(len(_encode_run(sorted(run), r_bits)) for run in runs.values())

    def __save_state(self, copy_arrays: bool = False) -> dict:
        """The filter's state, to restore if an operation fails part-way; copy the arrays if they will be changed
        in place (resize replaces them instead)"""
        state = {name: getattr(self, name) for name in _STATE_ATTRS}
        if copy_arrays:
            for name in ("_is_occupied", "_is_continuation", "_is_shifted", "_filter"):
                state[name] = copy.deepcopy(state[name])
        return state

    def __restore_state(self, state: dict) -> None:
        for name, value in state.items():
            setattr(self, name, value)

    def _is_empty(self, idx: int) -> bool:
        return (self._is_occupied[idx] + self._is_continuation[idx] + self._is_shifted[idx]) == 0

    def _run_start(self, quot: int) -> int:
        """The slot where the run of `quot` starts; `quot` must be occupied"""
        mask = self._size - 1
        j = quot
        runs = 0
        while True:  # back to the start of the cluster, counting the runs that start in it
            if self._is_occupied[j] == 1:
                runs += 1
            if self._is_shifted[j] == 0:
                break
            j = (j - 1) & mask
        while True:  # forward to the start of the run of `quot`
            if self._is_continuation[j] == 0:
                if runs == 1:
                    return j
                runs -= 1
            j = (j + 1) & mask

    def _read_run(self, start: int) -> list[int]:
        """The slots of the run that starts at `start`"""
        mask = self._size - 1
        slots = [self._filter[start]]
        idx = (start + 1) & mask
        while self._is_continuation[idx] == 1:
            slots.append(self._filter[idx])
            idx = (idx + 1) & mask
        return slots

    def _decode_block(self, pos: int) -> tuple[list[tuple[int, list[int]]], int]:
        """Decode the non-empty slots from `pos` (unwrapped; the start of a block) up to the next empty slot

        Returns:
            The (quotient, slots) of each run in order, and the unwrapped position of the empty slot"""
        quotients: list[int] = []
        runs: list[list[int]] = []
        idx = pos % self._size
        while not self._is_empty(idx):
            if self._is_occupied[idx] == 1:
                quotients.append(idx)
            if self._is_continuation[idx] == 0:
                runs.append([])
            runs[-1].append(self._filter[idx])
            pos += 1
            idx = pos % self._size
        return list(zip(quotients, runs, strict=True)), pos

    def _unwrap(self, idx: int, start: int) -> int:
        """The position of slot `idx` counting forward from `start`, so it is not smaller than `start`"""
        return start + (idx - start) % self._size

    def _block_around(self, quot: int) -> tuple[int, list[tuple[int, list[int]]], int]:
        """The block of non-empty slots holding the run of `quot` (or just `quot` when its slot is empty)

        Returns:
            The block start, its (quotient, slots) runs, and the unwrapped position of the empty slot after it"""
        if self._is_empty(quot):
            return quot, [], quot
        start = quot
        while not self._is_empty((start - 1) % self._size):
            start = (start - 1) % self._size
        runs, end = self._decode_block(start)
        return start, runs, end

    def _change_count(self, old_slots: list[int], rem: int, change: int) -> tuple[int, int, list[int]]:
        """Apply `change` to the count of `rem` in a run; returns the old count, the new count, and the new slots"""
        entries = _decode_run(old_slots, self._r)
        entry_idx = next((i for i, (r, _) in enumerate(entries) if r >= rem), len(entries))
        found = entry_idx < len(entries) and entries[entry_idx][0] == rem
        old_count = entries[entry_idx][1] if found else 0
        new_count = max(old_count + change, 0)
        if new_count == old_count:
            return old_count, new_count, old_slots
        if not found:
            entries.insert(entry_idx, [rem, new_count])
        elif new_count == 0:
            del entries[entry_idx]
        else:
            entries[entry_idx][1] = new_count
        return old_count, new_count, _encode_run(entries, self._r)

    def _needs_resize(self, growth: int) -> bool:
        """Whether to expand before using `growth` more slots; raises if it can't fit and won't expand"""
        needed = self._slots_used + growth
        if growth <= 0 or (needed <= self._size - 1 and needed / self._size <= self._max_load_factor):
            return False
        if self._auto_resize:
            return True
        if needed > self._size - 1:
            raise QuotientFilterError("Unable to insert the element due to insufficient space")
        return False

    def _absorb_blocks(self, runs: list[tuple[int, list[int]]], start: int, end: int) -> tuple[int, int]:
        """Decode the blocks after `end` that the laid-out `runs` would reach, adding their runs

        Returns:
            The unwrapped end of the decoded blocks and the end of the layout"""
        while True:
            layout_end = start
            for quot, slots in runs:
                layout_end = max(layout_end, self._unwrap(quot, start)) + len(slots)
            nxt = end
            while nxt < layout_end and self._is_empty(nxt % self._size):
                nxt += 1
            if nxt >= layout_end:
                return end, layout_end
            more, end = self._decode_block(nxt)
            runs.extend(more)

    def _write_runs(self, runs: list[tuple[int, list[int]]], start: int, clear_end: int) -> None:
        """Clear the slots from `start` to `clear_end` and write the runs in order from `start`"""
        size = self._size
        for pos in range(start, clear_end):
            idx = pos % size
            self._filter[idx] = 0
            self._is_occupied[idx] = 0
            self._is_continuation[idx] = 0
            self._is_shifted[idx] = 0

        pos = start
        for quot, slots in runs:
            home = self._unwrap(quot, start)
            run_start = max(pos, home)
            self._is_occupied[quot] = 1
            for i, val in enumerate(slots):
                idx = (run_start + i) % size
                self._filter[idx] = val
                self._is_continuation[idx] = 1 if i else 0
                self._is_shifted[idx] = 1 if run_start + i != home else 0
            pos = run_start + len(slots)

    def _update_in_place(
        self, quot: int, rem: int, change: int
    ) -> tuple[int | None, tuple[int, int, list[int]] | None]:
        """Apply a change that keeps the run's length (or changes nothing) in place

        Returns:
            The new count if done, else None; and, when the run of `quot` exists but its length changes, its
            (old count, new count, new slots) so the caller doesn't decode it again"""
        if self._is_occupied[quot] == 0:
            return None, None
        run_start = self._run_start(quot)
        old_slots = self._read_run(run_start)
        old_count, new_count, new_slots = self._change_count(old_slots, rem, change)
        if new_count == old_count:
            return old_count, None
        if len(new_slots) != len(old_slots):
            return None, (old_count, new_count, new_slots)
        for i, val in enumerate(new_slots):
            self._filter[(run_start + i) % self._size] = val
        self._elements_added += new_count - old_count
        self._unique_elements += (new_count > 0) - (old_count > 0)
        return new_count, None

    def _update(self, _hash: int, change: int) -> int:
        """Add `change` (negative to remove) to the count of `_hash`; returns the new count"""
        quot, rem = _hash >> self._r, _hash & ((1 << self._r) - 1)
        done, changed = self._update_in_place(quot, rem, change)
        if done is not None:
            return done

        start, runs, end = self._block_around(quot)
        run_idx = next((i for i, (q, _) in enumerate(runs) if q == quot), None)
        # the run was already changed by _update_in_place; a quotient with no run gets a new one
        old_count, new_count, new_slots = changed if changed is not None else self._change_count([], rem, change)

        growth = len(new_slots) - (len(runs[run_idx][1]) if run_idx is not None else 0)
        if self._needs_resize(growth):
            self.resize()
            return self._update(_hash, change)

        if run_idx is None:  # a new run goes before the first run whose quotient comes after it
            run_idx = next(
                (i for i, (q, _) in enumerate(runs) if self._unwrap(q, start) > self._unwrap(quot, start)), len(runs)
            )
            runs.insert(run_idx, (quot, new_slots))
        elif new_slots:
            runs[run_idx] = (quot, new_slots)
        else:
            del runs[run_idx]

        self._write_runs(runs, start, max(self._absorb_blocks(runs, start, end)))

        self._slots_used += growth
        self._elements_added += new_count - old_count
        self._unique_elements += (new_count > 0) - (old_count > 0)
        return new_count
