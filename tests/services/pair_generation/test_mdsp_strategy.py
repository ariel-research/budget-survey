"""Tests for the MultiDimensionalSinglePeakedStrategy."""

from unittest.mock import patch

import pytest

from application.exceptions import UnsuitableForStrategyError
from application.services.pair_generation import (
    MultiDimensionalSinglePeakedStrategy,
)


@pytest.fixture
def strategy():
    return MultiDimensionalSinglePeakedStrategy()


def enumerate_all_valid_vectors():
    """Enumerate all valid 3D budget vectors using 5-point granularity."""
    valid_vectors = []
    for a in range(5, 100, 5):
        for b in range(5, 100, 5):
            c = 100 - a - b
            if 5 <= c <= 95 and c % 5 == 0:
                valid_vectors.append((a, b, c))
    return valid_vectors


def test_is_unambiguously_closer_cases_REVISED(strategy):
    """Tests the core logic of the updated MDSP comparison."""
    peak = (40, 30, 30)

    # Case 1: Valid - 'near' is strictly closer on all dimensions
    q_far = (48, 20, 32)  # D_far = [+8, -10, +2]
    q_near = (44, 25, 31)  # D_near = [+4, -5, +1]
    assert strategy._is_unambiguously_closer(peak, q_near, q_far)

    # Case 2: Invalid - sign mismatch
    sign_mismatch_near = (40, 35, 25)  # D = [0, +5, -5]
    assert not strategy._is_unambiguously_closer(
        peak,
        sign_mismatch_near,
        q_far,
    )

    # Case 3: Invalid - 'near' is farther on one dimension
    farther_component = (44, 25, 33)  # D = [+4, -5, +3]
    assert not strategy._is_unambiguously_closer(
        peak,
        farther_component,
        q_far,
    )

    # Case 4: Valid - 'near' equals the peak (strict on non-zero dims)
    at_peak = peak  # D = [0, 0, 0]
    assert strategy._is_unambiguously_closer(peak, at_peak, q_far)

    # Case 5: Invalid - 'near' identical to 'far'
    assert not strategy._is_unambiguously_closer(peak, q_far, q_far)


def test_peak_dimension_edge_cases_REVISED(strategy):
    """
    Tests scenarios where one or more coordinates matches the peak exactly.
    """
    peak = (50, 30, 20)

    # Case 1: Valid - unchanged coordinate remains valid under revised logic
    q_far = (50, 40, 10)  # D_far = [0, +10, -10]
    q_near = (50, 35, 15)  # D_near = [0, +5, -5]
    assert strategy._is_unambiguously_closer(peak, q_near, q_far)

    # Case 2: Invalid - 'near' moves further away on an unchanged dimension
    q_far = (50, 40, 10)  # D_far = [0, +10, -10]
    q_near = (55, 35, 15)  # D_near = [+5, +5, -5]
    assert not strategy._is_unambiguously_closer(peak, q_near, q_far)

    # Case 3: Valid - 'near' moves to the peak on one dimension
    q_far = (55, 40, 5)  # D_far = [+5, +10, -15]
    q_near = (50, 35, 15)  # D_near = [0, +5, -5]
    assert strategy._is_unambiguously_closer(peak, q_near, q_far)

    # Case 4: Valid - 'near' equals the peak
    q_far = (55, 35, 10)  # D_far = [+5, +5, -10]
    q_near = (50, 30, 20)  # D_near = [0, 0, 0]
    assert strategy._is_unambiguously_closer(peak, q_near, q_far)


def test_unsuitable_for_zero_entries(strategy):
    """Zero entries in the user vector remain unsuitable for the strategy."""
    user_vector = (60, 40, 0)
    with pytest.raises(UnsuitableForStrategyError):
        strategy.generate_pairs(user_vector, n=10, vector_size=3)


def test_generate_pairs_filters_user_vector(strategy):
    """Generated pairs never reuse the original user vector."""
    user_vector = (40, 35, 25)
    pairs = strategy.generate_pairs(user_vector, n=10, vector_size=3)

    assert len(pairs) == 10
    far_desc = strategy.get_option_description(role="far")
    near_desc = strategy.get_option_description(role="near")

    for pair in pairs:
        vectors = list(pair.values())
        assert user_vector not in vectors
        far_vector = pair[far_desc]
        near_vector = pair[near_desc]
        assert strategy._is_unambiguously_closer(
            user_vector,
            near_vector,
            far_vector,
        )


def test_generate_pairs_failure(strategy):
    """Generation fails fast when the strategy never finds valid pairs."""
    user_vector = (40, 35, 25)

    with (
        patch.object(MultiDimensionalSinglePeakedStrategy, "MAX_ATTEMPTS", 5),
        patch.object(
            MultiDimensionalSinglePeakedStrategy,
            "_is_unambiguously_closer",
            return_value=False,
        ),
    ):
        with pytest.raises(ValueError):
            strategy.generate_pairs(user_vector, n=10, vector_size=3)


def test_all_valid_vectors_generate_successfully(strategy):
    """MDSP should generate pure pairs for every valid user vector."""
    valid_vectors = enumerate_all_valid_vectors()

    failed_vectors = []
    for user_vector in valid_vectors:
        try:
            pairs = strategy.generate_pairs(user_vector, n=10, vector_size=3)
            assert len(pairs) == 10
        except (ValueError, UnsuitableForStrategyError) as error:
            failed_vectors.append((user_vector, str(error)))

    success_rate = 1 - (len(failed_vectors) / len(valid_vectors))

    if failed_vectors:
        print(f"\nFailed vectors ({len(failed_vectors)}):")
        for vec, err in failed_vectors[:10]:
            print(f"  {vec}: {err[:60]}")

    assert success_rate == 1.0, (
        "Must generate pairs for ALL valid vectors. "
        f"Success rate: {success_rate:.1%} "
        f"({len(failed_vectors)} failures)"
    )
