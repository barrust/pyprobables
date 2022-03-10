# PyProbables Changelog

### Version 0.5.6
* Bloom Filters:
    * Fix for `ValueError` exception when using `estimate_elements()` when all bits are set
* Add Citation file

### Version 0.5.5
* Bloom Filters:
    * Re-implemented the entire Bloom Filter data structure to reduce complexity and code duplication
* Removed un-unsed imports
* Removed unnecessary casts
* Pylint Requested Style Changes:
    * Use python 3 `super()`
    * Use python 3 classes
* Remove use of temporary variables if possible and still clear

### Version 0.5.4
* All Probablistic Data Structures:
    * Added ability to load each `frombytes()`
    * Updated underlying data structures of number based lists to be more space and time efficient; see [Issue #60](https://github.com/barrust/pyprobables/issues/60)
* Cuckoo Filters:
    * Added `fingerprint_size_bits` property
    * Added `error_rate` property
    * Added ability to initialize based on error rate
* Simplified typing
* Ensure all `filepaths` can be `str` or `Path`

### Version 0.5.3
* Additional type hinting
* Improved format parsing and serialization; [see PR#81](https://github.com/barrust/pyprobables/pull/81). Thanks [@KOLANICH](https://github.com/KOLANICH)
* Bloom Filters
    * Added `export_to_hex` functionality for Bloom Filters on Disk
    * Export as C header (**\*.h**) for Bloom Filters on Disk and Counting Bloom Filters
* Added support for more input types for exporting and loading of saved files


### Version 0.5.2
* Add ability to hash bytes along with strings
* Make all tests files individually executable from the CLI. Thanks [@KOLANICH](https://github.com/KOLANICH)
* Added type hints

### Version 0.5.1
* Bloom Filter:
    * Export as a C header (**\*.h**)
* Count-Min Sketch
    * Add join/merge functionality
* Moved testing to use `NamedTemporaryFile` for file based tests

### Version 0.5.0
* ***BACKWARD INCOMPATIBLE CHANGES***
   * **NOTE:** Breaks backwards compatibility with previously exported blooms, counting-blooms, cuckoo filter, or count-min-sketch files using the default hash!
   * Update to the FNV_1a hash function
   * Simplified the default hash to use a seed value
* Ensure passing of depth to hashing function when using `hash_with_depth_int` or `hash_with_depth_bytes`

## Version 0.4.1
* Resolve [issue 57](https://github.com/barrust/pyprobables/issues/57) where false positive rate not stored / used the same in some instances

## Version 0.4.0
* Remove **Python 2.7** support

### Version 0.3.2
* Fix `RotatingBloomFilter` to keep information on number of elements inserted when exported and loaded. [see PR #50](https://github.com/barrust/pyprobables/pull/50) Thanks [@dvolker48](https://github.com/volker48)

### Version 0.3.1
* Add additional __slots__
* Very minor improvement to the hashing algorithm

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
