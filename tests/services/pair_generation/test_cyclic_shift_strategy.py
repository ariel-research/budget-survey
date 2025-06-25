"""Test suite for cyclic shift strategy."""

import time
from unittest.mock import patch

import numpy as np
import pytest

from application.exceptions import UnsuitableForStrategyError
from application.services.pair_generation import CyclicShiftStrategy

# Test constants
EXPECTED_VALID_VECTORS = 171
MAX_GENERATION_TIME = 3.0
PERFORMANCE_TIMEOUT = 10.0


def enumerate_all_valid_vectors():
    """
    Enumerate all valid 3D budget vectors.

    Returns:
        List[tuple]: All valid vectors (a,b,c) where:
            - a + b + c = 100
            - a,b,c ∈ {5,10,15,...,95}
            - a,b,c > 0
    """
    valid_vectors = []

    for a in range(5, 96, 5):
        for b in range(5, 96, 5):
            c = 100 - a - b

            if c > 0 and 5 <= c <= 95 and c % 5 == 0:
                valid_vectors.append((a, b, c))

    return valid_vectors


def validate_pair_structure(pair, pair_index, user_vector):
    """Validate basic pair structure and properties."""
    # Must have exactly 4 keys
    if len(pair) != 4:
        return f"Pair {pair_index} has {len(pair)} keys, expected 4"

    # Must have difference keys
    if "option1_differences" not in pair or "option2_differences" not in pair:
        return f"Pair {pair_index} missing difference keys"

    # Validate vector properties
    for key, vector in pair.items():
        if not key.endswith("_differences"):
            if (
                not isinstance(vector, tuple)
                or len(vector) != 3
                or sum(vector) != 100
                or not all(0 <= v <= 100 for v in vector)
            ):
                return f"Invalid vector in pair {pair_index}: {vector}"

    return None  # No errors


@pytest.fixture
def strategy():
    return CyclicShiftStrategy()


def test_strategy_name(strategy):
    """Test if strategy name is correct."""
    assert strategy.get_strategy_name() == "cyclic_shift"


def test_generate_random_differences(strategy):
    """Test random difference generation works correctly."""
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
    """Test cyclic shift functionality."""
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
    """Test difference verification functionality."""
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
    """Test group generation functionality."""
    user_vector = (20, 30, 50)
    vector_size = 3
    group_num = 1

    group_pairs = strategy._generate_group(user_vector, vector_size, group_num)

    # Should generate 3 pairs
    assert len(group_pairs) == 3

    # Each pair should be a dictionary with 4 entries
    # (2 vectors + 2 differences)
    for pair in group_pairs:
        assert isinstance(pair, dict)
        assert len(pair) == 4

        # Check that difference vectors are present
        assert "option1_differences" in pair
        assert "option2_differences" in pair

        # Check that keys contain shift information
        keys = list(pair.keys())
        assert any("shift" in key for key in keys)

        # Check that values are valid tuples (skip differences)
        for key, vector in pair.items():
            if not key.endswith("_differences"):
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
    # (2 vectors + 2 difference vectors)
    for pair in pairs:
        assert isinstance(pair, dict)
        assert len(pair) == 4

        # Check that difference vectors are present
        assert "option1_differences" in pair
        assert "option2_differences" in pair
        assert isinstance(pair["option1_differences"], list)
        assert isinstance(pair["option2_differences"], list)
        assert len(pair["option1_differences"]) == 3
        assert len(pair["option2_differences"]) == 3
        assert sum(pair["option1_differences"]) == 0  # Should sum to zero
        assert sum(pair["option2_differences"]) == 0  # Should sum to zero

        # Check that all vectors are valid (skip the difference keys)
        for key, vector in pair.items():
            if not key.endswith("_differences"):
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
        # Only consider actual vector values, not difference metadata
        vectors = tuple(
            sorted([v for k, v in pair.items() if not k.endswith("_differences")])
        )
        pair_sets.add(vectors)

    # All pairs should be unique
    assert len(pair_sets) == len(pairs)


def test_cyclic_pattern_consistency(strategy):
    """Test that cyclic shifts maintain PERFECT mathematical relationships."""
    user_vector = (30, 40, 30)

    group_pairs = strategy._generate_group(user_vector, 3, 1)

    if len(group_pairs) == 3:
        # Extract differences from each pair
        group_diffs = []
        for pair in group_pairs:
            diff1 = pair["option1_differences"]
            diff2 = pair["option2_differences"]
            group_diffs.append((diff1, diff2))

        # Verify PERFECT cyclic shift relationships
        base_diff1 = np.array(group_diffs[0][0])
        base_diff2 = np.array(group_diffs[0][1])

        for shift in range(1, 3):
            expected_diff1 = strategy._apply_cyclic_shift(base_diff1, shift)
            expected_diff2 = strategy._apply_cyclic_shift(base_diff2, shift)

            actual_diff1 = np.array(group_diffs[shift][0])
            actual_diff2 = np.array(group_diffs[shift][1])

            # PERFECT equality - no tolerance needed
            np.testing.assert_array_equal(
                actual_diff1,
                expected_diff1,
                err_msg=f"Shift {shift} diff1 not perfectly cyclic",
            )
            np.testing.assert_array_equal(
                actual_diff2,
                expected_diff2,
                err_msg=f"Shift {shift} diff2 not perfectly cyclic",
            )


@patch("application.services.pair_generation.cyclic_shift_strategy." "get_translation")
def test_option_labels(mock_get_translation, strategy):
    """Test option labels generation."""
    mock_get_translation.side_effect = lambda key, *args, **kwargs: {
        "cyclic_pattern_a": "Pattern A",
        "cyclic_pattern_b": "Pattern B",
    }.get(key, key)

    labels = strategy.get_option_labels()
    assert labels == ("Pattern A", "Pattern B")


def test_table_columns(strategy):
    """Test table columns definition."""
    columns = strategy.get_table_columns()

    assert isinstance(columns, dict)
    assert "group_consistency" in columns

    # Check column properties
    for column_key, column_def in columns.items():
        assert "name" in column_def
        assert "type" in column_def
        assert column_def["type"] == "percentage"
        assert column_def.get("highlight") is True


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


def test_perfect_mathematical_guarantee_sample_vectors(strategy):
    """Test perfect cyclic relationships for sample vectors."""
    test_vectors = [
        (30, 40, 30),
        (35, 35, 30),
        (25, 35, 40),
        (5, 5, 90),
    ]

    for user_vector in test_vectors:
        pairs = strategy.generate_pairs(user_vector, n=12, vector_size=3)
        assert len(pairs) == 12, f"Failed to generate 12 pairs for {user_vector}"

        # Verify perfect relationships in each group
        for group_start in range(0, 12, 3):
            group_pairs = pairs[group_start : group_start + 3]
            if len(group_pairs) == 3:
                assert strategy._validate_cyclic_relationships(group_pairs), (
                    f"Imperfect cyclic relationships for {user_vector}, "
                    f"group {group_start//3 + 1}"
                )


def test_comprehensive_algorithm_validation(strategy):
    """
    Comprehensive validation: ALL valid vectors must generate 12 pairs
    with PERFECT mathematical relationships.

    This test validates:
    1. Algorithm completeness (works for 100% of valid vectors)
    2. Perfect mathematical relationships (cyclic shifts)
    3. Performance requirements
    """
    print("\n=== COMPREHENSIVE ALGORITHM VALIDATION ===")

    # Get all valid vectors
    valid_vectors = enumerate_all_valid_vectors()
    assert len(valid_vectors) == EXPECTED_VALID_VECTORS, (
        f"Expected {EXPECTED_VALID_VECTORS} valid vectors, " f"got {len(valid_vectors)}"
    )

    print(f"Testing {len(valid_vectors)} valid vectors...")

    successful_vectors = []
    failed_vectors = []
    timing_results = []
    relationship_failures = []

    for i, user_vector in enumerate(valid_vectors, 1):
        print(
            f"Testing vector {i:2d}/{len(valid_vectors)}: " f"{user_vector}",
            end=" ... ",
        )

        try:
            start_time = time.time()
            pairs = strategy.generate_pairs(user_vector, n=12, vector_size=3)
            elapsed = time.time() - start_time

            # Basic validation
            if len(pairs) != 12:
                failed_vectors.append(
                    (user_vector, f"Generated {len(pairs)} pairs, expected 12")
                )
                print(f"FAIL (wrong count: {len(pairs)})")
                continue

            # Performance validation
            if elapsed >= PERFORMANCE_TIMEOUT:
                failed_vectors.append((user_vector, f"Too slow: {elapsed:.2f}s"))
                print(f"FAIL (timeout: {elapsed:.2f}s)")
                continue

            # Structural validation
            structure_error = None
            for j, pair in enumerate(pairs):
                error = validate_pair_structure(pair, j, user_vector)
                if error:
                    structure_error = error
                    break

            if structure_error:
                failed_vectors.append((user_vector, structure_error))
                print("FAIL (structure)")
                continue

            # MATHEMATICAL RELATIONSHIP VALIDATION
            perfect_relationships = True
            for group_start in range(0, 12, 3):
                group_pairs = pairs[group_start : group_start + 3]
                if len(group_pairs) == 3:
                    if not strategy._validate_cyclic_relationships(group_pairs):
                        relationship_failures.append(
                            (user_vector, f"Group {group_start//3 + 1}")
                        )
                        perfect_relationships = False
                        break

            if not perfect_relationships:
                print("FAIL (relationships)")
                continue

            # All validations passed
            successful_vectors.append(user_vector)
            timing_results.append((user_vector, elapsed))
            print(f"✓ ({elapsed:.3f}s)")

        except Exception as e:
            failed_vectors.append((user_vector, str(e)))
            print(f"FAIL (exception: {type(e).__name__})")

    # Results analysis
    total_tested = len(valid_vectors)
    total_successful = len(successful_vectors)
    success_rate = (total_successful / total_tested) * 100

    print("\n=== RESULTS ===")
    print(f"Vectors tested: {total_tested}")
    print(f"Successful: {total_successful}")
    print(f"Success rate: {success_rate:.1f}%")

    if timing_results:
        avg_time = sum(t[1] for t in timing_results) / len(timing_results)
        max_time = max(t[1] for t in timing_results)
        min_time = min(t[1] for t in timing_results)
        print(
            f"Timing: avg={avg_time:.3f}s, min={min_time:.3f}s, " f"max={max_time:.3f}s"
        )

    # Report failures
    if failed_vectors:
        print(f"\n❌ ALGORITHM FAILURES ({len(failed_vectors)}):")
        for vec, error in failed_vectors[:5]:  # Show first 5
            print(f"  {vec}: {error}")
        if len(failed_vectors) > 5:
            print(f"  ... and {len(failed_vectors) - 5} more")

    if relationship_failures:
        print(f"\n❌ RELATIONSHIP FAILURES " f"({len(relationship_failures)}):")
        for vec, error in relationship_failures[:5]:  # Show first 5
            print(f"  {vec}: {error}")
        if len(relationship_failures) > 5:
            print(f"  ... and {len(relationship_failures) - 5} more")

    # STRICT REQUIREMENTS
    assert total_successful == total_tested, (
        f"ALGORITHMIC INCOMPLETENESS: Only {total_successful}/"
        f"{total_tested} vectors succeeded. Algorithm must work for "
        f"100% of valid constraint space."
    )

    assert success_rate == 100.0, (
        f"Success rate {success_rate:.1f}% is below mathematical "
        f"requirement of 100%"
    )

    if timing_results:
        assert avg_time < MAX_GENERATION_TIME, (
            f"Average time {avg_time:.2f}s exceeds performance "
            f"requirement of {MAX_GENERATION_TIME}s"
        )

    print(
        "✅ COMPREHENSIVE VALIDATION COMPLETE: Perfect mathematical "
        "relationships guaranteed for ALL valid vectors"
    )


def test_logging_behavior(strategy, caplog):
    """Test appropriate logging occurs."""
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


def test_difference_generation_properties(strategy):
    """Test properties of difference generation."""
    user_vector = (20, 30, 50)
    vector_size = 3

    # Generate multiple pairs to check properties
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

        # At least one difference should be meaningful (|diff| >= 5)
        assert any(
            abs(d) >= 5 for d in diff1
        ), f"All differences in {diff1} are too small"
        assert any(
            abs(d) >= 5 for d in diff2
        ), f"All differences in {diff2} are too small"


def test_absolute_canonical_validation(strategy):
    """Test absolute canonical identical patterns are correctly identified."""
    # Identical absolute canonical forms
    assert strategy._are_absolute_canonical_identical([10, 0, -10], [-10, 0, 10])
    assert strategy._are_absolute_canonical_identical([10, -5, -5], [-10, 5, 5])
    assert strategy._are_absolute_canonical_identical([0, -10, 10], [10, 0, -10])

    # Different absolute canonical forms
    assert not strategy._are_absolute_canonical_identical([20, -10, -10], [15, -10, -5])
    assert not strategy._are_absolute_canonical_identical(
        [25, -15, -10], [20, -10, -10]
    )

    # Test in generated pairs
    user_vector = (30, 40, 30)
    pairs = strategy.generate_pairs(user_vector, n=12, vector_size=3)

    for i, pair in enumerate(pairs):
        diff1 = pair["option1_differences"]
        diff2 = pair["option2_differences"]

        abs_can1 = tuple(sorted(abs(x) for x in diff1))
        abs_can2 = tuple(sorted(abs(x) for x in diff2))

        assert abs_can1 != abs_can2, (
            f"Pair {i}: Found absolute canonical identical: "
            f"{diff1} and {diff2} both have form {abs_can1}"
        )
