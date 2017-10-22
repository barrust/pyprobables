PyProbables
===========

.. image:: https://badge.fury.io/py/pyprobables.svg
    :target: https://badge.fury.io/py/pyprobables
.. image:: https://coveralls.io/repos/github/barrust/pyprobables/badge.svg
    :target: https://coveralls.io/github/barrust/pyprobables
.. image:: https://travis-ci.org/barrust/pyprobables.svg?branch=master
    :target: https://travis-ci.org/barrust/pyprobables
.. image:: https://readthedocs.org/projects/pyprobables/badge/?version=latest
    :target: http://pyprobables.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status
.. image:: https://img.shields.io/badge/license-MIT-blue.svg
    :target: https://opensource.org/licenses/MIT/
    :alt: License

**pyprobables** is a python library for probabilistic data structures. The goal
is to provide the developer with a pure-python implementation of common
probabilistic data-structures to use in their work.

**pyprobables** uses a pure python hashing algorithm. To reduce speed and gain
raw performance, it is recommended using a different hashing algorithm such as
the murmur hash (mmh3) or the pyhash library. Each data object makes it easy to
pass in a hashing function as desired.

Installation
------------------

Pip Installation:

::

    $ pip install pyprobables

To install from source:

To install `pyprobables`, simply clone the `repository on GitHub
<https://github.com/barrust/pyprobables>`__, then run from the folder:

::

    $ python setup.py install

`pyprobables` supports python versions 2.7 and 3.3 - 3.6


API Documentation
---------------------

The documentation of is hosted on
`readthedocs.io <http://pyprobables.readthedocs.io/en/latest/code.html#api>`__

You can build the documentation locally by running:

::

    $ pip install sphinx
    $ cd docs/
    $ make html



Automated Tests
------------------

To run automated tests, one must simply run the following command from the
downloaded folder:

::

  $ python setup.py test



Quickstart
------------------

Import pyprobables and setup a Bloom Filter:

.. code:: python

    >>> from probables import (BloomFilter)
    >>> blm = BloomFilter(est_elements=1000, false_positive_rate=0.05)
    >>> blm.add('google.com')
    >>> blm.check('facebook.com')  # should return False
    >>> blm.check('google.com')  # should return True


Import pyprobables and setup a Count-Min Sketch:

.. code:: python

    >>> from probables import (CountMinSketch)
    >>> cms = CountMinSketch(width=1000, depth=5)
    >>> cms.add('google.com')  # should return 1
    >>> cms.add('facebook.com', 25)  # insert 25 at once; should return 25


Import pyprobables and setup a Cuckoo Filter:

.. code:: python

    >>> from probables import (CuckooFilter)
    >>> cko = CuckooFilter(capacity=100, max_swaps=10)
    >>> cko.add('google.com')
    >>> cko.check('facebook.com')  # should return False
    >>> cko.check('google.com')  # should return True

See the `API documentation <http://pyprobables.readthedocs.io/en/latest/code.html#api>`__
for other data structures available and the
`quickstart page <http://pyprobables.readthedocs.io/en/latest/quickstart.html#quickstart>`__
for more examples!


Changelog
------------------

Please see the `changelog
<https://github.com/barrust/pyprobables/blob/master/CHANGELOG.md>`__ for a list
of all changes.
