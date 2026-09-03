from __future__ import annotations

from math import floor, inf
from typing import Mapping


class AllocationError(ValueError):
    pass


def allocate(
    total: int,
    weights: Mapping[str, float],
    *,
    minima: Mapping[str, int] | None = None,
    maxima: Mapping[str, int] | None = None,
) -> dict[str, int]:
    """Allocate exactly ``total`` whole units using bounded largest remainder.

    Floors are satisfied first. Remaining units are apportioned proportionally
    among buckets that still have capacity. Caps are resolved before the final
    largest-remainder rounding step.
    """
    if total < 0:
        raise AllocationError("total must be non-negative")
    if not weights:
        if total == 0:
            return {}
        raise AllocationError("weights cannot be empty when total > 0")
    if any(w < 0 for w in weights.values()):
        raise AllocationError("weights must be non-negative")

    keys = list(weights)
    minima = minima or {}
    maxima = maxima or {}
    mins = {k: int(minima.get(k, 0)) for k in keys}
    maxs = {k: int(maxima[k]) if k in maxima else inf for k in keys}

    for k in keys:
        if mins[k] < 0:
            raise AllocationError(f"minimum for {k} must be non-negative")
        if maxs[k] < mins[k]:
            raise AllocationError(f"maximum for {k} is below its minimum")

    min_sum = sum(mins.values())
    finite_max_sum = sum(v for v in maxs.values() if v != inf)
    has_unbounded = any(v == inf for v in maxs.values())
    if min_sum > total:
        raise AllocationError(f"infeasible: minima sum to {min_sum}, above total {total}")
    if not has_unbounded and finite_max_sum < total:
        raise AllocationError(f"infeasible: maxima sum to {finite_max_sum}, below total {total}")

    result = mins.copy()
    remaining = total - min_sum
    if remaining == 0:
        return result

    # Continuous water-filling target for the remaining units.
    targets = {k: 0.0 for k in keys}
    active = {k for k in keys if result[k] < maxs[k]}
    left = float(remaining)

    while active and left > 1e-12:
        weight_sum = sum(weights[k] for k in active)
        basis = {k: (weights[k] if weight_sum > 0 else 1.0) for k in active}
        basis_sum = sum(basis.values())
        capped: list[str] = []

        for k in active:
            ideal = left * basis[k] / basis_sum
            capacity = maxs[k] - result[k]
            if capacity != inf and ideal >= capacity - 1e-12:
                targets[k] += float(capacity)
                left -= float(capacity)
                capped.append(k)

        if capped:
            active.difference_update(capped)
            continue

        for k in active:
            targets[k] += left * basis[k] / basis_sum
        left = 0.0

    if left > 1e-9:
        raise AllocationError("infeasible: insufficient capacity")

    # Integerize by largest remainder while respecting caps.
    extras = {k: floor(targets[k]) for k in keys}
    for k in keys:
        result[k] += extras[k]

    assigned = sum(extras.values())
    leftover = remaining - assigned
    ranking = sorted(keys, key=lambda k: (targets[k] - floor(targets[k]), weights[k], k), reverse=True)

    for k in ranking:
        if leftover == 0:
            break
        if result[k] < maxs[k]:
            result[k] += 1
            leftover -= 1

    if leftover != 0 or sum(result.values()) != total:
        raise AssertionError("exact-sum invariant violated")
    return result
