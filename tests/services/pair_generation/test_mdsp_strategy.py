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


def test_is_unambiguously_closer_cases(strategy):
    peak = (40, 30, 30)

    q_far = (50, 20, 30)
    q_near = (45, 25, 30)
    assert strategy._is_unambiguously_closer(peak, q_near, q_far)

    identical_far = (50, 20, 30)
    assert not strategy._is_unambiguously_closer(peak, identical_far, q_far)

    sign_mismatch_near = (40, 35, 25)
    assert not strategy._is_unambiguously_closer(peak, sign_mismatch_near, q_far)

    farther_component = (48, 18, 34)
    assert not strategy._is_unambiguously_closer(peak, farther_component, q_far)

    at_peak = peak
    assert not strategy._is_unambiguously_closer(peak, at_peak, q_far)


def test_unsuitable_for_zero_entries(strategy):
    user_vector = (60, 40, 0)
    with pytest.raises(UnsuitableForStrategyError):
        strategy.generate_pairs(user_vector, n=10, vector_size=3)


def test_generate_pairs_filters_user_vector(strategy):
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
        assert strategy._is_unambiguously_closer(user_vector, near_vector, far_vector)


def test_generate_pairs_failure(strategy):
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
