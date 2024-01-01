# https://mecha-mind.medium.com/membership-queries-with-big-data-9e5046d3270f

from array import array

from probables.hashes import KeyT, fnv_1a_32
from probables.utilities import Bitarray


def get_hash(x: KeyT, m: int):
    return fnv_1a_32(x, 0) & ((1 << m) - 1)


class QuotientFilter:
    def __init__(self):  # needs to be parameterized
        self._q = 24
        self._r = 8
        self._size = 1 << self._q  # same as 2**q

        self.is_occupied_arr = Bitarray(self._size)
        self.is_continuation_arr = Bitarray(self._size)
        self.is_shifted_arr = Bitarray(self._size)
        self._filter = array("I", [0]) * self._size

    def shift_insert(self, k, v, start, j, flag):
        if self.is_occupied_arr[j] == 0 and self.is_continuation_arr[j] == 0 and self.is_shifted_arr[j] == 0:
            self._filter[j] = v
            self.is_occupied_arr[k] = 1
            self.is_continuation_arr[j] = 1 if j != start else 0
            self.is_shifted_arr[j] = 1 if j != k else 0

        else:
            # print("using shift insert")
            i = (j + 1) & (self._size - 1)

            while True:
                f = self.is_occupied_arr[i] + self.is_continuation_arr[i] + self.is_shifted_arr[i]

                temp = self.is_continuation_arr[i]
                self.is_continuation_arr[i] = self.is_continuation_arr[j]
                self.is_continuation_arr[j] = temp

                self.is_shifted_arr[i] = 1

                temp = self._filter[i]
                self._filter[i] = self._filter[j]
                self._filter[j] = temp

                if f == 0:
                    break

                i = (i + 1) & (self._size - 1)

            self._filter[j] = v
            self.is_occupied_arr[k] = 1
            self.is_continuation_arr[j] = 1 if j != start else 0
            self.is_shifted_arr[j] = 1 if j != k else 0

            if flag == 1:
                self.is_continuation_arr[(j + 1) & (self._size - 1)] = 1

    def get_start_index(self, k):
        j = k
        cnts = 0

        while True:
            if j == k or self.is_occupied_arr[j] == 1:
                cnts += 1

            if self.is_shifted_arr[j] == 1:
                j = (j - 1) & (self._size - 1)
            else:
                break

        while True:
            if self.is_continuation_arr[j] == 0:
                if cnts == 1:
                    break
                cnts -= 1

            j = (j + 1) & (self._size - 1)

        return j

    def add(self, key: KeyT):
        if self.contains(key) is False:
            _hash = get_hash(key, self._q + self._r)
            key_quotient = _hash >> self._r
            key_remainder = _hash & ((1 << self._r) - 1)

            if (
                self.is_occupied_arr[key_quotient] == 0
                and self.is_continuation_arr[key_quotient] == 0
                and self.is_shifted_arr[key_quotient] == 0
            ):
                self._filter[key_quotient] = key_remainder
                self.is_occupied_arr[key_quotient] = 1

            else:
                j = self.get_start_index(key_quotient)

                if self.is_occupied_arr[key_quotient] == 0:
                    self.shift_insert(key_quotient, key_remainder, j, j, 0)

                else:
                    u = j
                    starts = 0
                    f = self.is_occupied_arr[j] + self.is_continuation_arr[j] + self.is_shifted_arr[j]

                    while starts == 0 and f != 0 and key_remainder > self._filter[j]:
                        j = (j + 1) & (self._size - 1)

                        if self.is_continuation_arr[j] == 0:
                            starts += 1

                        f = self.is_occupied_arr[j] + self.is_continuation_arr[j] + self.is_shifted_arr[j]

                    if starts == 1:
                        self.shift_insert(key_quotient, key_remainder, u, j, 0)
                    else:
                        self.shift_insert(key_quotient, key_remainder, u, j, 1)

    def contains(self, key: KeyT):
        _hash = get_hash(key, self._q + self._r)
        key_quotient = _hash >> self._r
        key_remainder = _hash & ((1 << self._r) - 1)

        if self.is_occupied_arr[key_quotient] == 0:
            return False

        else:
            j = self.get_start_index(key_quotient)

            starts = 0
            f = self.is_occupied_arr[j] + self.is_continuation_arr[j] + self.is_shifted_arr[j]

            while f != 0:
                if self.is_continuation_arr[j] == 0:
                    starts += 1

                if starts == 2 or self._filter[j] > key_remainder:
                    break

                if self._filter[j] == key_remainder:
                    return True

                j = (j + 1) & (self._size - 1)
                f = self.is_occupied_arr[j] + self.is_continuation_arr[j] + self.is_shifted_arr[j]

            return False
