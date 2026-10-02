# allot

Split a whole number of units across buckets in proportion to weights, with an optional floor and ceiling per bucket, so the total always adds up. Pulled out of a retail replenishment tool, [Replenish](https://oliverschwartz.me/replenish). More of my work is at [oliverschwartz.me](https://oliverschwartz.me).

```python
from allot import allocate

curve = {"8": 2, "9": 5, "10": 9, "11": 8, "12": 4, "13": 1}

allocate(24, curve, minima={s: 1 for s in curve}, maxima={"10": 6})
# {'8': 2, '9': 4, '10': 6, '11': 7, '12': 4, '13': 1}
```

24 pairs, six sizes, a floor of 1 on every size, and room for only 6 on size 10. On weight alone size 10 would take 7.45 pairs. The shelf holds 6, so it stops there and the extra 1.45 spills to the other sizes in proportion to their weights. Size 13 then comes to 0.9 of a pair, under its floor, so it sits at 1. The result is whole numbers and adds up to 24.

[Oliver: pairs and shoe sizes in this example. Too close to the business for a public README, or keep them?]

An impossible request raises instead of returning something close:

```python
allocate(1, {c: 1 for c in "abcdefgh"}, minima={c: 1 for c in "abcdefgh"})
# AllocationError: infeasible: minima sum to 8, above total 1
```

## Why this exists

I built a replenishment tool that decides how many pairs of a shoe go to each size. A size curve gives the weights. The buy gives the total. Every size has a floor, because a size on the shelf needs one behind it, and a ceiling, because the shelf is finite. The warehouse ships exactly what the number says, so the sizes have to add up to the buy.

Rounding each size on its own does not add up. My first version applied the minimum inside the rounding step, so every size got at least one pair. Then one pair was split across eight sizes and the function returned eight. It invented seven pairs out of a rounding rule.

[Oliver: did it happen that way, in your first version? If not, what really happened, in one or two sentences?]

allot holds any bucket at its floor or ceiling, splits the rest by weight, and rounds last. If the request is impossible it raises. It does not return a wrong number.

[Oliver: does the JavaScript engine in Replenish add a floor on top of a proportional share, or clamp to the floor like 0.2.0 does?]

## Install and run

```
pip install git+https://github.com/o-liverschwartz/allot@v0.2.0
```

Python 3.10 or later, no dependencies. It is not on PyPI, because another project already owns the name.

```
allocate(total, weights, *, minima=None, maxima=None) -> dict[str, int]
```

- `total`: units to distribute, a non-negative whole number
- `weights`: relative shares, finite and non-negative, need not sum to 1
- `minima`: per-bucket floor, whole numbers, default 0
- `maxima`: per-bucket ceiling, whole numbers, default none

A key in `minima` or `maxima` that is not in `weights` raises, so a typo cannot drop a constraint. If every weight is zero the split is even. Ties in the remainder go to the heavier weight, then to the key that sorts last, so the same input always returns the same output.

## What it does not do

- It does not choose the weights or the total. Those are your judgment.
- It does not search for a best answer. There is one answer for each input.
- A bucket with weight zero gets its floor and nothing else. If the other buckets are full and units are left over, it raises.
- It uses largest remainder only. It is not Sainte-Lague or Huntington-Hill.
- It takes whole numbers only. Pass money as integer cents.

## Tests

```
pip install ".[test]"
python -m pytest
```

The suite checks that the output sums to `total` and respects every floor and ceiling, or the call raises. A randomised test also checks that a request that can be met is never refused, and that every bucket lands within one unit of its exact share.

[Oliver: keep the `Co-Authored-By: Claude` trailers on commits, and say here how you used AI on this library?]

## License

MIT. See [LICENSE](LICENSE).
