# Changelog

## 0.2.0

Changed

- A floor now clamps. A bucket at its floor no longer also takes a share of what is left. `allocate(100, {"a": 1, "b": 1, "c": 98}, minima={"a": 10, "b": 10})` returned 11, 11, 78 in 0.1.0. It returns 10, 10, 80. Any request with a floor above a bucket's proportional share can change.
- A bucket with weight zero no longer takes overflow when the other buckets are full. It raises.
- Arithmetic is exact, so totals past 2**53 add up. 0.1.0 raised AssertionError from about 10**16.

Fixed

- A NaN weight was accepted and an infinite weight raised ValueError. Both raise AllocationError.
- A fractional total raised AssertionError, fractional floors and ceilings were truncated, an infinite ceiling raised OverflowError, and `True` was taken as a total of 1. They raise AllocationError.
- A key in minima or maxima with no weight was ignored. It raises.

Added

- `__version__`, a `py.typed` marker, a CI workflow, and this file.

## 0.1.0

First version. `allocate` with floors, ceilings and largest-remainder rounding.
