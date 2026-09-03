"""The guarantee is that the output sums to `total` and respects every bound, or
it raises. These tests are mostly that one sentence, under pressure."""
import random

import pytest

from apportion import AllocationError, allocate


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
