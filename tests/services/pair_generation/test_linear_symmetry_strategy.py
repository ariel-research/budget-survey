"""Test suite for linear symmetry strategy."""

import time
from unittest.mock import patch

import numpy as np
import pytest

from analysis.logic.stats_calculators import (
    calculate_linear_symmetry_group_consistency,
    parse_linear_pattern_strategy,
)
from application.services.pair_generation import LinearSymmetryStrategy

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
    return LinearSymmetryStrategy()


def test_strategy_name(strategy):
    """Test if strategy name is correct."""
    assert strategy.get_strategy_name() == "sign_symmetry_test"


def test_generate_distance_vectors(strategy):
    """Test distance vector generation functionality."""
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
    """Test group generation functionality."""
    user_vector = (20, 30, 50)
    vector_size = 3
    group_num = 1

    group_pairs = strategy._generate_group(user_vector, vector_size, group_num)

    # Should generate 2 pairs
    assert len(group_pairs) == 2

    # Each pair should be a dictionary with 4 entries
    # (2 vectors + 2 differences)
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
        # Only consider actual vector values, not the metadata
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


@patch(
    "application.services.pair_generation.linear_symmetry_strategy." "get_translation"
)
def test_option_labels(mock_get_translation, strategy):
    """Test option labels generation."""
    mock_get_translation.side_effect = lambda key, *args, **kwargs: {
        "linear_positive": "Linear Positive",
        "linear_negative": "Linear Negative",
    }.get(key, key)

    labels = strategy.get_option_labels()
    assert labels == ("Linear Positive", "Linear Negative")


def test_table_columns(strategy):
    """Test table columns definition."""
    columns = strategy.get_table_columns()

    assert isinstance(columns, dict)
    assert "linear_consistency" in columns

    # Check column properties
    column_def = columns["linear_consistency"]
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
    """Test perfect symmetry relationships for sample vectors."""
    test_vectors = [
        (40, 30, 30),
        (35, 35, 30),
        (25, 35, 40),
        (5, 5, 90),
    ]

    for user_vector in test_vectors:
        pairs = strategy.generate_pairs(user_vector, n=12, vector_size=3)
        assert len(pairs) == 12, f"Failed to generate 12 pairs for {user_vector}"

        # Verify perfect relationships in each group
        for group_start in range(0, 12, 2):
            group_pairs = pairs[group_start : group_start + 2]
            if len(group_pairs) == 2:
                assert strategy._validate_symmetry_relationships(group_pairs), (
                    f"Imperfect symmetry relationships for {user_vector}, "
                    f"group {group_start//2 + 1}"
                )


def test_comprehensive_algorithm_validation(strategy):
    """
    Comprehensive validation: ALL valid vectors must generate 12 pairs
    with PERFECT mathematical relationships.

    This test validates:
    1. Algorithm completeness (works for 100% of valid vectors)
    2. Perfect mathematical relationships (linear symmetry)
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
            for group_start in range(0, 12, 2):
                group_pairs = pairs[group_start : group_start + 2]
                if len(group_pairs) == 2:
                    if not strategy._validate_symmetry_relationships(group_pairs):
                        relationship_failures.append(
                            (user_vector, f"Group {group_start//2 + 1}")
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
    assert any("LinearSymmetryStrategy" in record.message for record in caplog.records)


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


def test_linear_symmetry_validation(strategy):
    """Test that linear symmetry patterns are validated correctly."""
    # Test problematic patterns that should be rejected
    v1 = np.array([10, -5, -5])
    v2 = np.array([-10, 5, 5])  # Additive inverse - absolute canonical

    assert strategy._are_absolute_canonical_identical(
        v1, v2
    ), "Additive inverse vectors should be absolute canonical identical"


def test_linear_symmetry_within_group_consistency(strategy):
    """Test that linear symmetry pairs maintain PERFECT relationships."""
    user_vector = (40, 30, 30)

    # Generate a single group
    group_pairs = strategy._generate_group(user_vector, 3, 1)

    if len(group_pairs) == 2:  # Only test if we got a full group
        # Extract the pairs: (+v1,+v2) and (-v1,-v2)
        positive_pair = group_pairs[0]  # ideal + v1, ideal + v2
        negative_pair = group_pairs[1]  # ideal - v1, ideal - v2

        # Get the actual difference vectors
        pos_diff1 = positive_pair["option1_differences"]
        pos_diff2 = positive_pair["option2_differences"]
        neg_diff1 = negative_pair["option1_differences"]
        neg_diff2 = negative_pair["option2_differences"]

        # PERFECT symmetry: negative differences should be exact opposites
        np.testing.assert_array_equal(
            np.array(pos_diff1),
            -np.array(neg_diff1),
            err_msg="Negative pair diff1 should be exact opposite of "
            "positive pair diff1",
        )
        np.testing.assert_array_equal(
            np.array(pos_diff2),
            -np.array(neg_diff2),
            err_msg="Negative pair diff2 should be exact opposite of "
            "positive pair diff2",
        )


def test_option_differences_calculation(strategy):
    """Test that option differences are calculated correctly."""
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
            f"expected={expected_diff1}, vector={option1_vector}, "
            f"user={user_vector}"
        )
        assert option2_diff == expected_diff2, (
            f"Option 2 differences mismatch: stored={option2_diff}, "
            f"expected={expected_diff2}, vector={option2_vector}, "
            f"user={user_vector}"
        )

        # Verify that applying differences to user vector gives back vectors
        reconstructed1 = [user_vector[i] + option1_diff[i] for i in range(3)]
        reconstructed2 = [user_vector[i] + option2_diff[i] for i in range(3)]

        assert tuple(reconstructed1) == option1_vector, (
            f"Cannot reconstruct option 1: {reconstructed1} != " f"{option1_vector}"
        )
        assert tuple(reconstructed2) == option2_vector, (
            f"Cannot reconstruct option 2: {reconstructed2} != " f"{option2_vector}"
        )


def test_linear_symmetry_consistency_calculation_mathematical_correctness():
    """
    Test that the linear symmetry consistency calculation is mathematically correct.
    """
    # Test Case 1: Perfect Linear Symmetry (both groups consistent)
    choices_perfect_symmetry = [
        # Group 1: User chooses v in both + and - directions
        {
            "pair_number": 1,
            "option1_strategy": "Linear Pattern + (v1)",
            "option2_strategy": "Linear Pattern + (w1)",
            "user_choice": 1,  # Chose v
        },
        {
            "pair_number": 2,
            "option1_strategy": "Linear Pattern - (v1)",
            "option2_strategy": "Linear Pattern - (w1)",
            "user_choice": 1,  # Chose v (CONSISTENT!)
        },
        # Group 2: User chooses w in both + and - directions
        {
            "pair_number": 3,
            "option1_strategy": "Linear Pattern + (v2)",
            "option2_strategy": "Linear Pattern + (w2)",
            "user_choice": 2,  # Chose w
        },
        {
            "pair_number": 4,
            "option1_strategy": "Linear Pattern - (v2)",
            "option2_strategy": "Linear Pattern - (w2)",
            "user_choice": 2,  # Chose w (CONSISTENT!)
        },
    ]

    result = calculate_linear_symmetry_group_consistency(choices_perfect_symmetry)

    # Validate perfect symmetry results
    assert (
        result["group_1"] == 100.0
    ), f"Group 1 should be 100% consistent, got {result['group_1']}"
    assert (
        result["group_2"] == 100.0
    ), f"Group 2 should be 100% consistent, got {result['group_2']}"
    assert (
        result["overall"] == 100.0
    ), f"Overall should be 100%, got {result['overall']}"

    # Test Case 2: No Linear Symmetry (both groups inconsistent)
    choices_no_symmetry = [
        # Group 1: User chooses v in + direction, w in - direction
        {
            "pair_number": 1,
            "option1_strategy": "Linear Pattern + (v1)",
            "option2_strategy": "Linear Pattern + (w1)",
            "user_choice": 1,  # Chose v
        },
        {
            "pair_number": 2,
            "option1_strategy": "Linear Pattern - (v1)",
            "option2_strategy": "Linear Pattern - (w1)",
            "user_choice": 2,  # Chose w (INCONSISTENT!)
        },
        # Group 2: User chooses w in + direction, v in - direction
        {
            "pair_number": 3,
            "option1_strategy": "Linear Pattern + (v2)",
            "option2_strategy": "Linear Pattern + (w2)",
            "user_choice": 2,  # Chose w
        },
        {
            "pair_number": 4,
            "option1_strategy": "Linear Pattern - (v2)",
            "option2_strategy": "Linear Pattern - (w2)",
            "user_choice": 1,  # Chose v (INCONSISTENT!)
        },
    ]

    result = calculate_linear_symmetry_group_consistency(choices_no_symmetry)

    # Validate no symmetry results
    assert (
        result["group_1"] == 0.0
    ), f"Group 1 should be 0% consistent, got {result['group_1']}"
    assert (
        result["group_2"] == 0.0
    ), f"Group 2 should be 0% consistent, got {result['group_2']}"
    assert result["overall"] == 0.0, f"Overall should be 0%, got {result['overall']}"

    # Test Case 3: Mixed Symmetry (one consistent, one inconsistent)
    choices_mixed_symmetry = [
        # Group 1: CONSISTENT - User chooses v in both directions
        {
            "pair_number": 1,
            "option1_strategy": "Linear Pattern + (v1)",
            "option2_strategy": "Linear Pattern + (w1)",
            "user_choice": 1,  # Chose v
        },
        {
            "pair_number": 2,
            "option1_strategy": "Linear Pattern - (v1)",
            "option2_strategy": "Linear Pattern - (w1)",
            "user_choice": 1,  # Chose v (CONSISTENT!)
        },
        # Group 2: INCONSISTENT - User chooses different vectors
        {
            "pair_number": 3,
            "option1_strategy": "Linear Pattern + (v2)",
            "option2_strategy": "Linear Pattern + (w2)",
            "user_choice": 1,  # Chose v
        },
        {
            "pair_number": 4,
            "option1_strategy": "Linear Pattern - (v2)",
            "option2_strategy": "Linear Pattern - (w2)",
            "user_choice": 2,  # Chose w (INCONSISTENT!)
        },
    ]

    result = calculate_linear_symmetry_group_consistency(choices_mixed_symmetry)

    # Validate mixed symmetry results
    assert (
        result["group_1"] == 100.0
    ), f"Group 1 should be 100% consistent, got {result['group_1']}"
    assert (
        result["group_2"] == 0.0
    ), f"Group 2 should be 0% consistent, got {result['group_2']}"
    assert result["overall"] == 50.0, f"Overall should be 50%, got {result['overall']}"


def test_parse_linear_pattern_strategy():
    """
    Test the helper function that parses linear pattern strategy strings.
    """
    # Test Case 1: Valid positive pattern
    group_num, sign, vector_choice = parse_linear_pattern_strategy(
        "Linear Pattern + (v1)", "Linear Pattern + (w1)", 1  # User chose option 1 (v)
    )
    assert group_num == 1
    assert sign == "+"
    assert vector_choice == 1  # v=1

    # Test Case 2: Valid negative pattern with w choice
    group_num, sign, vector_choice = parse_linear_pattern_strategy(
        "Linear Pattern - (v3)", "Linear Pattern - (w3)", 2  # User chose option 2 (w)
    )
    assert group_num == 3
    assert sign == "-"
    assert vector_choice == 2  # w=2

    # Test Case 3: Invalid pattern (mismatched groups)
    group_num, sign, vector_choice = parse_linear_pattern_strategy(
        "Linear Pattern + (v1)", "Linear Pattern + (w2)", 1  # Different group!
    )
    assert group_num is None
    assert sign is None
    assert vector_choice is None

    # Test Case 4: Invalid pattern (malformed string)
    group_num, sign, vector_choice = parse_linear_pattern_strategy(
        "Invalid Pattern", "Another Invalid Pattern", 1
    )
    assert group_num is None
    assert sign is None
    assert vector_choice is None


def test_linear_symmetry_edge_cases():
    """
    Test edge cases for linear symmetry consistency calculation.
    """
    # Test Case 1: Empty choices
    result = calculate_linear_symmetry_group_consistency([])
    assert result["overall"] == 0.0

    # Test Case 2: Incomplete group (only positive direction)
    incomplete_choices = [
        {
            "pair_number": 1,
            "option1_strategy": "Linear Pattern + (v1)",
            "option2_strategy": "Linear Pattern + (w1)",
            "user_choice": 1,
        },
        # Missing negative direction pair for group 1
    ]

    result = calculate_linear_symmetry_group_consistency(incomplete_choices)
    assert result["group_1"] == 0.0  # Incomplete group should be 0%
    assert result["overall"] == 0.0

    # Test Case 3: Malformed strategy strings
    malformed_choices = [
        {
            "pair_number": 1,
            "option1_strategy": "Invalid Pattern",
            "option2_strategy": "Another Invalid",
            "user_choice": 1,
        },
    ]

    result = calculate_linear_symmetry_group_consistency(malformed_choices)
    assert result["overall"] == 0.0
