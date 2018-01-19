''' Count-Min Sketch python implementation
    License: MIT
    Author: Tyler Barrus (barrust@gmail.com)
    URL: https://github.com/barrust/count-min-sketch
'''
from __future__ import (unicode_literals, absolute_import, print_function,
                        division)
import os
import math
from numbers import Number
from struct import (pack, unpack, calcsize)

from .. exceptions import (InitializationError, NotSupportedError)
from .. hashes import (default_fnv_1a)
from .. utilities import (is_valid_file)
from .. constants import (INT32_T_MIN, INT32_T_MAX, INT64_T_MIN, INT64_T_MAX)


class CountMinSketch(object):
    ''' Simple Count-Min Sketch implementation for use in python;
        It can read and write the same format as the c version
        (https://github.com/barrust/count-min-sketch)

        Args:
            width (int): The width of the count-min sketch
            depth (int): The depth of the count-min sketch
            confidence (float): The level of confidence desired
            error_rate (float): The desired error rate
            filepath (string): Path to file to load
            hash_function (function): Hashing strategy function to use \
            `hf(key, number)`
        Returns:
            CountMinSketch: A Count-Min Sketch object

        Note:
            Initialization order of operations:
                1) From file
                2) Width and depth
                3) Confidence and error rate
        Note:
            Default query type is `min`
        Note:
            For width and depth, width may realistically be in the thousands \
            while depth is in the single digit to teens '''

    def __init__(self, width=None, depth=None, confidence=None,
                 error_rate=None, filepath=None, hash_function=None):
        ''' default initilization function '''
        # default values
        self.__width = 0
        self.__depth = 0
        self.__confidence = 0.0
        self.__error_rate = 0.0
        self.__elements_added = 0
        self.__query_method = self.__min_query

        if is_valid_file(filepath):
            self.__load(filepath)
        elif width is not None and depth is not None:
            valid_prms = (isinstance(width, Number) and width > 0 and
                          isinstance(depth, Number) and depth > 0)
            if not valid_prms:
                msg = 'CountMinSketch: width and depth must be greater than 0'
                raise InitializationError(msg)
            self.__width = int(width)
            self.__depth = int(depth)
            self.__confidence = 1 - (1 / math.pow(2, self.depth))
            self.__error_rate = 2 / self.width
            self._bins = [0] * (self.width * self.depth)
        elif confidence is not None and error_rate is not None:
            valid_prms = (isinstance(confidence, Number) and confidence > 0 and
                          isinstance(error_rate, Number) and error_rate > 0)
            if not valid_prms:
                msg = 'CountMinSketch: width and depth must be greater than 0'
                raise InitializationError(msg)
            self.__confidence = confidence
            self.__error_rate = error_rate
            self.__width = math.ceil(2 / error_rate)
            numerator = (-1 * math.log(1 - confidence))
            self.__depth = math.ceil(numerator / 0.6931471805599453)
            self._bins = [0] * int(self.width * self.depth)
        else:
            msg = ('Must provide one of the following to initialize the '
                   'Count-Min Sketch:\n'
                   '    A file to load,\n'
                   '    The width and depth,\n'
                   '    OR confidence and error rate')
            raise InitializationError(msg)

        if hash_function is None:
            self._hash_function = default_fnv_1a
        else:
            self._hash_function = hash_function

    def __str__(self):
        ''' string representation of the count min sketch '''
        msg = ('Count-Min Sketch:\n'
               '\tWidth: {0}\n'
               '\tDepth: {1}\n'
               '\tConfidence: {2}\n'
               '\tError Rate: {3}\n'
               '\tElements Added: {4}')
        return msg.format(self.width, self.depth, self.confidence,
                          self.error_rate, self.elements_added)

    @property
    def width(self):
        ''' int: The width of the count-min sketch

            Note:
                Not settable '''
        return self.__width

    @property
    def depth(self):
        ''' int: The depth of the count-min sketch

            Note:
                Not settable '''
        return self.__depth

    @property
    def confidence(self):
        ''' float: The confidence of the count-min sketch

            Note:
                Not settable '''
        return self.__confidence

    @property
    def error_rate(self):
        ''' float: The error rate of the count-min sketch

            Note:
                Not settable '''
        return self.__error_rate

    @property
    def elements_added(self):
        ''' int: The number of elements added to the count-min sketch

            Note:
                Not settable '''
        return self.__elements_added

    @property
    def query_type(self):
        ''' str: The name of the query type being used

            Note:
                Valid values:
                    * 'min' or None
                    * 'mean'
                    * 'mean-min' '''
        if self.__query_method == self.__mean_query:
            return 'mean'
        elif self.__query_method == self.__mean_min_query:
            return 'mean-min'
        return 'min'

    @query_type.setter
    def query_type(self, val):
        ''' set to min query Options='min', 'mean', 'mean-min'
            other values are set to min
            setting to mean is converting to a Count-Mean Sketch
            setting to mean-min is converting to a Count-Mean-Min Sketch '''
        if val is None:
            self.__query_method = self.__min_query
            return
        val = val.lower()
        if val == 'mean':
            self.__query_method = self.__mean_query
        elif val == 'mean-min':
            self.__query_method = self.__mean_min_query
        else:
            self.__query_method = self.__min_query

    def clear(self):
        ''' Reset the count-min sketch to an empty state '''
        self.__elements_added = 0
        for i, _ in enumerate(self._bins):
            self._bins[i] = 0

    def hashes(self, key, depth=None):
        ''' Return the hashes based on the provided key

            Args:
                key (str): Description of arg1
                depth (int): Number of permutations of the hash to generate; \
                if None, generate `number_hashes`

            Returns:
                List(int): A list of the hashes for the key in int form '''
        t_depth = self.depth if depth is None else depth
        return self._hash_function(key, t_depth)

    def add(self, key, num_els=1):
        ''' Insert the element `key` into the count-min sketch

            Args:
                key (str): The element to insert
                num_els (int): The number of times to insert the element
            Returns:
                int: The number of times the element was likely inserted \
                after the insertion '''
        hashes = self.hashes(key)
        return self.add_alt(hashes, num_els)

    def add_alt(self, hashes, num_els=1):
        ''' Insert an element by using the hash representation

            Args:
                key (str): The element to insert
                num_els (int): The number of times to insert the element
            Returns:
                int: The number of times the element was likely inserted \
                after the insertion '''
        res = list()
        for i, val in enumerate(hashes):
            t_bin = (val % self.width) + (i * self.width)
            self._bins[t_bin] += num_els
            if self._bins[t_bin] > INT32_T_MAX:
                self._bins[t_bin] = INT32_T_MAX
            res.append(self._bins[t_bin])
        self.__elements_added += num_els

        if self.elements_added > INT64_T_MAX:
            self.__elements_added = INT64_T_MAX
        return self.__query_method(sorted(res))

    def remove(self, key, num_els=1):
        ''' Remove element 'key' from the count-min sketch

            Args:
                key (str): The element to remove
                num_els (int): The number of times to remove the element
            Returns:
                int: The number of times the element was likely inserted \
                after the removal '''
        hashes = self.hashes(key)
        return self.remove_alt(hashes, num_els)

    def remove_alt(self, hashes, num_els=1):
        ''' Remove an element by using the hash representation

            Args:
                hashes (list): The hashes representing the element to remove
                num_els (int): The number of times to remove the element
            Returns:
                int: The number of times the element was likely inserted \
                after the removal '''
        res = list()
        for i, val in enumerate(hashes):
            t_bin = (val % self.width) + (i * self.width)
            self._bins[t_bin] -= num_els
            if self._bins[t_bin] < INT32_T_MIN:
                self._bins[t_bin] = INT32_T_MIN
            res.append(self._bins[t_bin])
        self.__elements_added -= num_els
        if self.elements_added < INT64_T_MIN:
            self.__elements_added = INT64_T_MIN

        return self.__query_method(sorted(res))

    def check(self, key):
        ''' Check number of times element 'key' is in the count-min sketch

            Args:
                key (str): The key to check the number of times inserted
            Returns:
                int: The number of times the element was likely inserted '''
        hashes = self.hashes(key)
        return self.check_alt(hashes)

    def check_alt(self, hashes):
        ''' Check the count-min sketch for an element by using the hash \
            representation

            Args:
                hashes (list): The hashes representing the element to check
            Returns:
                int: The number of times the element was likely inserted '''
        bins = self.__get_values_sorted(hashes)
        return self.__query_method(bins)

    def export(self, filepath):
        ''' Export the count-min sketch to disk

            Args:
                filename (str): The filename to which the count-min sketch \
                will be written. '''
        with open(filepath, 'wb') as filepointer:
            # write out the bins
            rep = 'i' * len(self._bins)
            filepointer.write(pack(rep, *self._bins))
            filepointer.write(pack('IIq', self.width, self.depth,
                                   self.elements_added))

    def __load(self, filepath):
        ''' load the count-min sketch from file '''
        with open(filepath, 'rb') as filepointer:
            offset = calcsize('IIq')
            filepointer.seek(offset * -1, os.SEEK_END)
            mybytes = unpack('IIq', filepointer.read(offset))
            self.__width = mybytes[0]
            self.__depth = mybytes[1]
            self.__elements_added = mybytes[2]
            self.__confidence = 1 - (1 / math.pow(2, self.depth))
            self.__error_rate = 2 / self.width

            filepointer.seek(0, os.SEEK_SET)
            length = self.width * self.depth
            rep = 'i' * length
            offset = calcsize(rep)
            self._bins = list(unpack(rep, filepointer.read(offset)))

    def __get_values_sorted(self, hashes):
        ''' get the values sorted '''
        bins = list()
        for i, val in enumerate(hashes):
            t_bin = (val % self.width) + (i * self.width)
            bins.append(self._bins[t_bin])
        bins.sort()
        return bins

    @staticmethod
    def __min_query(results):
        ''' generate the min query; assumes sorted list '''
        return results[0]

    def __mean_query(self, results):
        ''' generate the mean query; assumes sorted list '''
        return sum(results) // self.depth

    def __mean_min_query(self, results):
        ''' generate the mean-min query; assumes sorted list '''
        meanmin = list()
        for t_bin in results:
            diff = self.elements_added - t_bin
            calc = t_bin - diff // (self.width - 1)
            meanmin.append(calc)
        meanmin.sort()
        if self.depth % 2 == 0:
            calc = meanmin[self.depth//2] + meanmin[self.depth//2 - 1]
            res = calc // 2
        else:
            res = meanmin[self.depth//2]
        return res


class CountMeanSketch(CountMinSketch):
    ''' Simple Count-Mean Sketch implementation for use in python;
        It can read and write the same format as the c version
        (https://github.com/barrust/count-min-sketch)

        Args:
            width (int): The width of the count-min sketch
            depth (int): The depth of the count-min sketch
            confidence (float): The level of confidence desired
            error_rate (float): The desired error rate
            filepath (string): Path to file to load
            hash_function (function): Hashing strategy function to use \
            `hf(key, number)`
        Returns:
            CountMeanSketch: A Count-Mean Sketch object
        Note:
            Initialization order of operations:
                1) From file
                2) Width and depth
                3) Confidence and error rate
        Note:
            Default query type is `mean`
        Note:
            For width and depth, width may realistically be in the thousands \
            while depth is in the single digit to teens  '''
    def __init__(self, width=None, depth=None, confidence=None,
                 error_rate=None, filepath=None, hash_function=None):
        super(CountMeanSketch, self).__init__(width, depth, confidence,
                                              error_rate, filepath,
                                              hash_function)
        self.query_type = 'mean'


class CountMeanMinSketch(CountMinSketch):
    ''' Simple Count-Mean-Min Sketch implementation for use in python;
        It can read and write the same format as the c version
        (https://github.com/barrust/count-min-sketch)

        Args:
            width (int): The width of the count-min sketch
            depth (int): The depth of the count-min sketch
            confidence (float): The level of confidence desired
            error_rate (float): The desired error rate
            filepath (string): Path to file to load
            hash_function (function): Hashing strategy function to use \
            `hf(key, number)`
        Returns:
            CountMeanMinSketch: A Count-Mean-Min Sketch object
        Note:
            Initialization order of operations:
                1) From file
                2) Width and depth
                3) Confidence and error rate
        Note:
            Default query type is `mean-min`
        Note:
            For width and depth, width may realistically be in the thousands \
            while depth is in the single digit to teens  '''
    def __init__(self, width=None, depth=None, confidence=None,
                 error_rate=None, filepath=None, hash_function=None):
        super(CountMeanMinSketch, self).__init__(width, depth, confidence,
                                                 error_rate, filepath,
                                                 hash_function)
        self.query_type = 'mean-min'


class HeavyHitters(CountMinSketch):
    ''' Find and track those elements that are the most common, or heavy
        hitters

        Args:
            num_hitters (int): The maximum number of distinct elements to track
            width (int): The width of the count-min sketch
            depth (int): The depth of the count-min sketch
            confidence (float): The level of confidence desired
            error_rate (float): The desired error rate
            filepath (string): Path to file to load
            hash_function (function): Hashing strategy function to use \
            `hf(key, number)`
        Returns:
            HeavyHitters: A Count-Min Sketch object
        Note:
            Initialization order of operations:
                1) From file
                2) Width and depth
                3) Confidence and error rate
        Note:
            Default query type is `min`
        Note:
            For width and depth, width may realistically be in the thousands \
            while depth is in the single digit to teens  '''

    def __init__(self, num_hitters=100, width=None, depth=None,
                 confidence=None, error_rate=None, filepath=None,
                 hash_function=None):

        super(HeavyHitters, self).__init__(width, depth, confidence,
                                           error_rate, filepath,
                                           hash_function)
        self.__top_x = dict()  # top x heavy hitters
        self.__top_x_size = 0
        self.__num_hitters = num_hitters
        self.__smallest = 0

    def __str__(self):
        ''' heavy hitters string rep '''
        msg = super(HeavyHitters, self).__str__()
        tmp = ('Heavy Hitters {0}\n'
               '\tNumber Hitters: {1}\n'
               '\tNumber Recorded: {2}')
        return tmp.format(msg, self.number_heavy_hitters, self.__top_x_size)

    @property
    def heavy_hitters(self):
        ''' dict: Return the heavy hitters, or most common elements

            Note:
                Not settable '''
        return self.__top_x

    @property
    def number_heavy_hitters(self):
        ''' int: Return the maximum number of heavy hitters being tracked

            Note:
                Not settable '''
        return self.__num_hitters

    def add(self, key, num_els=1):
        ''' Add element to heavy hitters

            Args:
                key (str): The element to add
                num_els (int): The number of instances to add
            Returns:
                int: Number of times key has been inserted
            Note:
                Override function '''
        hashes = self.hashes(key)
        return self.add_alt(key, hashes, num_els)

    def add_alt(self, key, hashes, num_els=1):
        ''' Add the element `key` represented as hashes to the HeavyHitters
            object (hence the different signature on the function!)

            Args:
                key (str): The element to add
                hashes (list): The list of integers representing the key to \
                insert
                num_els (int): The number of instances to add
            Returns:
                int: Number of times key has been inserted
            Note:
                Different key signature than the normal :class:`CountMinSketch`
            Note:
                Override function '''
        res = super(HeavyHitters, self).add_alt(hashes, num_els)

        # update the heavy hitters list as necessary
        if self.__top_x_size < self.__num_hitters:  # still have room in top x
            tmp = self.__top_x.get(key, None)
            self.__top_x[key] = res
            if tmp is None:
                self.__top_x_size = len(self.__top_x)
        elif key in self.__top_x:  # easy update as it is already there
            self.__top_x[key] = res
        elif res > self.__smallest:  # something in there is smaller
            self.__top_x[key] = res
            # get the key with the smallest element
            tmp_key = min(self.__top_x, key=self.__top_x.get)
            # delete this key
            self.__top_x.pop(tmp_key, None)
            new_min = min(self.__top_x, key=self.__top_x.get)
            self.__smallest = self.__top_x[new_min]
        return res

    def remove_alt(self, hashes, num_els=1):
        ''' Remove element based on hashes provided; not supported in
            heavy hitters

            Raises:
                NotSupportedError: This function is not supported by the \
                HeavyHitters class
            Note:
                Override function '''
        msg = ('Unable to remove elements in the HeavyHitters '
               'class as it is an un supported action (and does not'
               'make sense)!')
        raise NotSupportedError(msg)

    def clear(self):
        ''' Clear out the heavy hitters! '''
        super(HeavyHitters, self).clear()
        self.__top_x = dict()
        self.__top_x_size = 0
        self.__smallest = 0


class StreamThreshold(CountMinSketch):
    ''' keep track of those elements over a certain threshold '''

    def __init__(self, threshold=100, width=None, depth=None,
                 confidence=None, error_rate=None, filepath=None,
                 hash_function=None):
        super(StreamThreshold, self).__init__(width, depth, confidence,
                                              error_rate, filepath,
                                              hash_function)
        self.__threshold = threshold
        self.__meets_threshold = dict()

    def __str__(self):
        ''' stream threshold string rep '''
        msg = super(StreamThreshold, self).__str__()
        tmp = ('Stream Threshold {0}\n'
               '\tThreshold: {1}\n'
               '\tNumber Meeting Threshold: {2}')
        return tmp.format(msg, self.threshold, len(self.__meets_threshold))

    @property
    def meets_threshold(self):
        ''' dict: Those keys that meet the required threshold (with value) '''
        return self.__meets_threshold

    @property
    def threshold(self):
        ''' int: The threshold at which a key is tracked '''
        return self.__threshold

    def clear(self):
        ''' Clear out the stream threshold! '''
        super(StreamThreshold, self).clear()
        self.__meets_threshold = dict()

    def add(self, key, num_els=1):
        ''' Add the element for key into the data structure

            Args:
                key (str): The element to add
                num_els (int): The number of instances to add
            Returns:
                int: Number of times key has been inserted
            Note:
                Override function '''
        hashes = self.hashes(key)
        return self.add_alt(key, hashes, num_els)

    def add_alt(self, key, hashes, num_els=1):
        ''' Add the element for key into the data structure

            Args:
                key (str): The element to add
                hashes (list): The list of integers representing the key to \
                insert
                num_els (int): The number of instances to add
            Returns:
                int: Number of times key has been inserted
            Note:
                Different key signature than the normal :class:`CountMinSketch`
            Note:
                Override function '''
        res = super(StreamThreshold, self).add_alt(hashes, num_els)
        if res >= self.__threshold:
            self.__meets_threshold[key] = res
        return res

    def remove(self, key, num_els=1):
        ''' Remove element 'key' from the count-min sketch

            Args:
                key (str): The element to remove
                num_els (int): The number of times to remove the element
            Returns:
                int: The number of times the element was likely inserted \
                after the removal
            Note:
                Override function '''
        hashes = self.hashes(key)
        return self.remove_alt(key, hashes, num_els)

    def remove_alt(self, key, hashes, num_els=1):
        ''' Remove an element by using the hash representation

            Args:
                key (str): The key that the hashes represent
                hashes (list): The hashes representing the element to remove
                num_els (int): The number of times to remove the element
            Returns:
                int: The number of times the element was likely inserted \
                after the removal
            Note:
                Different key signature than the normal :class:`CountMinSketch`
            Note:
                Override function '''
        res = super(StreamThreshold, self).remove_alt(hashes, num_els)
        if res < self.__threshold:
            self.__meets_threshold.pop(key, None)
        else:
            self.__meets_threshold[key] = res
        return res
