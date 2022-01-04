.. _quickstart:

Quickstart
==========================


Install
+++++++++++++++++++++++++++++++

The easiest method of installing pyprobables is by using the pip package
manager:

Pip Installation:

::

    $ pip install pyprobables


API Documentation
+++++++++++++++++++++++++++++++

The full API documentation for the pyprobables package:  :ref:`api`

Example Usage
+++++++++++++++++++++++++++++++

Bloom Filters
-------------

Bloom Filters provide set operations of large datasets while being small in
memory footprint. They provide a zero percent false negative rate and a
predetermined, or desired, false positive rate.
`more information <https://en.wikipedia.org/wiki/Bloom_filter>`__


Import, Initialize, and Train
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. code:: python

    >>> from probables import (BloomFilter)
    >>> blm = BloomFilter(est_elements=1000000, false_positive_rate=0.05)
    >>> with open('war_and_peace.txt', 'r') as fp:
    >>>     for line in fp:
    >>>         for word in line.split():
    >>>             blm.add(word.lower())  # add each word to the bloom filter!
    >>> # end reading in the file


Query the Bloom Filter
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. code:: python

    >>> words_to_check = ['step', 'borzoi', 'diametrically', 'fleches', 'rain']
    >>> for word in words_to_check:
    >>>     blm.check(word)


Export the Bloom Filter
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. code:: python

    >>> blm.export('war_and_peace_bloom.blm')


Import a Bloom Filter
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. code:: python

    >>> blm2 = BloomFilter(filepath='war_and_peace_bloom.blm')
    >>> print(blm2.check('sutler'))


Other Bloom Filters
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Bloom Filter on Disk
"""""""""""""""""""""""""""""""""""""""""""""""

The **Bloom Filter on Disk** is a specialized version of the standard
Bloom Filter that is run directly off of disk instead of in memory. This
can be useful for very large Bloom Filters or when needing to access many
Blooms that are exported to file.


Expanding Bloom Filter
"""""""""""""""""""""""""""""""""""""""""""""""

The **Expanding Bloom Filter** is a specialized version of the standard
Bloom Filter that automatically grows to ensure that the desired false positive
rate is not exceeded. This is ideal for situations that it is a wild guess to
determine the number of elements that will be added.


Rotating Bloom Filter
"""""""""""""""""""""""""""""""""""""""""""""""

The **Rotating Bloom Filter** is a specialized version of the standard
Bloom Filter that rolls of earlier entries into the filter as they become more
stale. The popping of the queue can be done either programmatically or
automatically.


Counting Bloom Filter
"""""""""""""""""""""""""""""""""""""""""""""""

**Counting Bloom Filters** are another specialized version of the standard
Bloom Filter. Instead of using a bit array to track added elements, a
Counting Bloom uses integers to track the number of times the element has
been added.


Count-Min Sketch
-----------------

Count-Min Sketches, and its derivatives, are good for counting the number of
occurrences of an element in streaming data while not needing to retain all the
data elements. The result is a probabilistic count of elements inserted into
the data structure. It will always provide a **maximum** number of times
encountered. Notice that the result may be **more** than the true number
of times it was inserted, but never fewer.
`more information <https://en.wikipedia.org/wiki/Count%E2%80%93min_sketch>`__


Import, Initialize, and Train
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. code:: python

    >>> from probables import (CountMinSketch)
    >>> cms = CountMinSketch(width=100000, depth=5)
    >>> with open('war_and_peace.txt', 'r') as fp:
    >>>     for line in fp:
    >>>         for word in line.split():
    >>>             cms.add(word.lower())  # add each to the count-min sketch!


Query the Count-Min Sketch
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. code:: python

    >>> words_to_check = ['step', 'borzoi', 'diametrically', 'fleches', 'rain']
    >>> for word in words_to_check:
    >>>     print(cms.check(word))  # prints: 80, 17, 1, 20, 25


Export Count-Min Sketch
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. code:: python

    >>> cms.export('war_and_peace.cms')


Import a Count-Min Sketch
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. code:: python

    >>> cms2 = CountMinSketch(filepath='war_and_peace.cms')
    >>> print(cms2.check('fleches'))  # prints 20


Other Count-Min Sketches
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Count-Mean Sketch and Count-Mean-Min Sketch
"""""""""""""""""""""""""""""""""""""""""""""""

**Count-Mean Sketch** and **Count-Mean-Min Sketch** are identical to the
Count-Min Sketch for the data structure but both differ in the method of
calculating the number of times and element has been inserted. These are
currently supported by specifying at query time which method is desired
or by initializing to the desired class: CountMeanSketch or CountMeanMinSketch.


Heavy Hitters
"""""""""""""""""""""""""""""""""""""""""""""""

**Heavy Hitters** is a version of the Count-Min Sketch that tracks those
elements that are seen most often. Beyond the normal initialization parameters
one only needs to specify the number of heavy hitters to track.


Stream Threshold
"""""""""""""""""""""""""""""""""""""""""""""""

**Stream Threshold** is another version of the Count-Min Sketch similar to the
Heavy Hitters. The main difference is that the there is a threshold for
including an element to be tracked instead of tracking a certain number of
elements.


Cuckoo Filters
----------------------------------

Cuckoo Filters are a memory efficient method to approximate set membership.
They allow for the ability to add, remove, and look elements from the set.
They get the name cuckoo filter from the use of the
`cuckoo hashing <https://en.wikipedia.org/wiki/Cuckoo_hashing>`__ strategy.

Import, Initialize, and Train
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. code:: python3

    >>> from probables import (CuckooFilter)
    >>> ccf = CuckooFilter(capacity=100000, bucket_size=4, max_swaps=100)
    >>> with open('war_and_peace.txt', 'r') as fp:
    >>>     for line in fp:
    >>>         for word in line.split():
    >>>             ccf.add(word.lower())  # add each to the cuckoo filter!


Query the Cuckoo Filter
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. code:: python3

    >>> words_to_check = ['borzoi', 'diametrically', 'fleches', 'rain', 'foo']
    >>> for word in words_to_check:
    >>>     print(ccf.check(word))  # prints: True, True, True, True, False


Export the Cuckoo Filter
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. code:: python3

    >>> ccf.export('war_and_peace.cko')


Import a Cuckoo Filter
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. code:: python3

    >>> ccf2 = CuckooFilter(filepath='war_and_peace.cko')
    >>> print(ccf2.check('fleches'))  # prints True

Cuckoo Filters based on Error Rate
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
To use error rate to initialize a Cuckoo Filter, there are class methods that can be used.
`init_error_rate()` can be used to initialize a Cuckoo Filter that has not been exported, and
`load_error_rate()` can be used to load in a previously exported Cuckoo Filter that used error rate
to determine the parameters.

.. code:: python3

    >>> cko = CuckooFilter.init_error_rate(0.00001)
    >>> cko.export('war_and_peace.cko')
    >>> ckf = CuckooFilter.load_error_rate(0.00001)

Other Cuckoo Filters
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Counting Cuckoo Filter
"""""""""""""""""""""""""""""""""""""""""""""""
The counting cuckoo filter is similar to the standard filter except that it
tracks the number of times a fingerprint has been added to the filter.


Custom Hashing Functions
----------------------------------
In many instances, to get the best raw performance out of the data structures,
it is wise to use a non pure python hashing algorithm. It is recommended that
one is used that is compiled such as `mmh3 <https://github.com/hajimes/mmh3>`__
or `pyhash <https://github.com/flier/pyfasthash>`__ or even built in
cryptographic hashes.

Some pre-defined hashing strategies are provided that use built in
cryptographic hashes.

To use a pre-defined alternative hashing strategy:

.. code:: python3

    >>> from probables import (BloomFilter)
    >>> from probables.hashes import (default_sha256, default_md5)
    >>> blm = BloomFilter(est_elements=1000, false_positive_rate=0.05,
                          hash_function=default_sha256)
    >>> blm.add('google.com')
    >>> blm.check('facebook.com')  # should return False
    >>> blm.check('google.com')  # should return True

Decorators are provided to help make generating hashing strategies easier.

Defining hashing function using the provided decorators:

.. code:: python3

    >>> import mmh3  # murmur hash 3 implementation (pip install mmh3)
    >>> from pyprobables.hashes import (hash_with_depth_bytes)
    >>> from pyprobables import (BloomFilter)
    >>>
    >>> @hash_with_depth_bytes
    >>> def my_hash(key):
    >>>     return mmh3.hash_bytes(key)
    >>>
    >>> blm = BloomFilter(est_elements=1000, false_positive_rate=0.05, hash_function=my_hash)

.. code:: python3

    >>> import mmh3  # murmur hash 3 implementation (pip install mmh3)
    >>> from pyprobables.hashes import (hash_with_depth_int)
    >>> from pyprobables import (BloomFilter)
    >>>
    >>> @hash_with_depth_int
    >>> def my_hash(key, encoding='utf-8'):
    >>>    max64mod = UINT64_T_MAX + 1
    >>>    val = int(hashlib.sha512(key.encode(encoding)).hexdigest(), 16)
    >>>    return val % max64mod
    >>>
    >>> blm = BloomFilter(est_elements=1000, false_positive_rate=0.05, hash_function=my_hash)

Generate completely different hashing strategy

.. code:: python3

    >>> import mmh3  # murmur hash 3 implementation (pip install mmh3)
    >>>
    >>> def my_hash(key, depth, encoding='utf-8'):
    >>>     max64mod = UINT64_T_MAX + 1
    >>>     results = list()
    >>>     for i in range(0, depth):
    >>>         tmp = key[i:] + key[:i]
    >>>         val = int(hashlib.sha512(tmp.encode(encoding)).hexdigest(), 16)
    >>>         results.append(val % max64mod)
    >>>     return results


Indices and Tables
==================

* :ref:`home`
* :ref:`api`
* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
