# https://mecha-mind.medium.com/membership-queries-with-big-data-9e5046d3270f

from array import array

from probables.hashes import fnv_1a_32


def get_hash(x, m):
    return fnv_1a_32(x, 0) & ((1 << m) - 1)


class bitarray:
    # NOTE: NOT SPACE EFFICIENT FOR NOW
    def __init__(self, size: int):
        self.bitarray = array("B", [0]) * size
        self.size = size

    def __getitem__(self, idx: int):
        return self.bitarray[idx]

    def __setitem__(self, idx: int, val: int):
        if val < 0 or val > 1:
            raise ValueError("Invalid bit setting; must be 0 or 1")
        self.bitarray[idx] = val

    def set_bit(self, idx: int):
        self.bitarray[idx] = 1

    def clear_bit(self, idx: int):
        self.bitarray[idx] = 0


class QuotientFilter:
    def __init__(self):  # needs to be parameterized
        self.q = 24
        self.r = 8
        self.m = 1 << self.q  # the size of the array

        self.is_occupied_arr = bitarray(self.m)
        self.is_continuation_arr = bitarray(self.m)
        self.is_shifted_arr = bitarray(self.m)
        self._filter = array("I", [0]) * self.m

    def shift_insert(self, k, v, start, j, flag):
        if self.is_occupied_arr[j] == 0 and self.is_continuation_arr[j] == 0 and self.is_shifted_arr[j] == 0:
            self._filter[j] = v
            self.is_occupied_arr[k] = 1
            self.is_continuation_arr[j] = 1 if j != start else 0
            self.is_shifted_arr[j] = 1 if j != k else 0

        else:
            i = (j + 1) & (self.m - 1)

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

                i = (i + 1) & (self.m - 1)

            self._filter[j] = v
            self.is_occupied_arr[k] = 1
            self.is_continuation_arr[j] = 1 if j != start else 0
            self.is_shifted_arr[j] = 1 if j != k else 0

            if flag == 1:
                self.is_continuation_arr[(j + 1) & (self.m - 1)] = 1

    def get_start_index(self, k):
        j = k
        cnts = 0

        while True:
            if j == k or self.is_occupied_arr[j] == 1:
                cnts += 1

            if self.is_shifted_arr[j] == 1:
                j = (j - 1) & (self.m - 1)
            else:
                break

        while True:
            if self.is_continuation_arr[j] == 0:
                if cnts == 1:
                    break
                cnts -= 1

            j = (j + 1) & (self.m - 1)

        return j

    def add(self, x):
        if self.contains(x) is False:
            h = get_hash(x, self.q + self.r)
            k = h >> self.r
            v = h & ((1 << self.r) - 1)

            if self.is_occupied_arr[k] == 0 and self.is_continuation_arr[k] == 0 and self.is_shifted_arr[k] == 0:
                self._filter[k] = v
                self.is_occupied_arr[k] = 1

            else:
                j = self.get_start_index(k)

                if self.is_occupied_arr[k] == 0:
                    self.shift_insert(k, v, j, j, 0)

                else:
                    u = j
                    starts = 0
                    f = self.is_occupied_arr[j] + self.is_continuation_arr[j] + self.is_shifted_arr[j]

                    while starts == 0 and f != 0 and v > self._filter[j]:
                        j = (j + 1) & (self.m - 1)

                        if self.is_continuation_arr[j] == 0:
                            starts += 1

                        f = self.is_occupied_arr[j] + self.is_continuation_arr[j] + self.is_shifted_arr[j]

                    if starts == 1:
                        self.shift_insert(k, v, u, j, 0)
                    else:
                        self.shift_insert(k, v, u, j, 1)

    def contains(self, x):
        h = get_hash(x, self.q + self.r)
        k = h >> self.r
        v = h & ((1 << self.r) - 1)

        if self.is_occupied_arr[k] == 0:
            return False

        else:
            j = self.get_start_index(k)

            starts = 0
            f = self.is_occupied_arr[j] + self.is_continuation_arr[j] + self.is_shifted_arr[j]

            while f != 0:
                if self.is_continuation_arr[j] == 0:
                    starts += 1

                if starts == 2 or self._filter[j] > v:
                    break

                if self._filter[j] == v:
                    return True

                j = (j + 1) & (self.m - 1)
                f = self.is_occupied_arr[j] + self.is_continuation_arr[j] + self.is_shifted_arr[j]

            return False
