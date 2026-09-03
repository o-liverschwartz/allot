# apportion

Split a whole number of units across buckets in proportion to weights, when some
buckets have a floor, some have a ceiling, and the total has to come out exact.

```python
from apportion import allocate

allocate(100, {"a": 0.5, "b": 0.3, "c": 0.2})
# {'a': 50, 'b': 30, 'c': 20}

allocate(10, {"a": 0.9, "b": 0.1}, minima={"b": 3}, maxima={"a": 6})
# {'a': 6, 'b': 4}  -- b's floor is met, a is capped, the total is still 10
```

Pure Python, no dependencies, one function.

## The problem

Proportional splits produce fractions, and units are whole. Rounding each bucket
independently does not sum back to the total: three buckets at 33.3% of 100 round
to 33 each and lose a unit. The standard fix is largest-remainder — floor
everything, then hand the leftover units to the largest fractional parts.

Constraints are where it gets awkward. Real buckets have rules: never send fewer
than 2, never more than the shelf holds. The tempting move is to apply those rules
during the rounding step, and that is the move that breaks the total.

## Why the ordering matters

This library exists because of that mistake. In the tool it came out of, the
minimum was applied inside the floor calculation — every bucket got
`max(floor(share), 1)`. It reads as reasonable and it is fine at scale. Then a
total of 1 was split across 8 buckets and the function returned 8 units, having
invented seven of them out of a rounding rule.

`allocate` orders the work so the sum is exact by construction:

1. **Satisfy every floor first**, before anything proportional happens. If the
   floors already exceed the total, that is infeasible and it raises, rather than
   quietly returning more than it was given.
2. **Apportion what is left** among buckets that still have room. Buckets that
   would exceed their ceiling are filled to the ceiling and dropped, and their
   surplus is redistributed among the rest. That repeats until nothing more caps
   out, which is water-filling.
3. **Integerise last**, by largest remainder, skipping anything already at its
   ceiling.

The result sums to `total` exactly, or you get an `AllocationError` explaining
which constraint made it impossible. There is no third outcome; the invariant is
asserted before returning.

## Install

```
pip install git+https://github.com/o-liverschwartz/apportion
```

## Use

```python
allocate(total, weights, *, minima=None, maxima=None) -> dict[str, int]
```

- `total` — units to distribute, a non-negative integer
- `weights` — relative shares, non-negative, need not sum to 1
- `minima` — per-bucket floor, default 0
- `maxima` — per-bucket ceiling, default unbounded

Weights that are all zero fall back to an even split. Ties in the
largest-remainder step break by weight, then by key, so the same input always
returns the same output.

`AllocationError` is raised when the request cannot be honoured:

```python
allocate(5, {"a": 1, "b": 1}, minima={"a": 4, "b": 4})
# AllocationError: infeasible: minima sum to 8, above total 5

allocate(10, {"a": 1, "b": 1}, maxima={"a": 2, "b": 2})
# AllocationError: infeasible: maxima sum to 4, below total 10
```

## Where it came from

A retail replenishment tool I built, which decides how many units of a style to
send to each size. A size curve gives the weights, the buy gives the total, and
sizes carry both a floor (a size shown on the shelf needs stock behind it) and a
ceiling (there is only so much room). Every allocation has to be whole units and
has to add up to the buy, because the warehouse ships what the number says.

That tool is JavaScript and has its own implementation; this is the routine
rewritten as a standalone Python package with the ordering fixed and the
constraint handling generalised. The same shape turns up well outside retail —
seats to parties, budget to departments, requests to workers, samples to strata.

## Tests

```
python -m pytest
```

The suite checks the guarantee that matters — output sums to `total`, floors and
ceilings are respected, or it raises — including against randomised inputs, plus
the specific case that motivated the library.

## Licence

MIT. See [LICENSE](LICENSE).
