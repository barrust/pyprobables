''' pyprobables module '''
from __future__ import (unicode_literals, absolute_import, print_function)
from .blooms import (BloomFilter, BloomFilterOnDisk, CountingBloomFilter)
from .countminsketch import (CountMinSketch, HeavyHitters, StreamThreshold,
                             CountMeanSketch, CountMeanMinSketch)
from .exceptions import (InitializationError, NotSupportedError,
                         ProbablesBaseException)

__author__ = 'Tyler Barrus'
__maintainer__ = 'Tyler Barrus'
__email__ = 'barrust@gmail.com'
__license__ = 'MIT'
__version__ = '0.0.6'
__credits__ = []
__url__ = 'https://github.com/barrust/pyprobables'
__bugtrack_url__ = 'https://github.com/barrust/pyprobables/issues'

__all__ = ['BloomFilter', 'BloomFilterOnDisk', 'CountMinSketch',
           'HeavyHitters', 'StreamThreshold', 'CountMeanSketch',
           'CountMeanMinSketch', 'CountingBloomFilter']
