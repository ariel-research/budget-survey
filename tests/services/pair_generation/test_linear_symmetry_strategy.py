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

    # Each pair should be a dictionary with 4 entries (2 vectors + 2 differences)
    for pair in group_pairs:
        assert isinstance(pair, dict)
        assert len(pair) == 4

        # Check that difference vectors for display are present
        assert "option1_differences" in pair
        assert "option2_differences" in pair

        # Check that keys contain linear pattern information
        keys = list(pair.keys())
        linear_keys = [key for key in keys if "Linear Pattern" in key]
        assert len(linear_keys) == 2

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
        # Only consider the actual vector values, not the metadata
        vectors = tuple(
            sorted(
                [
                    v
                    for k, v in pair.items()
                    if not k.endswith("_differences") and isinstance(v, tuple)
                ]
            )
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
            # Skip difference metadata, only check actual vectors
            if not key.endswith("_differences") and isinstance(vector, tuple):
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
            if not key.endswith("_differences"):  # Skip difference metadata
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


def test_absolute_canonical_validation(strategy):
    """Test that absolute canonical identical patterns are correctly identified."""
    # Test the validation method directly with examples
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


def test_linear_symmetry_validation(strategy):
    """Test that linear symmetry patterns are validated correctly."""
    # Manually test some problematic patterns that should be rejected
    v1 = np.array([10, -5, -5])
    v2 = np.array([-10, 5, 5])  # Additive inverse - absolute canonical identical

    assert strategy._are_absolute_canonical_identical(
        v1, v2
    ), "Additive inverse vectors should be absolute canonical identical"


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
    # 3. a,b,c > 0 (no zeros for linear symmetry strategy)
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


def test_option_differences_calculation(strategy):
    """Test that option differences are calculated correctly as actual differences."""
    user_vector = (20, 30, 50)
    pairs = strategy.generate_pairs(user_vector, n=12, vector_size=3)

    for pair in pairs:
        # Get the strategy keys (the actual vector keys)
        strategy_keys = [k for k in pair.keys() if k.startswith("Linear Pattern")]
        assert len(strategy_keys) == 2

        option1_key = strategy_keys[0]
        option2_key = strategy_keys[1]

        option1_vector = pair[option1_key]
        option2_vector = pair[option2_key]
        option1_diff = pair["option1_differences"]
        option2_diff = pair["option2_differences"]

        # Calculate expected differences manually
        expected_diff1 = [option1_vector[i] - user_vector[i] for i in range(3)]
        expected_diff2 = [option2_vector[i] - user_vector[i] for i in range(3)]

        # Verify that stored differences match actual differences
        assert option1_diff == expected_diff1, (
            f"Option 1 differences mismatch: stored={option1_diff}, "
            f"expected={expected_diff1}, vector={option1_vector}, user={user_vector}"
        )
        assert option2_diff == expected_diff2, (
            f"Option 2 differences mismatch: stored={option2_diff}, "
            f"expected={expected_diff2}, vector={option2_vector}, user={user_vector}"
        )

        # Verify that applying differences to user vector gives back the vectors
        reconstructed1 = [user_vector[i] + option1_diff[i] for i in range(3)]
        reconstructed2 = [user_vector[i] + option2_diff[i] for i in range(3)]

        assert (
            tuple(reconstructed1) == option1_vector
        ), f"Cannot reconstruct option 1: {reconstructed1} != {option1_vector}"
        assert (
            tuple(reconstructed2) == option2_vector
        ), f"Cannot reconstruct option 2: {reconstructed2} != {option2_vector}"
