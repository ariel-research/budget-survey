"""Test suite for optimization metrics strategy."""

import pytest

from application.services.pair_generation.optimization import (
    OptimizationMetricsStrategy,
)


@pytest.fixture
def strategy():
    return OptimizationMetricsStrategy()


def test_sum_of_differences(strategy):
    """Test if sum_of_differences calculates correctly."""
    user_vector = (10, 20, 70)
    generated_vector = (15, 25, 60)
    assert strategy.sum_of_differences(user_vector, generated_vector) == 20


def test_minimal_ratio(strategy):
    """Test if minimal_ratio calculates correctly."""
    user_vector = (50, 30, 20)
    generated_vector = (30, 40, 30)
    assert strategy._minimal_ratio(user_vector, generated_vector) == 0.6


def test_calculate_optimization_metrics(strategy):
    """Test if optimization metrics are calculated correctly."""
    user_vector = (50, 30, 20)
    v1 = (30, 40, 30)
    v2 = (60, 20, 20)
    metrics = strategy._calculate_optimization_metrics(user_vector, v1, v2)
    assert len(metrics) == 4
    assert isinstance(metrics[0], (int, float))


def test_is_valid_pair(strategy):
    """Test if pair validation works correctly."""
    # Test case where first vector is better in sum, worse in ratio
    metrics = (30, 40, 0.6, 0.8)  # s1, s2, r1, r2
    assert strategy._is_valid_pair(metrics)

    # Test case where neither vector dominates
    metrics = (30, 40, 0.8, 0.6)
    assert not strategy._is_valid_pair(metrics)


def test_generate_pairs(strategy):
    """Test if pair generation works correctly."""
    user_vector = (60, 20, 20)
    n_pairs = 5
    pairs = strategy.generate_pairs(user_vector, n=n_pairs, vector_size=3)

    assert len(pairs) == n_pairs
    assert all(len(pair) == 2 for pair in pairs)
    assert all(len(v) == 3 for pair in pairs for v in pair)
    assert all(sum(v) == 100 for pair in pairs for v in pair)


@pytest.mark.parametrize("n_pairs", [5, 10, 15])
def test_generate_pairs_different_sizes(strategy, n_pairs):
    """Test if pair generation works with different numbers of pairs."""
    user_vector = (60, 20, 20)
    pairs = strategy.generate_pairs(user_vector, n=n_pairs, vector_size=3)
    assert len(pairs) == n_pairs


def test_generate_pairs_error_handling(strategy):
    """Test if pair generation handles errors correctly."""
    invalid_vector = (0, 0, 0)
    with pytest.raises(ValueError):
        strategy.generate_pairs(invalid_vector, n=10, vector_size=3)


def test_generated_pairs_are_valid(strategy):
    """Test if all generated pairs satisfy the complementary optimization properties."""
    user_vector = (60, 20, 20)
    pairs = strategy.generate_pairs(user_vector, n=10, vector_size=3)

    for v1, v2 in pairs:
        # Calculate optimization metrics for the pair
        metrics = strategy._calculate_optimization_metrics(user_vector, v1, v2)

        # Check if pair has valid optimization trade-offs
        assert strategy._is_valid_pair(metrics), (
            f"Invalid pair found:\n"
            f"Vector 1: {v1}\n"
            f"Vector 2: {v2}\n"
            f"Metrics (s1, s2, r1, r2): {metrics}"
        )
