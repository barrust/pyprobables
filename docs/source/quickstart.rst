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


Counting Bloom Filter
"""""""""""""""""""""""""""""""""""""""""""""""

**Counting Bloom Filters** are another specialized version of the standard
Bloom Filter. Instead of using a bit array to track added elements, a
Counting Bloom uses integers to track the number of times the element has
been added. **currently not supported; planned**


Count-Min Sketch
==========================

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


Indices and tables
==================

* :ref:`home`
* :ref:`api`
* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
