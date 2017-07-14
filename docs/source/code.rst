.. _api:

pyprobables API
***************

Here you can find the full developer API for the pyprobables project.
pyprobables provides a suite of probabilistic data-structures to be used
in data analytics and data science projects.


.. toctree::
   :maxdepth: 4

   code


Data Structures and Classes
===============================

Bloom Filters
-------------

Bloom Filters are a class of probabilistic data structures used for set
operations. Bloom Filters guarantee a zero percent false negative rate
and a predetermined false positive rate.


BloomFilter
+++++++++++++++++++++++++++++++

.. autoclass:: probables.BloomFilter
    :members:


BloomFilterOnDisk
+++++++++++++++++++++++++++++++

.. autoclass:: probables.BloomFilter
    :members:
    :inherited-members:


Count-Min Sketches
------------------

Count-Min Sketches are a class of probabilistic data structures designed to
count the number of occurrences of data elements in data streams.


CountMinSketch
+++++++++++++++++++++++++++++++

.. autoclass:: probables.CountMinSketch
    :members:


HeavyHitters
+++++++++++++++++++++++++++++++

.. autoclass:: probables.HeavyHitters
    :members:
    :inherited-members:


StreamThreshold
+++++++++++++++++++++++++++++++

.. autoclass:: probables.StreamThreshold
    :members:
    :inherited-members:


Exceptions
===============================

.. automodule:: probables.exceptions
    :members:


Hashing Functions
===============================

.. automodule:: probables.hashes
    :members:


Indices and tables
==================

* :ref:`home`
* :ref:`quickstart`
* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
