# PyProbables Changelog

### Version 0.8.0 (unreleased)

***Breaking Changes***
`CuckooFilter` and `CountingCuckooFilter` use a new layout and export format; filters exported by earlier versions raise an `InitializationError` on load and must be rebuilt from the original elements

* `Cuckoo Filter`
  * Fix: the false positive rate was far above `error_rate` and grew with the number of elements (0.46 measured for `init_error_rate(0.001)` with 5,000 elements); both buckets were computed from the fingerprint alone, so any element whose fingerprint was stored anywhere was reported present. The first bucket now comes from a mix of the whole hash, which a 64-bit hash keeps independent of the fingerprint (partial-key cuckoo hashing, Fan et al. 2014)
  * Fix: `add()` skipped elements whose fingerprint was stored anywhere in the filter, and `remove()` could remove a different element with the same fingerprint
  * Fix: `CountingCuckooFilter.check()` could return the count of a different element with the same fingerprint
  * Fix: elements whose fingerprint was 0 were dropped on export, since 0 marks an empty slot; a fingerprint of 0 is now stored as 1
  * Fingerprints are stored in `array`s of 1, 2, or 4 bytes per slot (about 1/12 the memory, and half the export size at `error_rate=0.001`); checks are about 1.35x faster
  * Expanding adds a table with a one bit longer fingerprint instead of re-inserting fingerprints into a larger table, so `error_rate` bounds the false positive rate of the whole filter; add `layers` property
  * `init_error_rate()` uses `ceil(log2(4 * bucket_size / error_rate))` bit fingerprints and raises `InitializationError` if the error rate is not between 0 and 1 or needs more than 32 bits
  * `load_error_rate()` and `frombytes(error_rate=...)` check the error rate stored in the export
  * `expansion_rate` must be a whole number greater than 1 (`InitializationError` from the constructor, `ValueError` from the setter); `fingerprint_size` can only be changed on an empty filter
  * `buckets` returns a read-only view that builds each bin when it is accessed; `CountingCuckooBin.increment()` and `decrement()` are deprecated, since they do not change the filter

### Version 0.7.1

* `Cuckoo Filter`
  * Implement rewind for both regular and counting; see [#149](https://github.com/barrust/pyprobables/pull/149); thanks [mayur-dhavan](https://github.com/mayur-dhavan)
  * `CountingCuckooFilter`: Increment Elements Added by number of elements inserted
* `CountingBloomFilter`
  * Fix: CountingBloomFilter union/intersection overflow on large counts; see [#153](https://github.com/barrust/pyprobables/pull/153); thanks [alibb007](https://github.com/alibb007)
### Version 0.7.0

***Breaking Changes***
Minor breaking changes; mismatched Bloom filters raise a `SimilarityError` instead of returning `None`

* `BitArray`
  * Add ability to read and write as bytes
  * Add abilitt to export
* Updated typing to be more consistent and correct
* Drop python 3.9 support

### Version 0.6.2

* `BloomFilterOnDisk`
  * Fix `FileNotFound` exception; see [issue #131](https://github.com/barrust/pyprobables/issues/131)
* Additional tests for `QuotientFilter` and `ExpandingBloomFilter`
* Drop python 3.8 support
* Add python 3.14 support

### Version 0.6.1

* `QuotientFilter`:
  * Add ability to get hashes from the filter either as a list, or as a generator
  * Add quotient filter expand capability, auto and on request
  * Add QuotientFilterError exception
  * Add merge functionality
  * Add retrieve hashes from the filter
  * Add resize filter, automatically or programatically
  * Add merging two filters into one
  * Add removal of an element from the filter
* `Count-Min Sketch`:
  * Fix bug in elements added calculation when joining Count-Min Sketches; see [PR #119](https://github.com/barrust/pyprobables/pull/119); Thanks [@cunla](https://github.com/cunla)

### Version 0.6.0

* Add `QuotientFilter` implementation; [see issue #37](https://github.com/barrust/pyprobables/issues/37)
* Add `bitarray` implementation
* Bitwise operations in lieu of modulo calculations

### Version 0.5.9

* Add `py.typed` files so that mypy will find type annotations
* Drop support for python `3.6` and `3.7`

### Version 0.5.8

* Make the `mmap` utility class windows compatible; see [PR #160](https://github.com/barrust/pyprobables/pull/106); Thanks [@leonhma](https://github.com/leonhma)

### Version 0.5.7

* Update Build System and update project metadata
* Better support for `resolve_path` in passed filenames
* Remove Python 3.5 support
* Pylint inspired updates

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

* Add additional **slots**
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

* Use **slots**

### Version 0.1.4

* Drop support for python 3.3
* Ensure passing parameters correctly to parent classes

### Version 0.1.3

* Better parameter validation
* Cuckoo Filters:
  * Support passing different hash function
  * Support for different fingerprint size
* Utility to help generate valid hashing strategies using decorators
  * hash_with_depth_bytes
  * hash_with_depth_int
* Updated documentation

### Version 0.1.2

* Counting Cuckoo Filter
  * Basic functionality: add, remove, check
  * Expand
  * Import / Export
* Fix and tests for utility functions
* Fix package build

### Version 0.1.1

* CuckooFilter
  * Import / Export functionality
  * Enforce single insertion per key
  * Auto expand when insertion failure OR when called to do so (settable)

### Version 0.1.0

* Cuckoo Filter
  * Added basic Cuckoo Filter code

### Version 0.0.8

* Counting Bloom Filter
  * Estimate unique elements added
  * Union
  * Intersection
  * Jaccard Index

### Version 0.0.7

* Counting Bloom Filter
  * Fix counting bloom hex export / import
  * Fix for overflow issue in counting bloom export
  * Added ability to remove from counting bloom
* Count-Min Sketch
  * Fix for not recording large numbers of inserts and deletions correctly

### Version 0.0.6

* Probabilistic data structures added:
  * Counting Bloom Filter
* Minor code clean-up
* Re-factored Bloom Filters

### Version 0.0.5

* Better on-line documentation
* Changed access to some public functions

### Version 0.0.4

* Probabilistic data structures:
  * Bloom Filter
  * Bloom Filter (on disk)
  * Count-Min Sketch
  * Count-Mean Sketch
  * Count-Mean-Min Sketch
  * Heavy Hitters
  * Stream Threshold
* Import and export of each
