"""Test suite for rounded weighted vector strategy."""

import numpy as np
import pytest

from application.services.pair_generation import RoundedWeightedAverageVectorStrategy


@pytest.fixture
def strategy():
    return RoundedWeightedAverageVectorStrategy()


def test_strategy_name(strategy):
    """Test if strategy name is correct."""
    assert strategy.get_strategy_name() == "star_shaped_preference_test_rounded"


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

    # Basic structure tests
    assert len(pairs) == 10
    assert all(isinstance(pair, dict) for pair in pairs)
    assert all(len(pair) == 2 for pair in pairs)

    # Test vectors in each pair
    for pair in pairs:
        vectors = list(pair.values())
        # Check vector length
        assert all(len(v) == 3 for v in vectors)
        # Check sums and multiples of 5
        assert all(sum(v) == 100 for v in vectors)
        assert all(v % 5 == 0 for vector in vectors for v in vector)

        # Get the random vector (first vector in the pair)
        random_vector = next(v for k, v in pair.items() if "Random Vector" in k)
        # Test that random vector is different from user vector
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


def test_rounding_adjustment_logic(strategy):
    """Test the adjustment logic when sum != 100 after rounding."""
    # Test case 1: Sum > 100 after rounding (should decrease largest element)
    input_vector = np.array([40, 35, 35])  # Sum = 110 after rounding
    result = strategy._rounded_vector(input_vector)
    assert result.tolist() == [30, 35, 35]  # Largest element (40) adjusted to 30
    assert sum(result) == 100
    assert all(v % 5 == 0 for v in result)

    # Test case 2: Sum < 100 after rounding (should increase largest element)
    input_vector = np.array([25, 30, 30])  # Sum = 85 after rounding
    result = strategy._rounded_vector(input_vector)
    assert result.tolist() == [25, 45, 30]  # Largest element (30) adjusted to 45
    assert sum(result) == 100
    assert all(v % 5 == 0 for v in result)

    # Test case 3: Clear largest element (middle position)
    input_vector = np.array([25, 45, 25])  # Sum = 95 after rounding
    result = strategy._rounded_vector(input_vector)
    assert result.tolist() == [25, 50, 25]  # Largest element (45) adjusted to 50
    assert sum(result) == 100
    assert all(v % 5 == 0 for v in result)


def test_specific_rounding_examples(strategy):
    """Test specific rounding examples from documentation."""
    # Test the docstring example
    input_vector = np.array([39, 39, 22])
    result = strategy._rounded_vector(input_vector)
    assert result.tolist() == [40, 40, 20]  # Exact expected output
    assert sum(result) == 100
    assert all(v % 5 == 0 for v in result)

    # Test another example that requires adjustment
    input_vector = np.array([37, 37, 26])
    result = strategy._rounded_vector(input_vector)
    assert result.tolist() == [40, 35, 25]  # Should round and adjust
    assert sum(result) == 100
    assert all(v % 5 == 0 for v in result)


def test_weighted_vector_specific_examples(strategy):
    """Test specific weighted vector examples with known outputs."""
    # Test the docstring example from the class
    user_vector = np.array([60, 25, 15])
    random_vector = np.array([30, 45, 25])
    x_weight = 0.3

    result = strategy._calculate_weighted_vector(user_vector, random_vector, x_weight)
    assert result == (40, 40, 20)  # Exact expected output from docstring
    assert sum(result) == 100
    assert all(v % 5 == 0 for v in result)

    # Test another weight to ensure consistency
    x_weight = 0.7
    result = strategy._calculate_weighted_vector(user_vector, random_vector, x_weight)
    assert sum(result) == 100
    assert all(v % 5 == 0 for v in result)
    # Should be different from the 0.3 weight result
    assert result != (40, 40, 20)
