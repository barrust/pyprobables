.. _quickstart:

pyprobables Quickstart
######################

.. toctree::
   :maxdepth: 5

   quickstart


Install
**************************

The easiest method of installing pyprobables is by using the pip package
manager:

Pip Installation:

::

    $ pip install pyprobables


API Documentation
**************************

The full API documentation for the pyprobables package:  :ref:`api`

Example Usage
**************************

Bloom Filters
==========================

Bloom Filters provide set operations of large datasets while being small in
memory footprint. They provide a zero percent false negative rate and a
predetermined false positive rate.

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



Count-Min Sketch
==========================

Count-Min Sketches, and its derivatives, are good for counting the number of
occurrences of an element in streaming data while not needing to retain all the
data elements. The result is a probabilistic count of elements inserted into
the data structure. It will always provide a **maximum** number of times
encountered.

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
