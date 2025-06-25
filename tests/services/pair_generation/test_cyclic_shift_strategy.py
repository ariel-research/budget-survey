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
        # Only consider the actual vector values, not the difference metadata
        vectors = tuple(
            sorted([v for k, v in pair.items() if not k.endswith("_differences")])
        )
        pair_sets.add(vectors)

    # All pairs should be unique
    assert len(pair_sets) == len(pairs)


def test_cyclic_pattern_consistency(strategy):
    """Test that cyclic shifts within a group maintain PERFECT mathematical relationships."""
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


def test_perfect_mathematical_guarantee_all_vectors(strategy):
    """Test that perfect cyclic relationships are guaranteed for ALL valid vectors."""
    # Test with various user vectors that would have had rounding issues
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
                assert strategy._validate_cyclic_relationships(
                    group_pairs
                ), f"Imperfect cyclic relationships for {user_vector}, group {group_start//3 + 1}"


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


def test_absolute_canonical_validation(strategy):
    """Test that absolute canonical identical patterns are correctly identified."""
    # Test the validation method directly with CORRECT examples
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
            f"Pair {i}: Found absolute canonical identical: {diff1} and {diff2} "
            f"both have form {abs_can1}"
        )


def test_cyclic_shift_preserves_validation(strategy):
    """Test that validation works correctly across all shifts."""
    # Manually test some problematic patterns
    diff1 = np.array([10, -5, -5])
    diff2 = np.array([-10, 5, 5])  # Additive inverse

    # These should be caught at any shift
    for shift in range(3):
        shifted1 = strategy._apply_cyclic_shift(diff1, shift)
        shifted2 = strategy._apply_cyclic_shift(diff2, shift)

        assert strategy._are_absolute_canonical_identical(
            shifted1, shifted2
        ), f"Shift {shift} should preserve absolute canonical identity"


def test_cyclic_shift_within_group_consistency(strategy):
    """Test that cyclic shifts within a group maintain proper relationships."""
    user_vector = (30, 40, 30)

    # Generate a single group
    group_pairs = strategy._generate_group(user_vector, 3, 1)

    if len(group_pairs) == 3:  # Only test if we got a full group
        # Extract differences from each pair
        group_diffs = []
        for pair in group_pairs:
            diff1 = pair["option1_differences"]
            diff2 = pair["option2_differences"]
            group_diffs.append((diff1, diff2))

        # The differences should follow cyclic shift pattern
        base_diff1 = np.array(group_diffs[0][0])
        base_diff2 = np.array(group_diffs[0][1])

        for shift in range(1, 3):
            expected_diff1 = strategy._apply_cyclic_shift(base_diff1, shift)
            expected_diff2 = strategy._apply_cyclic_shift(base_diff2, shift)

            actual_diff1 = np.array(group_diffs[shift][0])
            actual_diff2 = np.array(group_diffs[shift][1])

            np.testing.assert_array_equal(
                actual_diff1,
                expected_diff1,
                err_msg=f"Shift {shift} diff1 not properly cyclic",
            )
            np.testing.assert_array_equal(
                actual_diff2,
                expected_diff2,
                err_msg=f"Shift {shift} diff2 not properly cyclic",
            )


def test_generation_feasibility_all_valid_vectors(strategy):
    """
    Mathematical verification that ALL valid user vectors generate exactly 12 pairs.

    This test systematically enumerates the complete constraint space of valid
    3-dimensional budget vectors and verifies algorithmic completeness.
    """
    import time

    # MATHEMATICAL CONSTRAINT SPACE DEFINITION:
    # Valid vector (a,b,c) must satisfy:
    # 1. a + b + c = 100 (budget constraint)
    # 2. a,b,c ∈ {5,10,15,...,95} (multiples of 5)
    # 3. a,b,c > 0 (no zeros for cyclic shift strategy)
    # 4. 5 ≤ a,b,c ≤ 95 (valid range)

    print("\n=== MATHEMATICAL ENUMERATION OF CONSTRAINT SPACE ===")

    # Systematically enumerate ALL valid vectors
    valid_vectors = []
    enumeration_stats = {
        "total_combinations": 0,
        "sum_violations": 0,
        "range_violations": 0,
        "zero_violations": 0,
        "valid_count": 0,
    }

    # For 3D budget vectors with multiples of 5
    for a in range(5, 96, 5):  # a ∈ {5,10,15,...,95}
        for b in range(5, 96, 5):  # b ∈ {5,10,15,...,95}
            enumeration_stats["total_combinations"] += 1

            # Calculate c from constraint: a + b + c = 100
            c = 100 - a - b

            # Validate c against all constraints
            if c <= 0:
                enumeration_stats["zero_violations"] += 1
                continue
            if c < 5 or c > 95:
                enumeration_stats["range_violations"] += 1
                continue
            if c % 5 != 0:
                enumeration_stats["sum_violations"] += 1
                continue

            # Vector satisfies all constraints
            valid_vectors.append((a, b, c))
            enumeration_stats["valid_count"] += 1

    # Mathematical verification of enumeration completeness
    print("Enumeration Statistics:")
    print(f"  Total combinations tested: {enumeration_stats['total_combinations']}")
    print("  Constraint violations:")
    print(f"    Zero values: {enumeration_stats['zero_violations']}")
    print(f"    Range violations: {enumeration_stats['range_violations']}")
    print(f"    Sum constraint violations: {enumeration_stats['sum_violations']}")
    print(f"  Valid vectors found: {enumeration_stats['valid_count']}")

    # Theoretical count: For a+b+c=100, multiples of 5, 5≤a,b,c≤95
    # This gives us exactly 171 valid vectors
    expected_count = 171
    assert len(valid_vectors) == expected_count, (
        f"Mathematical enumeration error: Expected exactly {expected_count} "
        f"valid vectors, got {len(valid_vectors)}"
    )

    print(f"✓ Enumeration complete: {len(valid_vectors)} vectors")

    # ALGORITHMIC COMPLETENESS VERIFICATION
    print("\n=== ALGORITHMIC COMPLETENESS VERIFICATION ===")

    successful_vectors = []
    failed_vectors = []
    timing_results = []
    pair_validation_failures = []

    for i, user_vector in enumerate(valid_vectors, 1):
        print(f"Testing vector {i:2d}/{len(valid_vectors)}: {user_vector}", end=" ... ")

        try:
            start_time = time.time()
            pairs = strategy.generate_pairs(user_vector, n=12, vector_size=3)
            elapsed = time.time() - start_time

            # STRICT VALIDATION: Must generate exactly 12 pairs
            if len(pairs) != 12:
                pair_validation_failures.append(
                    (user_vector, f"Generated {len(pairs)} pairs, expected 12")
                )
                print(f"FAIL (wrong count: {len(pairs)})")
                continue

            # Performance validation
            if elapsed >= 10.0:
                failed_vectors.append((user_vector, f"Too slow: {elapsed:.2f}s"))
                print(f"FAIL (timeout: {elapsed:.2f}s)")
                continue

            # Additional pair validity checks
            for j, pair in enumerate(pairs):
                # Each pair must have exactly 4 keys
                if len(pair) != 4:
                    pair_validation_failures.append(
                        (user_vector, f"Pair {j} has {len(pair)} keys, expected 4")
                    )
                    print("FAIL (pair structure)")
                    break

                # Must have difference keys
                if (
                    "option1_differences" not in pair
                    or "option2_differences" not in pair
                ):
                    pair_validation_failures.append(
                        (user_vector, f"Pair {j} missing difference keys")
                    )
                    print("FAIL (missing diffs)")
                    break

                # Validate vector properties
                for key, vector in pair.items():
                    if not key.endswith("_differences"):
                        if (
                            not isinstance(vector, tuple)
                            or len(vector) != 3
                            or sum(vector) != 100
                            or not all(0 <= v <= 100 for v in vector)
                        ):
                            pair_validation_failures.append(
                                (user_vector, f"Invalid vector in pair {j}: {vector}")
                            )
                            print("FAIL (invalid vector)")
                            break
                else:
                    continue
                break
            else:
                # All validations passed
                successful_vectors.append(user_vector)
                timing_results.append((user_vector, elapsed))
                print(f"✓ ({elapsed:.3f}s)")
                continue

        except Exception as e:
            failed_vectors.append((user_vector, str(e)))
            print(f"FAIL (exception: {type(e).__name__})")

    # MATHEMATICAL COMPLETENESS RESULTS
    print("\n=== COMPLETENESS VERIFICATION RESULTS ===")

    total_tested = len(valid_vectors)
    total_successful = len(successful_vectors)
    success_rate = (total_successful / total_tested) * 100

    print(f"Vectors tested: {total_tested}")
    print(f"Successful: {total_successful}")
    print(f"Success rate: {success_rate:.1f}%")

    if timing_results:
        avg_time = sum(t[1] for t in timing_results) / len(timing_results)
        max_time = max(t[1] for t in timing_results)
        min_time = min(t[1] for t in timing_results)
        print(f"Timing: avg={avg_time:.3f}s, min={min_time:.3f}s, max={max_time:.3f}s")

    # Report failures in detail
    if failed_vectors:
        print(f"\n❌ ALGORITHM FAILURES ({len(failed_vectors)}):")
        for vec, error in failed_vectors:
            print(f"  {vec}: {error}")

    if pair_validation_failures:
        print(f"\n❌ PAIR VALIDATION FAILURES ({len(pair_validation_failures)}):")
        for vec, error in pair_validation_failures:
            print(f"  {vec}: {error}")

    # MATHEMATICAL REQUIREMENT: 100% SUCCESS RATE
    # The algorithm must be able to generate exactly 12 valid pairs
    # for every single valid user vector in the constraint space
    assert total_successful == total_tested, (
        f"ALGORITHMIC INCOMPLETENESS DETECTED: "
        f"Only {total_successful}/{total_tested} vectors succeeded. "
        f"Algorithm must work for 100% of valid constraint space."
    )

    assert (
        success_rate == 100.0
    ), f"Success rate {success_rate:.1f}% is below mathematical requirement of 100%"

    if timing_results:
        assert (
            avg_time < 3.0
        ), f"Average time {avg_time:.2f}s exceeds performance requirement of 3.0s"

    print(
        "✅ MATHEMATICAL VERIFICATION COMPLETE: Algorithm is complete over constraint space"
    )


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
