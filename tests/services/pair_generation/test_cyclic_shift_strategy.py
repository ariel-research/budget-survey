"""Test suite for cyclic shift strategy."""

from unittest.mock import patch

import numpy as np
import pytest

from application.exceptions import UnsuitableForStrategyError
from application.services.pair_generation import CyclicShiftStrategy


@pytest.fixture
def strategy():
    return CyclicShiftStrategy()


def test_strategy_name(strategy):
    """Test if strategy name is correct."""
    assert strategy.get_strategy_name() == "cyclic_shift"


def test_generate_random_differences(strategy):
    """Test if random difference generation works correctly."""
    user_vector = (20, 30, 50)
    vector_size = 3

    diff1, diff2 = strategy._generate_random_differences(user_vector, vector_size)

    # Check that differences are numpy arrays
    assert isinstance(diff1, np.ndarray)
    assert isinstance(diff2, np.ndarray)
    assert len(diff1) == vector_size
    assert len(diff2) == vector_size

    # Check that differences sum to zero
    assert np.sum(diff1) == 0
    assert np.sum(diff2) == 0

    # Check that resulting vectors are valid
    user_array = np.array(user_vector)
    vec1 = user_array + diff1
    vec2 = user_array + diff2

    assert np.all(vec1 >= 0)
    assert np.all(vec1 <= 100)
    assert np.all(vec2 >= 0)
    assert np.all(vec2 <= 100)
    assert np.sum(vec1) == 100
    assert np.sum(vec2) == 100


def test_apply_cyclic_shift(strategy):
    """Test if cyclic shift works correctly."""
    differences = np.array([10, -5, -5])

    # Test shift by 0 (no change)
    shifted_0 = strategy._apply_cyclic_shift(differences, 0)
    np.testing.assert_array_equal(shifted_0, [10, -5, -5])

    # Test shift by 1 (right shift)
    shifted_1 = strategy._apply_cyclic_shift(differences, 1)
    np.testing.assert_array_equal(shifted_1, [-5, 10, -5])

    # Test shift by 2 (right shift by 2)
    shifted_2 = strategy._apply_cyclic_shift(differences, 2)
    np.testing.assert_array_equal(shifted_2, [-5, -5, 10])


def test_verify_differences(strategy):
    """Test if difference verification works correctly."""
    user_vector = (20, 30, 50)

    # Valid differences
    valid_diff1 = np.array([10, -5, -5])
    valid_diff2 = np.array([-10, 5, 5])
    assert strategy._verify_differences(user_vector, valid_diff1, valid_diff2)

    # Invalid differences (would create negative values)
    invalid_diff1 = np.array([-25, 0, 25])
    invalid_diff2 = np.array([25, 0, -25])
    assert not strategy._verify_differences(user_vector, invalid_diff1, invalid_diff2)

    # Invalid differences (would create values > 100)
    invalid_diff1 = np.array([60, 0, -60])
    invalid_diff2 = np.array([-60, 0, 60])
    assert not strategy._verify_differences(user_vector, invalid_diff1, invalid_diff2)


def test_generate_group(strategy):
    """Test if group generation works correctly."""
    user_vector = (20, 30, 50)
    vector_size = 3
    group_num = 1

    group_pairs = strategy._generate_group(user_vector, vector_size, group_num)

    # Should generate 3 pairs
    assert len(group_pairs) == 3

    # Each pair should be a dictionary with 2 entries
    for pair in group_pairs:
        assert isinstance(pair, dict)
        assert len(pair) == 2

        # Check that keys contain shift information
        keys = list(pair.keys())
        assert any("shift" in key for key in keys)

        # Check that values are valid tuples
        for vector in pair.values():
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

    # Each pair should be a dictionary
    for pair in pairs:
        assert isinstance(pair, dict)
        assert len(pair) == 2

        # Check that all vectors are valid
        for vector in pair.values():
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
        vectors = tuple(sorted(pair.values()))
        pair_sets.add(vectors)

    # All pairs should be unique
    assert len(pair_sets) == len(pairs)


def test_cyclic_pattern_consistency(strategy):
    """Test that cyclic patterns are consistent within groups."""
    user_vector = (30, 30, 40)

    # Generate a single group to test pattern consistency
    group_pairs = strategy._generate_group(user_vector, 3, 1)

    if len(group_pairs) == 3:  # Only test if we got a full group
        # Extract shift amounts from descriptions
        shifts = []
        for pair in group_pairs:
            for key in pair.keys():
                if "shift" in key:
                    # Extract shift number from key
                    after_shift = key.split("shift ")[1]
                    parts = after_shift.split(")")[0]
                    shift_num = int(parts)
                    shifts.append(shift_num)
                    break

        # Should have shifts 0, 1, 2
        assert sorted(set(shifts)) == [0, 1, 2]


@patch("application.services.pair_generation.cyclic_shift_strategy.get_translation")
def test_option_labels(mock_get_translation, strategy):
    """Test if option labels are generated correctly."""
    mock_get_translation.side_effect = lambda key, *args, **kwargs: {
        "cyclic_pattern_a": "Pattern A",
        "cyclic_pattern_b": "Pattern B",
    }.get(key, key)

    labels = strategy.get_option_labels()
    assert labels == ("Pattern A", "Pattern B")


def test_table_columns(strategy):
    """Test if table columns are defined correctly."""
    columns = strategy.get_table_columns()

    assert isinstance(columns, dict)
    assert "pattern_a_preference" in columns
    assert "pattern_b_preference" in columns

    # Check column properties
    for column_key, column_def in columns.items():
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
        for vector in pair.values():
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
        for vector in pair.values():
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
    assert any("CyclicShiftStrategy" in record.message for record in caplog.records)


def test_zero_value_logging(strategy, caplog):
    """Test logging when zero values are detected."""
    user_vector_with_zero = (0, 40, 60)

    with caplog.at_level("INFO"):
        with pytest.raises(UnsuitableForStrategyError):
            strategy.generate_pairs(user_vector_with_zero, n=12, vector_size=3)

    # Should log the zero value detection
    assert any("zero values" in record.message for record in caplog.records)


def test_generate_random_differences_independence(strategy):
    """Test that the two difference vectors are generated independently."""
    user_vector = (20, 30, 50)
    vector_size = 3

    # Generate multiple pairs to check independence
    pairs_generated = []
    for _ in range(5):
        diff1, diff2 = strategy._generate_random_differences(user_vector, vector_size)

        # Check that differences sum to zero
        assert np.sum(diff1) == 0
        assert np.sum(diff2) == 0

        # Check that they're canonically different
        sorted_diff1 = np.sort(diff1)
        sorted_diff2 = np.sort(diff2)
        assert not np.array_equal(
            sorted_diff1, sorted_diff2
        ), f"Difference vectors have same pattern: {diff1} and {diff2}"

        # Store for uniqueness check
        pairs_generated.append((tuple(diff1), tuple(diff2)))

    # Check that we're getting different pairs (not always the same)
    unique_pairs = set(pairs_generated)
    assert len(unique_pairs) > 1, "Always generating the same difference pairs"


def test_generate_random_differences_canonical_difference(strategy):
    """Test that generated difference vectors are canonically different."""
    user_vector = (30, 40, 30)
    vector_size = 3

    # Run multiple times to ensure consistency
    for _ in range(10):
        diff1, diff2 = strategy._generate_random_differences(user_vector, vector_size)

        # Sort both arrays to get canonical form
        sorted_diff1 = np.sort(diff1)
        sorted_diff2 = np.sort(diff2)

        # They should not be equal when sorted
        assert not np.array_equal(
            sorted_diff1, sorted_diff2
        ), f"Vectors {diff1} and {diff2} have the same canonical form"

        # But they should both sum to 0
        assert np.sum(diff1) == 0
        assert np.sum(diff2) == 0

        # And produce valid vectors
        user_array = np.array(user_vector)
        vec1 = user_array + diff1
        vec2 = user_array + diff2

        assert np.all(vec1 >= 0) and np.all(vec1 <= 100)
        assert np.all(vec2 >= 0) and np.all(vec2 <= 100)
        assert np.sum(vec1) == 100
        assert np.sum(vec2) == 100


def test_generate_random_differences_meaningful(strategy):
    """Test that generated differences are meaningful (not too small)."""
    user_vector = (20, 30, 50)
    vector_size = 3

    for _ in range(5):
        diff1, diff2 = strategy._generate_random_differences(user_vector, vector_size)

        # At least one difference should be meaningful (|diff| >= 5)
        assert any(
            abs(d) >= 5 for d in diff1
        ), f"All differences in {diff1} are too small"
        assert any(
            abs(d) >= 5 for d in diff2
        ), f"All differences in {diff2} are too small"


def test_edge_case_small_range(strategy):
    """Test with vectors that have limited valid difference ranges."""
    # This vector limits the possible differences significantly
    user_vector = (5, 90, 5)
    vector_size = 3

    # Should still be able to generate valid differences
    diff1, diff2 = strategy._generate_random_differences(user_vector, vector_size)

    # Verify constraints
    user_array = np.array(user_vector)
    vec1 = user_array + diff1
    vec2 = user_array + diff2

    # Check all values are in valid range [0, 100]
    assert np.all(vec1 >= 0) and np.all(vec1 <= 100)
    assert np.all(vec2 >= 0) and np.all(vec2 <= 100)

    # Check sums
    assert np.sum(vec1) == 100
    assert np.sum(vec2) == 100

    # Check canonical difference
    assert not np.array_equal(np.sort(diff1), np.sort(diff2))
