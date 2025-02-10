"""Test suite for root sum squared vs minimal ratio strategy."""

import pytest

from application.services.pair_generation import RootSumSquaredRatioStrategy


@pytest.fixture
def strategy():
    return RootSumSquaredRatioStrategy()


def test_strategy_name(strategy):
    """Test if strategy name is correct."""
    assert strategy.get_strategy_name() == "root_sum_squared_ratio"


def test_get_metric_types(strategy):
    """Test if metric types are correctly defined."""
    metric_type1, metric_type2 = strategy.get_metric_types()
    assert metric_type1 == "rss"
    assert metric_type2 == "ratio"


def test_root_sum_squared_differences(strategy):
    """Test if root sum squared differences calculation is correct."""
    user_vector = (60, 25, 15)
    comparison_vector = (50, 30, 20)

    # Expected: sqrt((60-50)² + (25-30)² + (15-20)²)
    # = sqrt(100 + 25 + 25) = sqrt(150) ≈ 12.25
    result = strategy.root_sum_squared_differences(user_vector, comparison_vector)
    assert round(result, 2) == 12.25


def test_calculate_optimization_metrics(strategy):
    """Test if optimization metrics are calculated correctly."""
    user_vector = (60, 25, 15)
    v1 = (50, 30, 20)  # Better minimal ratio
    v2 = (65, 25, 10)  # Better root sum squared

    rss1, rss2, ratio1, ratio2 = strategy._calculate_optimization_metrics(
        user_vector, v1, v2
    )

    # v1 metrics
    assert round(rss1, 2) == 12.25  # sqrt(100 + 25 + 25)
    assert round(ratio1, 2) == 0.83  # min(50/60, 30/25, 20/15)

    # v2 metrics
    assert round(rss2, 2) == 7.07  # sqrt(25 + 0 + 25)
    assert round(ratio2, 2) == 0.67  # min(65/60, 25/25, 10/15)


def test_is_valid_pair(strategy):
    """Test if pair validation logic works correctly."""
    metrics_valid = (10.0, 15.0, 0.7, 0.8)  # First better in RSS, worse in ratio
    metrics_invalid = (10.0, 15.0, 0.8, 0.7)  # First better in both

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
        # Check strategy descriptions
        descriptions = list(pair.keys())
        vectors = list(pair.values())

        # Check for correct metric descriptions
        assert any("Root Sum Squared Optimized Vector" in desc for desc in descriptions)
        assert any("Ratio Optimized Vector" in desc for desc in descriptions)

        # Verify each description includes a value
        assert all(":" in desc for desc in descriptions)

        # Check vectors
        assert all(isinstance(v, tuple) for v in vectors)
        assert all(len(v) == 3 for v in vectors)
        assert all(sum(v) == 100 for v in vectors)
        assert all(all(0 <= x <= 95 for x in v) for v in vectors)


def test_option_descriptions(strategy):
    """Test if option descriptions are generated correctly."""
    desc_rss = strategy.get_option_description(metric_type="rss", value=15.5)
    desc_ratio = strategy.get_option_description(metric_type="ratio", value=0.75)

    assert desc_rss == "Root Sum Squared Optimized Vector: 15.50"
    assert desc_ratio == "Ratio Optimized Vector: 0.75"

    labels = strategy.get_option_labels()
    assert labels == ("Root Sum Squared Optimized Vector", "Ratio Optimized Vector")


def test_pair_optimization_properties(strategy):
    """Test if generated pairs have proper optimization properties."""
    user_vector = (40, 35, 25)
    pairs = strategy.generate_pairs(user_vector, n=3, vector_size=3)

    for pair in pairs:
        vectors = list(pair.values())
        v1, v2 = vectors

        # Calculate metrics
        rss1 = strategy.root_sum_squared_differences(user_vector, v1)
        rss2 = strategy.root_sum_squared_differences(user_vector, v2)
        ratio1 = strategy.minimal_ratio(user_vector, v1)
        ratio2 = strategy.minimal_ratio(user_vector, v2)

        # Verify either: v1 better in RSS and worse in ratio, or vice versa
        valid_combination = (rss1 < rss2 and ratio1 < ratio2) or (
            rss2 < rss1 and ratio2 < ratio1
        )
        assert valid_combination, "Pair does not show valid optimization trade-off"


def test_error_handling(strategy):
    """Test if error handling works correctly."""
    invalid_vector = (0, 0, 0)
    with pytest.raises(ValueError):
        strategy.generate_pairs(invalid_vector, n=5, vector_size=3)

    # Test with invalid vector size
    with pytest.raises(ValueError):
        strategy.generate_pairs((50, 50), n=5, vector_size=3)


def test_ratio_with_zero_components(strategy):
    """Test ratio calculation handles vectors with zero components properly."""
    user_vector = (60, 25, 15)
    comparison_vector = (50, 30, 20)

    ratio = strategy.minimal_ratio(user_vector, comparison_vector)
    assert 0 < ratio <= 1  # Ratio should be positive and not exceed 1

    # Edge case with zeros - should handle division by zero gracefully
    user_vector_with_zero = (60, 0, 40)
    comparison_vector_with_zero = (50, 0, 50)

    ratio = strategy.minimal_ratio(user_vector_with_zero, comparison_vector_with_zero)
    assert 0 < ratio <= 1  # Should still maintain valid ratio range
