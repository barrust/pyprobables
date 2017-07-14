.. _api:

pyprobables API
***************

Here you can find the full developer API for the pyprobables project.

Contents:
=========

.. toctree::
   :maxdepth: 3

   code


Data Structures and Classes
===============================

Bloom Filters
-------------

Bloom Filters are a class of probabilistic data structures that guarantee a
zero percent false negative rate and a predetermined false positive rate.

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

Indices and tables
==================

* :ref:`home`
* :ref:`quickstart`
* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
