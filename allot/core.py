from __future__ import annotations

from collections.abc import Mapping
from fractions import Fraction
from math import floor, isfinite


class AllocationError(ValueError):
    pass


def _whole(name: str, value) -> int:
    whole = isinstance(value, int) and not isinstance(value, bool) or isinstance(value, float) and value.is_integer()
    if not whole:
        raise AllocationError(f"{name} must be a whole number, got {value!r}")
    return int(value)


def allocate(
    total: int,
    weights: Mapping[str, float],
    *,
    minima: Mapping[str, int] | None = None,
    maxima: Mapping[str, int] | None = None,
) -> dict[str, int]:
    """Split ``total`` whole units in proportion to ``weights``, exactly.

    Each bucket is clamped to its floor and ceiling, and the rest share what is
    left in proportion to their weights. Arithmetic is exact (Fractions), so the
    result sums to ``total`` for any size of ``total`` or raises AllocationError.
    """
    total = _whole("total", total)
    if total < 0:
        raise AllocationError("total must be non-negative")
    minima, maxima = minima or {}, maxima or {}
    unknown = (set(minima) | set(maxima)) - set(weights)
    if unknown:
        raise AllocationError(f"minima or maxima name buckets with no weight: {sorted(map(str, unknown))}")
    if not weights:
        if total == 0:
            return {}
        raise AllocationError("weights cannot be empty when total > 0")
    for k, w in weights.items():
        if not isfinite(w) or w < 0:
            raise AllocationError(f"weight for {k} must be finite and non-negative")

    lo = {k: _whole(f"minimum for {k}", minima.get(k, 0)) for k in weights}
    hi = {k: _whole(f"maximum for {k}", maxima[k]) if k in maxima else None for k in weights}
    for k in weights:
        if lo[k] < 0:
            raise AllocationError(f"minimum for {k} must be non-negative")
        if hi[k] is not None and hi[k] < lo[k]:
            raise AllocationError(f"maximum for {k} is below its minimum")
    if sum(lo.values()) > total:
        raise AllocationError(f"infeasible: minima sum to {sum(lo.values())}, above total {total}")
    if None not in hi.values() and sum(hi.values()) < total:
        raise AllocationError(f"infeasible: maxima sum to {sum(hi.values())}, below total {total}")

    # All-zero weights mean "no opinion": split evenly.
    w = {k: Fraction(v) for k, v in weights.items()}
    if not any(w.values()):
        w = {k: Fraction(1) for k in w}

    # Clamp-and-redistribute. Fix buckets at a bound, share the rest by weight.
    # If clamping added units, the bucket shares must shrink, so fix the floors;
    # if it removed units, fix the ceilings. That order keeps every fix final.
    target: dict[str, Fraction] = {}
    free = set(w)
    while free:
        rest = total - sum(target.values())
        wsum = sum(w[k] for k in free)
        if wsum == 0:  # only zero-weight buckets left: they get their floor
            target.update({k: Fraction(lo[k]) for k in free})
            break
        share = {k: rest * w[k] / wsum for k in free}
        low = [k for k in free if share[k] < lo[k]]
        high = [k for k in free if hi[k] is not None and share[k] > hi[k]]
        if not low and not high:
            target.update(share)
            break
        gain = sum(lo[k] - share[k] for k in low) - sum(share[k] - hi[k] for k in high)
        pick = (low if gain > 0 else high) if gain else low + high
        target.update({k: Fraction(lo[k] if k in low else hi[k]) for k in pick})
        free -= set(pick)
    if sum(target.values()) != total:
        raise AllocationError(
            f"infeasible: buckets with weight cannot take all {total} units within their bounds,"
            " and zero-weight buckets do not take overflow"
        )

    result = {k: floor(t) for k, t in target.items()}
    leftover = total - sum(result.values())
    ranking = sorted(w, key=lambda k: (target[k] - result[k], w[k], k), reverse=True)
    for k in ranking[:leftover]:
        result[k] += 1
    return {k: result[k] for k in weights}
