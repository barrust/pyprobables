.. _api:

pyprobables API
====================

Here you can find the full developer API for the pyprobables project.
pyprobables provides a suite of probabilistic data-structures to be used
in data analytics and data science projects.


Data Structures and Classes
============================

Bloom Filters
-------------

Bloom Filters are a class of probabilistic data structures used for set
operations. Bloom Filters guarantee a zero percent false negative rate
and a predetermined false positive rate. Once the number of elements inserted
exceeds the estimated elements, the false positive rate will increase over the
desired amount.
`Further Reading <https://en.wikipedia.org/wiki/Bloom_filter>`__


.. _BloomFilterAnchor:

BloomFilter
+++++++++++++++++++++++++++++++

.. autoclass:: probables.BloomFilter
    :members:
    :inherited-members:


BloomFilterOnDisk
+++++++++++++++++++++++++++++++

.. autoclass:: probables.BloomFilterOnDisk
    :members:

For more information of all methods and properties, see `BloomFilter`_.

ExpandingBloomFilter
+++++++++++++++++++++++++++++++

.. autoclass:: probables.ExpandingBloomFilter
    :members:

RotatingBloomFilter
+++++++++++++++++++++++++++++++

.. autoclass:: probables.RotatingBloomFilter
    :members:
    :inherited-members:

CountingBloomFilter
+++++++++++++++++++++++++++++++

.. autoclass:: probables.CountingBloomFilter
    :members:
    :inherited-members:


Cuckoo Filters
--------------

Cuckoo filters are a space efficient data structure that supports set
membership testing. Cuckoo filters support insertion, deletion, and lookup of
elements with low overhead and few false positive results. The name is derived
from the `cuckoo hashing <https://en.wikipedia.org/wiki/Cuckoo_hashing>`__
strategy used to resolve conflicts.
`Further Reading <https://www.cs.cmu.edu/~dga/papers/cuckoo-conext2014.pdf>`__

CuckooFilter
+++++++++++++++++++++++++++++++
.. autoclass:: probables.CuckooFilter
    :members:

CountingCuckooFilter
+++++++++++++++++++++++++++++++
.. autoclass:: probables.CountingCuckooFilter
    :members:
    :inherited-members:


Count-Min Sketches
------------------

Count-Min Sketches, and its derivatives, are good for estimating the number of
occurrences of an element in streaming data while not needing to retain all the
data elements. The result is a probabilistic count of elements inserted into
the data structure. It will always provide the **maximum** number of times a
data element was encountered. Notice that the result may be **more** than the
true number of times it was inserted, but never fewer.
`Further Reading <https://en.wikipedia.org/wiki/Count%E2%80%93min_sketch>`__


CountMinSketch
+++++++++++++++++++++++++++++++

.. autoclass:: probables.CountMinSketch
    :members:


CountMeanSketch
+++++++++++++++++++++++++++++++

.. autoclass:: probables.CountMeanSketch
    :members:

For more information of all methods and properties, see `CountMinSketch`_.


CountMeanMinSketch
+++++++++++++++++++++++++++++++

.. autoclass:: probables.CountMeanMinSketch
    :members:

For more information of all methods and properties, see `CountMinSketch`_.


HeavyHitters
+++++++++++++++++++++++++++++++

.. autoclass:: probables.HeavyHitters
    :members:

For more information of all methods and properties, see `CountMinSketch`_.


StreamThreshold
+++++++++++++++++++++++++++++++

.. autoclass:: probables.StreamThreshold
    :members:

For more information of all methods and properties, see `CountMinSketch`_.


Exceptions
============================

.. automodule:: probables.exceptions
    :members:


Hashing Functions
============================

.. automodule:: probables.hashes
    :members:


Indices and Tables
============================

* :ref:`home`
* :ref:`quickstart`
* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
