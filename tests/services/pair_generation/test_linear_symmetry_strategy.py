"""Test suite for linear symmetry strategy."""

from unittest.mock import patch

import numpy as np
import pytest

from application.exceptions import UnsuitableForStrategyError
from application.services.pair_generation import LinearSymmetryStrategy


@pytest.fixture
def strategy():
    return LinearSymmetryStrategy()


def test_strategy_name(strategy):
    """Test if strategy name is correct."""
    assert strategy.get_strategy_name() == "linear_symmetry"


def test_generate_distance_vectors(strategy):
    """Test if distance vector generation works correctly."""
    user_vector = (20, 30, 50)
    vector_size = 3

    v1, v2 = strategy._generate_distance_vectors(user_vector, vector_size)

    # Check that vectors are numpy arrays
    assert isinstance(v1, np.ndarray)
    assert isinstance(v2, np.ndarray)
    assert len(v1) == vector_size
    assert len(v2) == vector_size

    # Check that vectors sum to zero
    assert np.sum(v1) == 0
    assert np.sum(v2) == 0

    # Check that vectors are different
    assert not np.array_equal(v1, v2)

    # Check that neither is all zeros
    assert not np.all(v1 == 0)
    assert not np.all(v2 == 0)

    # Check that both addition and subtraction produce valid vectors
    user_array = np.array(user_vector)

    vec1_plus = user_array + v1
    vec1_minus = user_array - v1
    vec2_plus = user_array + v2
    vec2_minus = user_array - v2

    # All resulting vectors should be valid
    for vec in [vec1_plus, vec1_minus, vec2_plus, vec2_minus]:
        assert np.all(vec >= 0)
        assert np.all(vec <= 100)
        assert np.sum(vec) == 100


def test_generate_group(strategy):
    """Test if group generation works correctly."""
    user_vector = (20, 30, 50)
    vector_size = 3
    group_num = 1

    group_pairs = strategy._generate_group(user_vector, vector_size, group_num)

    # Should generate 2 pairs
    assert len(group_pairs) == 2

    # Each pair should be a dictionary with 4 entries (2 vectors + 2 distances)
    for pair in group_pairs:
        assert isinstance(pair, dict)
        assert len(pair) == 4

        # Check that distance vectors are present
        assert "distance_v1" in pair
        assert "distance_v2" in pair

        # Check that keys contain linear pattern information
        keys = list(pair.keys())
        linear_keys = [key for key in keys if "Linear Pattern" in key]
        assert len(linear_keys) == 2

        # Check that values are valid tuples (skip distances)
        for key, vector in pair.items():
            if not key.startswith("distance_"):
                assert isinstance(vector, tuple)
                assert len(vector) == vector_size
                assert sum(vector) == 100
                assert all(0 <= v <= 100 for v in vector)


def test_generate_pairs_success(strategy):
    """Test successful pair generation."""
    user_vector = (20, 30, 50)
    pairs = strategy.generate_pairs(user_vector, n=12, vector_size=3)

    # Should generate exactly 12 pairs
    assert len(pairs) == 12

    # Each pair should be a dictionary with 4 entries
    for pair in pairs:
        assert isinstance(pair, dict)
        assert len(pair) == 4

        # Check that distance vectors are present
        assert "distance_v1" in pair
        assert "distance_v2" in pair
        assert isinstance(pair["distance_v1"], list)
        assert isinstance(pair["distance_v2"], list)
        assert len(pair["distance_v1"]) == 3
        assert len(pair["distance_v2"]) == 3

        # Check that all vectors are valid (skip the distance keys)
        for key, vector in pair.items():
            if not key.startswith("distance_"):
                assert isinstance(vector, tuple)
                assert len(vector) == 3
                assert sum(vector) == 100
                assert all(0 <= v <= 100 for v in vector)


def test_generate_pairs_with_zero_values(strategy):
    """Test that strategy raises UnsuitableForStrategyError for zero values."""
    user_vector_with_zero = (0, 50, 50)

    with pytest.raises(UnsuitableForStrategyError) as exc_info:
        strategy.generate_pairs(user_vector_with_zero, n=12, vector_size=3)

    assert "zero values" in str(exc_info.value)


def test_generate_pairs_error_handling(strategy):
    """Test error handling for invalid inputs."""
    # Test with invalid vector sum
    invalid_vector = (30, 30, 30)
    with pytest.raises(ValueError):
        strategy.generate_pairs(invalid_vector, n=12, vector_size=3)

    # Test with invalid vector size
    invalid_size_vector = (50, 50)
    with pytest.raises(ValueError):
        strategy.generate_pairs(invalid_size_vector, n=12, vector_size=3)


def test_pair_uniqueness(strategy):
    """Test that generated pairs are unique."""
    user_vector = (25, 35, 40)
    pairs = strategy.generate_pairs(user_vector, n=12, vector_size=3)

    # Convert pairs to a set of sorted tuples for uniqueness check
    pair_sets = set()
    for pair in pairs:
        # Only consider the actual vector values, not the distance metadata
        vectors = tuple(
            sorted([v for k, v in pair.items() if not k.startswith("distance_")])
        )
        pair_sets.add(vectors)

    # All pairs should be unique
    assert len(pair_sets) == len(pairs)


def test_linear_symmetry_pattern(strategy):
    """Test that linear symmetry patterns are correctly generated."""
    user_vector = (30, 30, 40)

    # Generate a single group to test symmetry
    group_pairs = strategy._generate_group(user_vector, 3, 1)

    if len(group_pairs) == 2:  # Only test if we got a full group
        # Extract the pattern types
        patterns = []
        for pair in group_pairs:
            for key in pair.keys():
                if "Linear Pattern" in key:
                    if "+" in key:
                        patterns.append("positive")
                    elif "-" in key:
                        patterns.append("negative")

        # Should have both positive and negative patterns
        assert "positive" in patterns
        assert "negative" in patterns


@patch("application.services.pair_generation.linear_symmetry_strategy.get_translation")
def test_option_labels(mock_get_translation, strategy):
    """Test if option labels are generated correctly."""
    mock_get_translation.side_effect = lambda key, *args, **kwargs: {
        "linear_positive": "Linear Positive",
        "linear_negative": "Linear Negative",
    }.get(key, key)

    labels = strategy.get_option_labels()
    assert labels == ("Linear Positive", "Linear Negative")


def test_table_columns(strategy):
    """Test if table columns are defined correctly."""
    columns = strategy.get_table_columns()

    assert isinstance(columns, dict)
    assert "linear_consistency" in columns

    # Check column properties
    column_def = columns["linear_consistency"]
    assert "name" in column_def
    assert "type" in column_def
    assert column_def["type"] == "percentage"
    assert column_def.get("highlight") is True


def test_multiples_of_five_constraint(strategy):
    """Test that vectors respect multiples of 5 constraint when appropriate."""
    # User vector without 5 should produce multiples of 5
    user_vector = (20, 30, 50)
    pairs = strategy.generate_pairs(user_vector, n=12, vector_size=3)

    for pair in pairs:
        for key, vector in pair.items():
            if not key.startswith("distance_"):  # Skip distance metadata
                assert all(
                    v % 5 == 0 for v in vector
                ), f"Vector {vector} contains non-multiples of 5"

    # User vector with 5 should allow non-multiples
    user_vector_with_five = (25, 30, 45)
    pairs_with_five = strategy.generate_pairs(
        user_vector_with_five, n=12, vector_size=3
    )

    # Should still generate valid pairs (may or may not be multiples of 5)
    assert len(pairs_with_five) == 12
    for pair in pairs_with_five:
        for key, vector in pair.items():
            if not key.startswith("distance_"):  # Skip distance metadata
                assert sum(vector) == 100
                assert all(0 <= v <= 100 for v in vector)


def test_edge_case_vectors(strategy):
    """Test strategy with edge case user vectors."""
    # Test with extreme distributions
    extreme_vector = (5, 5, 90)
    pairs = strategy.generate_pairs(extreme_vector, n=12, vector_size=3)
    assert len(pairs) == 12

    # Test with equal distribution
    equal_vector = (33, 33, 34)  # Closest to equal that sums to 100
    pairs = strategy.generate_pairs(equal_vector, n=12, vector_size=3)
    assert len(pairs) == 12


def test_logging_behavior(strategy, caplog):
    """Test that appropriate logging occurs."""
    user_vector = (20, 30, 50)

    with caplog.at_level("INFO"):
        strategy.generate_pairs(user_vector, n=12, vector_size=3)

    # Should log successful generation
    assert any("Generated" in record.message for record in caplog.records)
    assert any("LinearSymmetryStrategy" in record.message for record in caplog.records)


def test_zero_value_logging(strategy, caplog):
    """Test logging when zero values are detected."""
    user_vector_with_zero = (0, 40, 60)

    with caplog.at_level("INFO"):
        with pytest.raises(UnsuitableForStrategyError):
            strategy.generate_pairs(user_vector_with_zero, n=12, vector_size=3)

    # Should log the zero value detection
    assert any("zero values" in record.message for record in caplog.records)


def test_distance_vector_constraints(strategy):
    """Test that distance vectors satisfy all constraints."""
    user_vector = (20, 30, 50)
    vector_size = 3

    # Generate multiple pairs to check constraints
    for _ in range(5):
        v1, v2 = strategy._generate_distance_vectors(user_vector, vector_size)

        # Both vectors should sum to zero
        assert np.sum(v1) == 0
        assert np.sum(v2) == 0

        # Neither should be all zeros
        assert not np.all(v1 == 0)
        assert not np.all(v2 == 0)

        # They should be different
        assert not np.array_equal(v1, v2)

        # At least one element should be meaningful (>=5)
        assert any(abs(d) >= 5 for d in v1)
        assert any(abs(d) >= 5 for d in v2)


def test_symmetry_hypothesis(strategy):
    """Test that the symmetry hypothesis is correctly implemented."""
    user_vector = (40, 30, 30)
    user_array = np.array(user_vector)

    # Generate distance vectors
    v1, v2 = strategy._generate_distance_vectors(user_vector, 3)

    # Test positive distance pair: (ideal + v1) vs (ideal + v2)
    pos_a = user_array + v1
    pos_b = user_array + v2

    # Test negative distance pair: (ideal - v1) vs (ideal - v2)
    neg_a = user_array - v1
    neg_b = user_array - v2

    # All should be valid budget allocations
    for vec in [pos_a, pos_b, neg_a, neg_b]:
        assert np.all(vec >= 0)
        assert np.all(vec <= 100)
        assert abs(np.sum(vec) - 100) < 1e-10  # Account for floating point


def test_group_generation_reliability(strategy):
    """Test that group generation is reliable and doesn't fail often."""
    user_vector = (25, 35, 40)
    successful_groups = 0

    # Try to generate 10 groups
    for group_num in range(1, 11):
        group_pairs = strategy._generate_group(user_vector, 3, group_num)
        if len(group_pairs) == 2:
            successful_groups += 1

    # Should succeed in generating most groups
    assert successful_groups >= 8  # Allow some failures but expect mostly success
