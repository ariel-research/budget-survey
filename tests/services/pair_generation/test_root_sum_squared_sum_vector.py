"""Test suite for root sum squared vs sum differences strategy."""

import pytest

from application.services.pair_generation import RootSumSquaredSumStrategy


@pytest.fixture
def strategy():
    return RootSumSquaredSumStrategy()


def test_strategy_name(strategy):
    """Test if strategy name is correct."""
    assert strategy.get_strategy_name() == "root_sum_squared_sum"


def test_root_sum_squared_differences(strategy):
    """Test if root sum squared differences calculation is correct."""
    user_vector = (50, 30, 20)
    comparison_vector = (40, 40, 20)

    # Expected: sqrt((50-40)² + (30-40)² + (20-20)²)
    # = sqrt(100 + 100 + 0) = sqrt(200) ≈ 14.14
    result = strategy.root_sum_squared_differences(user_vector, comparison_vector)
    assert round(result, 2) == 14.14


def test_calculate_optimization_metrics(strategy):
    """Test if optimization metrics are calculated correctly."""
    user_vector = (60, 20, 20)
    v1 = (50, 25, 25)  # Better root sum squared
    v2 = (70, 15, 15)  # Better sum of differences

    rss1, rss2, sum1, sum2 = strategy._calculate_optimization_metrics(
        user_vector, v1, v2
    )

    # v1 metrics
    assert round(rss1, 2) == 12.25  # sqrt(100 + 25 + 25)
    assert sum1 == 20  # |60-50| + |20-25| + |20-25|

    # v2 metrics
    assert round(rss2, 2) == 12.25  # sqrt(100 + 25 + 25)
    assert sum2 == 20  # |60-70| + |20-15| + |20-15|


def test_is_valid_pair(strategy):
    """Test if pair validation logic works correctly."""
    metrics_valid = (10.0, 15.0, 25, 20)  # First better in RSS, second better in sum
    metrics_invalid = (10.0, 15.0, 20, 25)  # First better in both

    assert strategy._is_valid_pair(metrics_valid)
    assert not strategy._is_valid_pair(metrics_invalid)


def test_generate_pairs(strategy):
    """Test if pair generation works correctly."""
    user_vector = (50, 25, 25)
    pairs = strategy.generate_pairs(user_vector, n=10, vector_size=3)

    assert len(pairs) == 10
    assert all(isinstance(pair, dict) for pair in pairs)
    assert all(len(pair) == 2 for pair in pairs)

    for pair in pairs:
        print(f"*** pair: {pair} ***")
        # Check strategy descriptions
        descriptions = list(pair.keys())
        vectors = list(pair.values())

        descs = [desc for desc in descriptions]
        print(f"*** Descriptions: {descs} ***")

        assert any("Root Sum Squared Optimized Vector" in desc for desc in descriptions)
        assert any("Sum Optimized Vector" in desc for desc in descriptions)

        # Check vectors
        assert all(isinstance(v, tuple) for v in vectors)
        assert all(len(v) == 3 for v in vectors)
        assert all(sum(v) == 100 for v in vectors)
        assert all(all(0 <= x <= 95 for x in v) for v in vectors)


def test_option_descriptions(strategy):
    """Test if option descriptions are generated correctly."""
    desc_rss = strategy.get_option_description(metric_type="rss", value=15.5)
    desc_sum = strategy.get_option_description(metric_type="sum", value=25)

    assert desc_rss == "Root Sum Squared Optimized Vector: 15.50"
    assert desc_sum == "Sum Optimized Vector: 25"

    labels = strategy.get_option_labels()
    assert labels == ("Root Sum Squared Optimized Vector", "Sum Optimized Vector")


def test_pair_optimization_properties(strategy):
    """Test if generated pairs have proper optimization properties."""
    user_vector = (40, 35, 25)
    pairs = strategy.generate_pairs(user_vector, n=3, vector_size=3)

    for pair in pairs:
        vectors = list(pair.values())
        _descriptions = list(pair.keys())
        v1, v2 = vectors

        # Calculate metrics
        rss1 = strategy.root_sum_squared_differences(user_vector, v1)
        rss2 = strategy.root_sum_squared_differences(user_vector, v2)
        sum1 = strategy.sum_of_differences(user_vector, v1)
        sum2 = strategy.sum_of_differences(user_vector, v2)

        # Verify either: v1 better in RSS and v2 better in sum, or vice versa
        valid_combination = (rss1 < rss2 and sum1 > sum2) or (
            rss2 < rss1 and sum2 > sum1
        )
        assert valid_combination


def test_error_handling(strategy):
    """Test if error handling works correctly."""
    invalid_vector = (0, 0, 0)
    with pytest.raises(ValueError):
        strategy.generate_pairs(invalid_vector, n=5, vector_size=3)

    # Test with invalid vector size
    with pytest.raises(ValueError):
        strategy.generate_pairs((50, 50), n=5, vector_size=3)
