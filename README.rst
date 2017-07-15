PyProbables
===========

**pyprobables** is a python library for probabilistic data structures. The goal
is to provide the developer with a pure-python implementation of common
probabilistic data-structures to use in their work.


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

You can build the documentation yourself by running:

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

See the `API documentation <http://pyprobables.readthedocs.io/en/latest/code.html#api>`__
for other data structures available and the
`quickstart page <http://pyprobables.readthedocs.io/en/latest/quickstart.html#quickstart>`__
for more examples!


Changelog
------------------

Please see the `changelog
<https://github.com/barrust/pyprobables/blob/master/CHANGELOG.md>`__ for a list
of all changes.
