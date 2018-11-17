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
.. image:: https://pepy.tech/badge/pyprobables
    :target: https://pepy.tech/project/pyprobables
    :alt: Downloads

**pyprobables** is a pure-python library for probabilistic data structures.
The goal is to provide the developer with a pure-python implementation of
common probabilistic data-structures to use in their work.

To achieve better raw performance, it is recommended supplying an alternative
hashing algorithm that has been compiled in C. This could include using the
md5 and sha512 algorithms provided or installing a third party package and
writing your own hashing strategy. Some options include the murmur hash
`mmh3 <https://github.com/hajimes/mmh3>`__ or those from the
`pyhash <https://github.com/flier/pyfasthash>`__ library. Each data object in
**pyprobables** makes it easy to pass in a custom hashing function.

Read more about how to use `Supplying a pre-defined, alternative hashing strategies`_
or `Defining hashing function using the provided decorators`_.

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

Import pyprobables and setup a Bloom Filter
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: python

    from probables import (BloomFilter)
    blm = BloomFilter(est_elements=1000, false_positive_rate=0.05)
    blm.add('google.com')
    blm.check('facebook.com')  # should return False
    blm.check('google.com')  # should return True


Import pyprobables and setup a Count-Min Sketch
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: python

    from probables import (CountMinSketch)
    cms = CountMinSketch(width=1000, depth=5)
    cms.add('google.com')  # should return 1
    cms.add('facebook.com', 25)  # insert 25 at once; should return 25


Import pyprobables and setup a Cuckoo Filter
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: python

    from probables import (CuckooFilter)
    cko = CuckooFilter(capacity=100, max_swaps=10)
    cko.add('google.com')
    cko.check('facebook.com')  # should return False
    cko.check('google.com')  # should return True


Supplying a pre-defined, alternative hashing strategies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: python

    from probables import (BloomFilter)
    from probables.hashes import (default_sha256)
    blm = BloomFilter(est_elements=1000, false_positive_rate=0.05,
                      hash_function=default_sha256)
    blm.add('google.com')
    blm.check('facebook.com')  # should return False
    blm.check('google.com')  # should return True


.. _use-custom-hashing-strategies:

Defining hashing function using the provided decorators
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: python

    import mmh3  # murmur hash 3 implementation (pip install mmh3)
    from pyprobables.hashes import (hash_with_depth_bytes)
    from pyprobables import (BloomFilter)

    @hash_with_depth_bytes
    def my_hash(key):
        return mmh3.hash_bytes(key)

    blm = BloomFilter(est_elements=1000, false_positive_rate=0.05, hash_function=my_hash)

.. code:: python

    import mmh3  # murmur hash 3 implementation (pip install mmh3)
    from pyprobables.hashes import (hash_with_depth_int)
    from pyprobables import (BloomFilter)

    @hash_with_depth_int
    def my_hash(key, encoding='utf-8'):
        max64mod = UINT64_T_MAX + 1
        val = int(hashlib.sha512(key.encode(encoding)).hexdigest(), 16)
        return val % max64mod

    blm = BloomFilter(est_elements=1000, false_positive_rate=0.05, hash_function=my_hash)


See the `API documentation <http://pyprobables.readthedocs.io/en/latest/code.html#api>`__
for other data structures available and the
`quickstart page <http://pyprobables.readthedocs.io/en/latest/quickstart.html#quickstart>`__
for more examples!


Changelog
------------------

Please see the `changelog
<https://github.com/barrust/pyprobables/blob/master/CHANGELOG.md>`__ for a list
of all changes.
