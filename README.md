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
* `json_get` function for extracting data from within
  nested lists and dicts such as those returned from a JSON api.
* `locate_key` function for searching through JSON for a dict key matching a regular expression

  
## Changelog

### 0.0.4
* Added `dirf` module

### 0.0.6
* Added `data_structures` module

### 0.0.7
* Added `string` module with normalize_whitespace function

### 0.0.8
* Added `json.locate_key` function
* Got `dirf.dirf` working.
