"""Test suite for rounded weighted vector strategy."""

import numpy as np
import pytest

from application.services.pair_generation import RoundedWeightedAverageVectorStrategy


@pytest.fixture
def strategy():
    return RoundedWeightedAverageVectorStrategy()


def test_strategy_name(strategy):
    """Test if strategy name is correct."""
    assert strategy.get_strategy_name() == "rounded_weighted_average_vector"


def test_generate_different_random_vector(strategy):
    """Test if random vector generation works correctly."""
    user_vector = (20, 30, 50)
    existing_vectors = {user_vector}

    random_vector = strategy._generate_different_random_vector(
        user_vector, 3, existing_vectors
    )

    assert isinstance(random_vector, tuple)
    assert len(random_vector) == 3
    assert sum(random_vector) == 100
    assert random_vector != user_vector
    # Test that values are multiples of 5
    assert all(v % 5 == 0 for v in random_vector)


def test_rounded_vector(strategy):
    """Test if vector rounding works correctly."""
    # Test case 1: Vector that needs minimal adjustment
    input_vector = np.array([38, 39, 23])
    result = strategy._rounded_vector(input_vector)
    assert all(v % 5 == 0 for v in result)
    assert sum(result) == 100

    # Test case 2: Vector with decimal values
    input_vector = np.array([33.33, 33.33, 33.34])
    result = strategy._rounded_vector(input_vector)
    assert all(v % 5 == 0 for v in result)
    assert sum(result) == 100

    # Test case 3: Vector already in multiples of 5
    input_vector = np.array([40, 35, 25])
    result = strategy._rounded_vector(input_vector)
    assert all(v % 5 == 0 for v in result)
    assert sum(result) == 100


def test_calculate_weighted_vector(strategy):
    """Test if weighted vector calculation works correctly with rounding."""
    # Test case from documentation example
    user_vector = np.array([60, 25, 15])
    random_vector = np.array([30, 45, 25])
    x_weight = 0.3

    weighted_vector = strategy._calculate_weighted_vector(
        user_vector, random_vector, x_weight
    )

    assert isinstance(weighted_vector, tuple)
    assert len(weighted_vector) == 3
    assert sum(weighted_vector) == 100
    assert all(v % 5 == 0 for v in weighted_vector)

    # Test with different weights
    x_weight = 0.7
    weighted_vector = strategy._calculate_weighted_vector(
        user_vector, random_vector, x_weight
    )

    assert sum(weighted_vector) == 100
    assert all(v % 5 == 0 for v in weighted_vector)


def test_generate_pairs(strategy):
    """Test if pair generation works correctly with rounding."""
    user_vector = (20, 30, 50)
    pairs = strategy.generate_pairs(user_vector, n=10, vector_size=3)

    assert len(pairs) == 10
    assert all(len(pair) == 2 for pair in pairs)
    assert all(len(v) == 3 for pair in pairs for v in pair)

    # Test that all vectors sum to 100 and are multiples of 5
    for random_vector, weighted_vector in pairs:
        assert sum(random_vector) == 100
        assert sum(weighted_vector) == 100
        assert all(v % 5 == 0 for v in random_vector)
        assert all(v % 5 == 0 for v in weighted_vector)

    # Test that no random vector is the same as user_vector
    for random_vector, _ in pairs:
        assert random_vector != user_vector


def test_generate_pairs_error_handling(strategy):
    """Test if pair generation handles errors correctly."""
    invalid_vector = (0, 0, 0)
    with pytest.raises(ValueError):
        strategy.generate_pairs(invalid_vector, n=10, vector_size=3)


def test_edge_cases(strategy):
    """Test edge cases for rounding behavior."""
    # Test with very small decimals
    input_vector = np.array([33.33334, 33.33333, 33.33333])
    result = strategy._rounded_vector(input_vector)
    assert all(v % 5 == 0 for v in result)
    assert sum(result) == 100

    # Test with large numbers before rounding
    user_vector = np.array([90, 5, 5])
    random_vector = np.array([10, 45, 45])
    x_weight = 0.5
    result = strategy._calculate_weighted_vector(user_vector, random_vector, x_weight)
    assert all(v % 5 == 0 for v in result)
    assert sum(result) == 100


def test_rounding_consistency(strategy):
    """Test if rounding is consistent across multiple calls."""
    user_vector = np.array([60, 25, 15])
    random_vector = np.array([30, 45, 25])
    x_weight = 0.3

    # Generate multiple results and verify they're all the same
    results = [
        strategy._calculate_weighted_vector(user_vector, random_vector, x_weight)
        for _ in range(5)
    ]

    # All results should be identical
    assert all(result == results[0] for result in results)
    # All results should be multiples of 5
    assert all(v % 5 == 0 for result in results for v in result)
