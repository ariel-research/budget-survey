"""Test suite for optimization metrics strategy with new dictionary format."""

import pytest

from application.services.pair_generation.optimization_metrics_vector import (
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
    assert strategy.minimal_ratio(user_vector, generated_vector) == 0.6


def test_generate_pairs(strategy):
    """Test if pair generation works correctly with strategy descriptions."""
    user_vector = (60, 20, 20)
    n_pairs = 5
    pairs = strategy.generate_pairs(user_vector, n=n_pairs, vector_size=3)

    assert len(pairs) == n_pairs
    assert all(isinstance(pair, dict) for pair in pairs)
    assert all(len(pair) == 2 for pair in pairs)

    for pair in pairs:
        # Check strategy descriptions
        descriptions = list(pair.keys())
        vectors = list(pair.values())

        assert any("Sum Optimized Vector" in desc for desc in descriptions)
        assert any("Ratio Optimized Vector" in desc for desc in descriptions)

        # Check vectors
        assert all(isinstance(v, tuple) for v in vectors)
        assert all(len(v) == 3 for v in vectors)
        assert all(sum(v) == 100 for v in vectors)


def test_generated_pairs_are_valid(strategy):
    """Test if all generated pairs satisfy the complementary optimization properties."""
    user_vector = (60, 20, 20)
    pairs = strategy.generate_pairs(user_vector, n=10, vector_size=3)

    for pair in pairs:
        descriptions = list(pair.keys())
        vectors = list(pair.values())
        v1, v2 = vectors

        # Calculate optimization metrics
        metrics = strategy._calculate_optimization_metrics(user_vector, v1, v2)

        # Extract values from descriptions to verify matching
        sum_desc = next(desc for desc in descriptions if "Sum Optimized" in desc)
        ratio_desc = next(desc for desc in descriptions if "Ratio Optimized" in desc)

        sum_value = float(sum_desc.split("best: ")[1].split(",")[0])
        ratio_value = float(ratio_desc.split("best: ")[1].split(",")[0])

        # Verify that descriptions match actual metrics
        if sum_desc == descriptions[0]:  # First vector is sum-optimized
            assert abs(metrics[0] - sum_value) < 0.01  # sum diff for v1
            assert abs(metrics[3] - ratio_value) < 0.01  # ratio for v2
        else:  # Second vector is sum-optimized
            assert abs(metrics[1] - sum_value) < 0.01  # sum diff for v2
            assert abs(metrics[2] - ratio_value) < 0.01  # ratio for v1


def test_option_descriptions(strategy):
    """Test if option descriptions are generated correctly."""
    description_sum = strategy.get_option_description(
        metric_type="sum", best_value=25, worst_value=35
    )
    description_ratio = strategy.get_option_description(
        metric_type="ratio", best_value=0.75, worst_value=0.60
    )

    assert "Sum Optimized Vector" in description_sum
    assert "best: 25.00" in description_sum
    assert "worst: 35.00" in description_sum

    assert "Ratio Optimized Vector" in description_ratio
    assert "best: 0.75" in description_ratio
    assert "worst: 0.60" in description_ratio


def test_generate_pairs_error_handling(strategy):
    """Test if pair generation handles errors correctly."""
    invalid_vector = (0, 0, 0)
    with pytest.raises(ValueError):
        strategy.generate_pairs(invalid_vector, n=10, vector_size=3)


def test_edge_cases(strategy):
    """Test edge cases for optimization metrics."""
    # Test with extreme allocations
    user_vector = (90, 5, 5)
    pairs = strategy.generate_pairs(user_vector, n=5, vector_size=3)

    for pair in pairs:
        vectors = list(pair.values())
        # Verify vectors maintain valid ranges
        assert all(0 <= v <= 95 for vector in vectors for v in vector)
        # Verify sums remain correct
        assert all(sum(vector) == 100 for vector in vectors)


def test_vector_distinctness(strategy):
    """Test that generated vectors are distinct from user vector."""
    user_vector = (40, 30, 30)
    pairs = strategy.generate_pairs(user_vector, n=5, vector_size=3)

    for pair in pairs:
        vectors = list(pair.values())
        assert all(v != user_vector for v in vectors)


def test_metric_value_extraction(strategy):
    """Test extraction of metric values from descriptions."""
    user_vector = (50, 25, 25)
    pairs = strategy.generate_pairs(user_vector, n=1, vector_size=3)
    pair = pairs[0]

    descriptions = list(pair.keys())
    sum_desc = next(desc for desc in descriptions if "Sum Optimized" in desc)
    ratio_desc = next(desc for desc in descriptions if "Ratio Optimized" in desc)

    # Extract best values from the new format
    sum_value = float(sum_desc.split("best: ")[1].split(",")[0])
    ratio_value = float(ratio_desc.split("best: ")[1].split(",")[0])

    assert sum_value > 0, "Sum difference should be positive"
    assert 0 < ratio_value <= 1, "Ratio should be between 0 and 1"


def test_pair_generation_consistency(strategy):
    """Test that pair generation is consistent with the same input."""
    user_vector = (45, 35, 20)
    pairs1 = strategy.generate_pairs(user_vector, n=5, vector_size=3)
    pairs2 = strategy.generate_pairs(user_vector, n=5, vector_size=3)

    # While vectors might be different (due to randomness),
    # verify that structure and constraints are consistent
    assert len(pairs1) == len(pairs2) == 5

    for pair1, pair2 in zip(pairs1, pairs2):
        # Check structure consistency
        assert len(pair1) == len(pair2) == 2
        # Check description format consistency
        assert all(
            "Sum Optimized Vector" in desc
            for pair in [pair1, pair2]
            for desc in pair.keys()
            if "Sum" in desc
        )
        assert all(
            "Ratio Optimized Vector" in desc
            for pair in [pair1, pair2]
            for desc in pair.keys()
            if "Ratio" in desc
        )
