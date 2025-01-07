"""Test suite for weighted vector strategy."""

import numpy as np
import pytest

from application.services.pair_generation import WeightedAverageVectorStrategy


@pytest.fixture
def strategy():
    return WeightedAverageVectorStrategy()


def test_strategy_name(strategy):
    """Test if strategy name is correct."""
    assert strategy.get_strategy_name() == "weighted_average_vector"


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


def test_calculate_weighted_vector(strategy):
    """Test if weighted vector calculation works correctly."""
    user_vector = np.array([20, 30, 50])
    random_vector = np.array([40, 40, 20])
    x_weight = 0.1

    weighted_vector = strategy._calculate_weighted_vector(
        user_vector, random_vector, x_weight
    )

    assert isinstance(weighted_vector, tuple)
    assert len(weighted_vector) == 3
    assert sum(weighted_vector) == 100
    assert weighted_vector == (38, 39, 23)


def test_generate_pairs(strategy):
    """Test if pair generation works correctly."""
    user_vector = (20, 30, 50)
    pairs = strategy.generate_pairs(user_vector, n=10, vector_size=3)

    assert len(pairs) == 10
    assert all(len(pair) == 2 for pair in pairs)
    assert all(len(v) == 3 for pair in pairs for v in pair)
    assert all(sum(v) == 100 for pair in pairs for v in pair)

    # Test that no random vector is the same as user_vector
    for random_vector, _ in pairs:
        assert random_vector != user_vector


def test_generate_pairs_error_handling(strategy):
    """Test if pair generation handles errors correctly."""
    invalid_vector = (0, 0, 0)
    with pytest.raises(ValueError):
        strategy.generate_pairs(invalid_vector, n=10, vector_size=3)


def test_all_vectors_sum_to_100(strategy):
    """Test if all generated vectors sum to exactly 100."""
    user_vector = (20, 30, 50)
    pairs = strategy.generate_pairs(user_vector)

    for random_vector, weighted_vector in pairs:
        assert sum(random_vector) == 100
        assert sum(weighted_vector) == 100
