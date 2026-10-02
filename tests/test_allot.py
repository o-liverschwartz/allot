"""The guarantee is that the output sums to `total` and respects every bound, or
it raises. These tests are mostly that one sentence, under pressure."""
import random

import pytest

from allot import AllocationError, allocate


def check(result, total, weights, minima=None, maxima=None):
    """Every invariant the library promises, asserted together."""
    assert sum(result.values()) == total
    assert set(result) == set(weights)
    assert all(isinstance(v, int) and v >= 0 for v in result.values())
    for k, floor in (minima or {}).items():
        assert result[k] >= floor, f"{k} fell below its minimum"
    for k, ceiling in (maxima or {}).items():
        assert result[k] <= ceiling, f"{k} exceeded its maximum"


def test_clean_split_is_exact():
    assert allocate(100, {"a": 0.5, "b": 0.3, "c": 0.2}) == {"a": 50, "b": 30, "c": 20}


def test_thirds_do_not_lose_a_unit():
    # Rounding each bucket alone gives 33/33/33 and drops one. Largest remainder
    # hands it to whichever bucket was closest to earning it.
    result = allocate(100, {"a": 1, "b": 1, "c": 1})
    check(result, 100, {"a": 1, "b": 1, "c": 1})
    assert sorted(result.values()) == [33, 33, 34]


def test_floors_are_met_and_the_total_holds():
    weights, minima = {"a": 0.9, "b": 0.1}, {"b": 3}
    result = allocate(10, weights, minima=minima)
    check(result, 10, weights, minima=minima)
    assert result["b"] >= 3


def test_a_capped_bucket_spills_into_the_others():
    weights, maxima = {"a": 0.9, "b": 0.1}, {"a": 6}
    result = allocate(10, weights, maxima=maxima)
    check(result, 10, weights, maxima=maxima)
    assert result == {"a": 6, "b": 4}


def test_capping_cascades():
    # a and b both cap out, and everything they cannot take lands on c.
    weights = {"a": 5, "b": 4, "c": 1}
    maxima = {"a": 2, "b": 2}
    result = allocate(20, weights, maxima=maxima)
    check(result, 20, weights, maxima=maxima)
    assert result == {"a": 2, "b": 2, "c": 16}


def test_the_bug_this_library_exists_for():
    """One unit across eight buckets is one unit.

    The routine this came from applied the per-bucket minimum inside the floor
    calculation, so every bucket got max(floor(share), 1) and a total of 1 came
    back as 8. Floors are satisfied before anything proportional now, so asking
    for a floor that cannot fit is an error rather than invented units.
    """
    weights = {k: 1 for k in "abcdefgh"}
    assert sum(allocate(1, weights).values()) == 1

    with pytest.raises(AllocationError, match="minima sum to 8, above total 1"):
        allocate(1, weights, minima={k: 1 for k in weights})


def test_infeasible_floors_raise():
    with pytest.raises(AllocationError, match="above total"):
        allocate(5, {"a": 1, "b": 1}, minima={"a": 4, "b": 4})


def test_infeasible_ceilings_raise():
    with pytest.raises(AllocationError, match="below total"):
        allocate(10, {"a": 1, "b": 1}, maxima={"a": 2, "b": 2})


def test_a_ceiling_under_its_own_floor_raises():
    with pytest.raises(AllocationError, match="below its minimum"):
        allocate(10, {"a": 1}, minima={"a": 5}, maxima={"a": 3})


def test_rejects_nonsense_inputs():
    with pytest.raises(AllocationError):
        allocate(-1, {"a": 1})
    with pytest.raises(AllocationError):
        allocate(10, {"a": -1})
    with pytest.raises(AllocationError):
        allocate(10, {})
    with pytest.raises(AllocationError):
        allocate(10, {"a": 1}, minima={"a": -1})


def test_empty_edges():
    assert allocate(0, {}) == {}
    assert allocate(0, {"a": 1, "b": 1}) == {"a": 0, "b": 0}


def test_zero_weights_split_evenly():
    result = allocate(9, {"a": 0, "b": 0, "c": 0})
    check(result, 9, {"a": 0, "b": 0, "c": 0})
    assert result == {"a": 3, "b": 3, "c": 3}


def test_one_weight_carries_everything():
    assert allocate(7, {"a": 1, "b": 0}) == {"a": 7, "b": 0}


def test_exact_capacity_is_feasible_not_infeasible():
    # Ceilings summing to exactly the total is the tightest legal request.
    weights, maxima = {"a": 1, "b": 1}, {"a": 3, "b": 3}
    assert allocate(6, weights, maxima=maxima) == {"a": 3, "b": 3}


def test_floors_that_exactly_fill_the_total():
    weights, minima = {"a": 1, "b": 1}, {"a": 2, "b": 3}
    result = allocate(5, weights, minima=minima)
    check(result, 5, weights, minima=minima)
    assert result == {"a": 2, "b": 3}


def test_output_is_deterministic():
    args = (37, {"a": 1.1, "b": 1.1, "c": 1.1, "d": 0.7})
    assert len({tuple(sorted(allocate(*args).items())) for _ in range(50)}) == 1


def test_holds_up_under_random_input():
    rng = random.Random(20260902)
    for _ in range(2000):
        n = rng.randint(1, 8)
        keys = [f"k{i}" for i in range(n)]
        weights = {k: rng.choice([0, rng.random(), rng.randint(1, 100)]) for k in keys}
        minima = {k: rng.randint(0, 3) for k in keys if rng.random() < 0.4}
        maxima = {k: rng.randint(0, 12) for k in keys if rng.random() < 0.4}
        total = rng.randint(0, 200)
        try:
            result = allocate(total, weights, minima=minima, maxima=maxima)
        except AllocationError:
            # Refusing is a valid outcome; returning a wrong answer is not.
            continue
        check(result, total, weights, minima, maxima)


# --- added in the fix pass: one test per bug ---------------------------------

@pytest.mark.parametrize("bad", [float("nan"), float("inf")])
def test_non_finite_weights_raise(bad):
    with pytest.raises(AllocationError, match="finite"):
        allocate(10, {"a": bad, "b": 1})


def test_a_fractional_total_raises_allocation_error():
    with pytest.raises(AllocationError, match="whole number"):
        allocate(10.5, {"a": 1, "b": 1})


def test_a_fractional_floor_is_refused_not_truncated():
    with pytest.raises(AllocationError, match="whole number"):
        allocate(10, {"a": 1, "b": 1}, minima={"a": 2.9})


def test_an_infinite_ceiling_raises_allocation_error():
    with pytest.raises(AllocationError, match="whole number"):
        allocate(10, {"a": 1, "b": 1}, maxima={"a": float("inf")})


def test_a_bool_total_is_refused():
    with pytest.raises(AllocationError, match="whole number"):
        allocate(True, {"a": 1, "b": 1})


def test_a_bound_on_a_bucket_with_no_weight_raises():
    # A typo in a key used to drop the constraint without a word.
    with pytest.raises(AllocationError, match="no weight"):
        allocate(10, {"a": 1, "b": 1}, minima={"c": 9})


def test_totals_past_float_precision_still_add_up():
    total = 10**18 + 7
    assert sum(allocate(total, {"a": 1, "b": 2, "c": 3}).values()) == total


def test_a_floor_lifts_a_bucket_to_its_floor_and_no_further():
    # c carries 80% of the weight and gets 80% of the units. a and b sit at
    # their floor instead of taking a proportional share on top of it.
    weights, minima = {"a": 1, "b": 1, "c": 8}, {"a": 2, "b": 2}
    assert allocate(10, weights, minima=minima) == {"a": 2, "b": 2, "c": 6}
    # 0.1.0 returned 11/11/78 here.
    small = allocate(100, {"a": 1, "b": 1, "c": 98}, minima={"a": 10, "b": 10})
    assert small == {"a": 10, "b": 10, "c": 80}


def test_zero_weight_buckets_are_not_used_as_overflow():
    with pytest.raises(AllocationError, match="zero-weight"):
        allocate(10, {"a": 1, "b": 0}, maxima={"a": 2})


def test_feasible_requests_are_never_refused_and_stay_near_the_exact_share():
    """Refusing a request that can be met is a bug too. And every bucket lands
    within one unit of its exact clamped share, found here by bisection."""
    from fractions import Fraction as F

    rng = random.Random(20260929)
    for _ in range(500):
        n = rng.randint(1, 8)
        keys = [f"k{i}" for i in range(n)]
        weights = {k: rng.randint(1, 100) for k in keys}
        minima = {k: rng.randint(0, 4) for k in keys if rng.random() < 0.5}
        maxima = {k: rng.randint(0, 15) for k in keys if rng.random() < 0.5}
        total = rng.randint(0, 150)
        lo = {k: minima.get(k, 0) for k in keys}
        hi = {k: maxima.get(k, 10**9) for k in keys}
        if any(hi[k] < lo[k] for k in keys) or not sum(lo.values()) <= total <= sum(hi.values()):
            continue
        result = allocate(total, weights, minima=minima, maxima=maxima)
        check(result, total, weights, minima, maxima)

        def clamped(x, weights=weights, lo=lo, hi=hi, keys=keys):
            return {k: min(max(x * weights[k], lo[k]), hi[k]) for k in keys}

        a, b = F(0), F(10**6)
        for _ in range(60):
            mid = (a + b) / 2
            a, b = (mid, b) if sum(clamped(mid).values()) < total else (a, mid)
        exact = clamped(b)
        assert all(abs(result[k] - exact[k]) < 1 + F(1, 10**6) for k in keys)
