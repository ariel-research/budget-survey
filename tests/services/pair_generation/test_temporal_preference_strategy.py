"""
Tests for TemporalPreferenceStrategy pair generation.

This module tests the temporal preference strategy that generates pairs
comparing user's ideal vector against random vectors to test temporal
discounting preferences.
"""

from unittest.mock import patch

import pytest

from application.services.pair_generation.temporal_preference_strategy import (
    TemporalPreferenceStrategy,
)


@pytest.fixture
def strategy():
    """Create a TemporalPreferenceStrategy instance for testing."""
    return TemporalPreferenceStrategy()


def test_strategy_name(strategy):
    """Test that strategy returns correct name identifier."""
    assert strategy.get_strategy_name() == "temporal_preference_test"


def test_option_labels(strategy):
    """Test that strategy returns correct option labels."""
    labels = strategy.get_option_labels()
    assert labels == ("Ideal This Year", "Ideal Next Year")


def test_get_metric_name(strategy):
    """Test metric name retrieval."""
    assert strategy._get_metric_name("consistency") == "Temporal Consistency"
    assert strategy._get_metric_name("ideal_this_year") == "Ideal This Year Preference"
    assert strategy._get_metric_name("ideal_next_year") == "Ideal Next Year Preference"
    assert strategy._get_metric_name("unknown_metric") == "Unknown Metric"


def test_get_table_columns(strategy):
    """Test table column definitions for temporal preference analysis."""
    columns = strategy.get_table_columns()

    assert "ideal_this_year" in columns
    assert "ideal_next_year" in columns

    assert columns["ideal_this_year"]["name"] == "Ideal This Year (%)"
    assert columns["ideal_next_year"]["name"] == "Ideal Next Year (%)"

    # Check all columns are marked as percentage type and highlighted
    for col in columns.values():
        assert col["type"] == "percentage"
        assert col["highlight"] is True

    # Ensure we only have the expected 2 columns
    assert len(columns) == 2


def test_is_ranking_based(strategy):
    """Test that strategy is not ranking-based."""
    assert strategy.is_ranking_based() is False


def test_generate_pairs_default_parameters(strategy):
    """Test pair generation with default parameters."""
    user_vector = (60, 25, 15)
    pairs = strategy.generate_pairs(user_vector)

    # Default should generate 10 pairs
    assert len(pairs) == 10

    # Each pair should have the correct structure
    for pair in pairs:
        assert len(pair) == 2
        assert "Ideal This Year" in pair
        assert "Ideal Next Year" in pair

        # Option 1 should always be the user's ideal vector
        assert pair["Ideal This Year"] == user_vector

        # Option 2 should be different from user vector
        assert pair["Ideal Next Year"] != user_vector

        # Option 2 should be a valid vector (sum to 100)
        assert sum(pair["Ideal Next Year"]) == 100


def test_generate_pairs_custom_parameters(strategy):
    """Test pair generation with custom parameters."""
    user_vector = (40, 30, 30)
    n = 5
    vector_size = 3

    pairs = strategy.generate_pairs(user_vector, n=n, vector_size=vector_size)

    # Should generate exactly n pairs
    assert len(pairs) == n

    # Verify structure
    for pair in pairs:
        assert pair["Ideal This Year"] == user_vector
        assert len(pair["Ideal Next Year"]) == vector_size
        assert sum(pair["Ideal Next Year"]) == 100


def test_generate_pairs_uniqueness(strategy):
    """Test that generated random vectors are unique."""
    user_vector = (50, 30, 20)
    pairs = strategy.generate_pairs(user_vector, n=10)

    # Extract all Option 2 vectors (random vectors)
    random_vectors = [pair["Ideal Next Year"] for pair in pairs]

    # All random vectors should be unique
    assert len(set(random_vectors)) == len(random_vectors)

    # None should match the user vector
    for vec in random_vectors:
        assert vec != user_vector


def test_generate_pairs_vector_validation(strategy):
    """Test that all generated vectors are valid."""
    user_vector = (80, 10, 10)
    pairs = strategy.generate_pairs(user_vector, n=10)

    for pair in pairs:
        option2_vector = pair["Ideal Next Year"]

        # Vector should sum to 100
        assert sum(option2_vector) == 100

        # All values should be non-negative and <= 100
        for value in option2_vector:
            assert 0 <= value <= 100

        # Values should be divisible by 5 (per create_random_vector logic)
        for value in option2_vector:
            assert value % 5 == 0


def test_generate_pairs_invalid_user_vector(strategy):
    """Test error handling for invalid user vectors."""
    # Test invalid sum
    with pytest.raises(ValueError, match="Vector must sum to 100"):
        strategy.generate_pairs((50, 30, 30))  # sums to 110

    # Test negative values
    with pytest.raises(ValueError, match="Vector values must be between 0 and 100"):
        strategy.generate_pairs((-10, 60, 50))

    # Test values over 100
    with pytest.raises(ValueError, match="Vector values must be between 0 and 100"):
        strategy.generate_pairs((110, -5, -5))

    # Test wrong size
    with pytest.raises(ValueError, match="Vector must have length 3"):
        strategy.generate_pairs((50, 50))  # only 2 elements


def test_generate_pairs_invalid_n(strategy):
    """Test error handling for invalid n parameter."""
    user_vector = (60, 25, 15)

    # Test n <= 0
    with pytest.raises(ValueError, match="Number of pairs must be positive"):
        strategy.generate_pairs(user_vector, n=0)

    with pytest.raises(ValueError, match="Number of pairs must be positive"):
        strategy.generate_pairs(user_vector, n=-1)

    # Test n > 50 (upper limit)
    with pytest.raises(ValueError, match="Number of pairs must not exceed 50"):
        strategy.generate_pairs(user_vector, n=51)


def test_generate_unique_random_vectors(strategy):
    """Test the internal method for generating unique random vectors."""
    user_vector = (60, 25, 15)
    n = 8
    vector_size = 3

    unique_vectors = strategy._generate_unique_random_vectors(
        user_vector, n, vector_size
    )

    # Should return exactly n vectors
    assert len(unique_vectors) == n

    # All vectors should be unique
    assert len(set(unique_vectors)) == n

    # None should match user vector
    for vec in unique_vectors:
        assert vec != user_vector
        assert sum(vec) == 100  # Valid vectors


def test_generate_unique_random_vectors_insufficient_unique(strategy):
    """Test handling when insufficient unique vectors can be generated."""
    # Use a mock to simulate create_random_vector returning same vector repeatedly
    user_vector = (60, 25, 15)

    # Mock create_random_vector to always return user_vector or a very limited set
    # This should trigger the ValueError for insufficient unique vectors
    with patch.object(strategy, "create_random_vector") as mock_create:
        mock_create.return_value = user_vector  # Always return user vector

        with pytest.raises(
            ValueError, match="Unable to generate .* unique random vectors"
        ):
            strategy._generate_unique_random_vectors(user_vector, 5, 3)


def test_pairs_structure_consistency(strategy):
    """Test that pair structure is consistent across multiple calls."""
    user_vector = (45, 35, 20)

    # Generate pairs multiple times
    pairs1 = strategy.generate_pairs(user_vector, n=5)
    pairs2 = strategy.generate_pairs(user_vector, n=5)

    # Structure should be consistent (though content will differ due to randomness)
    assert len(pairs1) == len(pairs2) == 5

    for p1, p2 in zip(pairs1, pairs2):
        # Both should have same keys
        assert set(p1.keys()) == set(p2.keys())

        # Both should have user vector as Option 1
        assert p1["Ideal This Year"] == user_vector
        assert p2["Ideal This Year"] == user_vector


def test_edge_case_extreme_user_vectors(strategy):
    """Test strategy with extreme but valid user vectors."""
    extreme_vectors = [
        (100, 0, 0),  # All in one category
        (0, 100, 0),  # All in another category
        (0, 0, 100),  # All in third category
        (5, 5, 90),  # Minimal diversity
        (90, 5, 5),  # High concentration
    ]

    for user_vector in extreme_vectors:
        pairs = strategy.generate_pairs(user_vector, n=5)

        assert len(pairs) == 5

        for pair in pairs:
            assert pair["Ideal This Year"] == user_vector
            assert pair["Ideal Next Year"] != user_vector
            assert sum(pair["Ideal Next Year"]) == 100


@patch("application.services.pair_generation.temporal_preference_strategy.logger")
def test_logging_behavior(mock_logger, strategy):
    """Test that strategy logs appropriately."""
    user_vector = (60, 25, 15)

    strategy.generate_pairs(user_vector, n=3)

    # Check that info logs were called
    mock_logger.info.assert_any_call("Generating 3 temporal preference pairs")
    mock_logger.info.assert_any_call(
        "Successfully generated 3 temporal preference pairs"
    )


def test_vector_size_parameter(strategy):
    """Test that vector_size parameter works correctly."""
    user_vector = (60, 25, 15)
    vector_size = 3

    pairs = strategy.generate_pairs(user_vector, n=5, vector_size=vector_size)

    for pair in pairs:
        assert len(pair["Ideal This Year"]) == vector_size
        assert len(pair["Ideal Next Year"]) == vector_size


def test_large_n_value(strategy):
    """Test strategy with larger n values within limits."""
    user_vector = (50, 30, 20)
    n = 20  # Still within the 50 limit

    pairs = strategy.generate_pairs(user_vector, n=n)

    assert len(pairs) == n

    # All random vectors should still be unique
    random_vectors = [pair["Ideal Next Year"] for pair in pairs]
    assert len(set(random_vectors)) == len(random_vectors)
