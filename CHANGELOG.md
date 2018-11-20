# PyProbables Changelog

### Version 0.3.0
* Bloom Filters:
    * Import/Export of Expanding and Rotating Bloom Filters
    * Fix for importing standard Bloom Filters

### Version 0.2.6
* Bloom Filters:
    * Addition of a Rotating Bloom Filter

### Version 0.2.5
* Bloom Filters:
    * Addition of an Expanding Bloom Filter

### Version 0.2.0
* Use __slots__

### Version 0.1.4:
* Drop support for python 3.3
* Ensure passing parameters correctly to parent classes

### Version 0.1.3:
* Better parameter validation
* Cuckoo Filters:
    * Support passing different hash function
    * Support for different fingerprint size
* Utility to help generate valid hashing strategies using decorators
    * hash_with_depth_bytes
    * hash_with_depth_int
* Updated documentation

### Version 0.1.2:
* Counting Cuckoo Filter
    * Basic functionality: add, remove, check
    * Expand
    * Import / Export
* Fix and tests for utility functions
* Fix package build

### Version 0.1.1:
* CuckooFilter
    * Import / Export functionality
    * Enforce single insertion per key
    * Auto expand when insertion failure OR when called to do so (settable)

### Version 0.1.0:
* Cuckoo Filter
    * Added basic Cuckoo Filter code

### Version 0.0.8:
* Counting Bloom Filter
    * Estimate unique elements added
    * Union
    * Intersection
    * Jaccard Index

### Version 0.0.7:
* Counting Bloom Filter
    * Fix counting bloom hex export / import
    * Fix for overflow issue in counting bloom export
    * Added ability to remove from counting bloom
* Count-Min Sketch
    * Fix for not recording large numbers of inserts and deletions correctly

### Version 0.0.6:
* Probabilistic data structures added:
    * Counting Bloom Filter
* Minor code clean-up
* Re-factored Bloom Filters

### Version 0.0.5:
* Better on-line documentation
* Changed access to some public functions

### Version 0.0.4:
* Probabilistic data structures:
    * Bloom Filter
    * Bloom Filter (on disk)
    * Count-Min Sketch
    * Count-Mean Sketch
    * Count-Mean-Min Sketch
    * Heavy Hitters
    * Stream Threshold
* Import and export of each
