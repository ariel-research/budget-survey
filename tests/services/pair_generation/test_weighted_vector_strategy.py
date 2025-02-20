"""Test suite for weighted vector strategy with new dictionary format."""

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
    """Test if pair generation works correctly with strategy descriptions."""
    user_vector = (20, 30, 50)
    pairs = strategy.generate_pairs(user_vector, n=10, vector_size=3)

    assert len(pairs) == 10
    assert all(isinstance(pair, dict) for pair in pairs)
    assert all(len(pair) == 2 for pair in pairs)

    for pair in pairs:
        # Check strategy descriptions
        descriptions = list(pair.keys())
        vectors = list(pair.values())

        assert any("Random" in desc for desc in descriptions)
        assert any("Average Weighted" in desc for desc in descriptions)

        # Check that percentage is included in weighted vector description
        weighted_desc = next(
            desc for desc in descriptions if "Average Weighted" in desc
        )
        assert "%" in weighted_desc

        # Check vectors
        assert all(isinstance(v, tuple) for v in vectors)
        assert all(len(v) == 3 for v in vectors)
        assert all(sum(v) == 100 for v in vectors)


def test_weight_progression(strategy):
    """Test if weights are properly distributed in generated pairs."""
    user_vector = (30, 40, 30)
    pairs = strategy.generate_pairs(user_vector, n=10, vector_size=3)

    # Extract weights from descriptions
    weights = []
    for pair in pairs:
        weighted_desc = next(
            desc for desc in pair.keys() if "Average Weighted Vector" in desc
        )
        weight = int(weighted_desc.split(": ")[1].rstrip("%"))
        weights.append(weight)

    # Sort weights to verify distribution
    weights.sort()

    # Verify weight distribution
    assert 10 in weights, "Should include 10% weight"
    assert 90 in weights, "Should include 90% weight"
    assert all(
        w in [10, 20, 30, 40, 50, 50, 60, 70, 80, 90] for w in weights
    ), "Weights should match expected values"


def test_option_descriptions(strategy):
    """Test if option descriptions are generated correctly."""
    description_random = strategy.get_option_description()
    description_weighted = strategy.get_option_description(weight=0.3)

    assert description_random == "Random Vector"
    assert description_weighted == "Average Weighted Vector: 30%"

    labels = strategy.get_option_labels()
    assert labels == ("Random", "Weighted Average")


def test_generate_pairs_error_handling(strategy):
    """Test if pair generation handles errors correctly."""
    invalid_vector = (0, 0, 0)
    with pytest.raises(ValueError):
        strategy.generate_pairs(invalid_vector, n=10, vector_size=3)


def test_vector_value_ranges(strategy):
    """Test that all generated vectors maintain valid value ranges."""
    user_vector = (80, 10, 10)
    pairs = strategy.generate_pairs(user_vector, n=10, vector_size=3)

    for pair in pairs:
        vectors = list(pair.values())
        # Verify vectors maintain valid ranges
        assert all(0 <= v <= 100 for vector in vectors for v in vector)
        # Verify sums remain correct
        assert all(sum(vector) == 100 for vector in vectors)


def test_weighted_vector_consistency(strategy):
    """Test that weighted vectors are consistent with weights."""
    user_vector = np.array([60, 20, 20])
    random_vector = np.array([20, 40, 40])

    # Test different weights
    weights = [0.1, 0.3, 0.5, 0.7, 0.9]
    for weight in weights:
        weighted_vector = strategy._calculate_weighted_vector(
            user_vector, random_vector, weight
        )
        # Values should be between random and user vectors
        assert all(
            min(u, r) <= w <= max(u, r)
            for u, r, w in zip(user_vector, random_vector, weighted_vector)
        )
