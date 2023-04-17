# jocassid-commons

## Overview
Miscellaneous utility code written in Python.  Modules within this library 
include:

### `accumulator_dict`
* `AccumulatorDict` - A `dict` where keys are lists or sets and 
`accumulator_dict[key] = value` will add `value` to the list or set for that key

### `data_structures`
* `MergeQueue` - An Iterable that merges data from two or more iterables or 
iterators.  It's original purpose was to merge two iterables of sorted data 
while retaining the sort order.

### `dirf`
* Contains the `dirf` function a wrapper around the built-in `dir` function that adds filtering capabilities.

### `json`
* Contains the `json_get` method for extracting data from within
  nested lists and dicts such as those returned from a JSON api.

  
## Changelog

### 0.0.4
* Added `dirf` module

### 0.0.6
* Added `data_structures` module
