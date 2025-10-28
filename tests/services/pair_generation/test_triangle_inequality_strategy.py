"""Test suite for triangle inequality strategy."""

import time

import numpy as np
import pytest

from application.exceptions import UnsuitableForStrategyError
from application.services.pair_generation import TriangleInequalityStrategy

# Test constants
EXPECTED_VALID_VECTORS = 171  # Vectors without zeros
MAX_GENERATION_TIME = 3.0
PERFORMANCE_TIMEOUT = 10.0


def enumerate_all_valid_vectors():
    """
    Enumerate all valid 3D budget vectors without zeros.

    Returns:
        List[tuple]: All valid vectors (a,b,c) where:
            - a + b + c = 100
            - a,b,c ∈ {5,10,15,...,95}
            - a,b,c > 0 (no zeros)
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
    # Must have required keys
    required_keys = ["group_number", "rotation_number", "variant", "is_biennial"]
    for key in required_keys:
        if key not in pair:
            return f"Pair {pair_index} missing key: {key}"

    # Must have difference keys
    if "option1_differences" not in pair or "option2_differences" not in pair:
        return f"Pair {pair_index} missing difference keys"

    # Validate biennial vectors (6 elements each)
    for key, vector in pair.items():
        if (
            not key.endswith("_differences")
            and not key.endswith("_number")
            and key not in ["variant", "is_biennial"]
        ):
            if (
                not isinstance(vector, list)
                or len(vector) != 6  # Biennial: 3 for Year 1 + 3 for Year 2
                or sum(vector[:3]) != 100  # Year 1 sums to 100
                or sum(vector[3:]) != 100  # Year 2 sums to 100
                or not all(0 <= v <= 100 for v in vector)
            ):
                return f"Invalid biennial vector in pair {pair_index}: {vector}"

    return None  # No errors


@pytest.fixture
def strategy():
    return TriangleInequalityStrategy()


def test_strategy_name(strategy):
    """Test if strategy name is correct."""
    assert strategy.get_strategy_name() == "triangle_inequality_test"


def test_generate_pairs_returns_exactly_12(strategy):
    """Test that generate_pairs returns exactly 12 pairs."""
    user_vector = (20, 30, 50)
    pairs = strategy.generate_pairs(user_vector, n=12, vector_size=3)

    assert len(pairs) == 12


def test_generate_pairs_structure(strategy):
    """Test the structure of generated pairs."""
    user_vector = (20, 30, 50)
    pairs = strategy.generate_pairs(user_vector, n=12, vector_size=3)

    for i, pair in enumerate(pairs):
        # Check group and rotation numbers
        assert 1 <= pair["group_number"] <= 2
        assert 0 <= pair["rotation_number"] <= 2
        assert pair["variant"] in ["positive", "negative"]
        assert pair["is_biennial"] is True

        # Check differences are 6-element arrays
        assert len(pair["option1_differences"]) == 6
        assert len(pair["option2_differences"]) == 6


def test_decomposition_correctness(strategy):
    """Test that q = q1 + q2 for decomposition."""
    user_vector = (30, 40, 30)

    # Generate a base change vector
    q = strategy._generate_base_change_vector(user_vector, 3)

    # Decompose it
    q1, q2 = strategy._decompose_change_vector(q)

    # Verify q1 + q2 = q
    assert np.allclose(q1 + q2, q), f"Decomposition failed: {q1} + {q2} != {q}"

    # Verify pattern: q1 = [x1, 0, -x1], q2 = [0, x2, -x2]
    x1, x2, x3 = q
    expected_q1 = np.array([x1, 0, -x1])
    expected_q2 = np.array([0, x2, -x2])

    assert np.array_equal(q1, expected_q1), f"q1 pattern wrong: {q1} != {expected_q1}"
    assert np.array_equal(q2, expected_q2), f"q2 pattern wrong: {q2} != {expected_q2}"


def test_coordinate_rotations(strategy):
    """Test that coordinate rotations work correctly."""
    v = np.array([10, 20, 30])

    # Rotation 0: no change
    assert np.array_equal(strategy._rotate_vector(v, 0), [10, 20, 30])

    # Rotation 1: right shift by 1
    assert np.array_equal(strategy._rotate_vector(v, 1), [30, 10, 20])

    # Rotation 2: right shift by 2
    assert np.array_equal(strategy._rotate_vector(v, 2), [20, 30, 10])


def test_flattening_biennial_budget(strategy):
    """Test flattening of biennial budgets."""
    year1 = (30, 40, 30)
    year2 = (20, 50, 30)

    flattened = strategy._flatten_biennial_budget(year1, year2)

    assert flattened == [30, 40, 30, 20, 50, 30]
    assert len(flattened) == 6


def test_with_zero_values(strategy):
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


def test_pair_count_by_groups(strategy):
    """Test that we get correct number of pairs per group."""
    user_vector = (25, 35, 40)
    pairs = strategy.generate_pairs(user_vector, n=12, vector_size=3)

    # Count pairs by group
    group_counts = {}
    for pair in pairs:
        group = pair["group_number"]
        group_counts[group] = group_counts.get(group, 0) + 1

    # Should have 6 pairs per group (2 groups × 3 rotations × 2 variants = 12)
    assert len(group_counts) == 2
    for count in group_counts.values():
        assert count == 6  # Each group has 6 pairs


def test_positive_and_negative_variants(strategy):
    """Test that both positive and negative variants are generated."""
    user_vector = (30, 30, 40)
    pairs = strategy.generate_pairs(user_vector, n=12, vector_size=3)

    positive_count = sum(1 for pair in pairs if pair["variant"] == "positive")
    negative_count = sum(1 for pair in pairs if pair["variant"] == "negative")

    # Should have 6 positive and 6 negative (2 groups × 3 rotations)
    assert positive_count == 6
    assert negative_count == 6


def test_edge_case_vectors(strategy):
    """Test strategy with edge case user vectors."""
    # Test with extreme distributions
    extreme_vector = (5, 5, 90)
    pairs = strategy.generate_pairs(extreme_vector, n=12, vector_size=3)
    assert len(pairs) == 12

    # Test with more balanced distribution
    balanced_vector = (30, 35, 35)
    pairs = strategy.generate_pairs(balanced_vector, n=12, vector_size=3)
    assert len(pairs) == 12


def test_all_valid_vectors_generate_pairs(strategy):
    """
    Test that ALL valid non-zero vectors successfully generate 12 pairs.

    This ensures the algorithm is complete for the entire valid constraint space.
    """
    print("\n=== COMPREHENSIVE ALGORITHM VALIDATION ===")

    valid_vectors = enumerate_all_valid_vectors()
    assert (
        len(valid_vectors) == EXPECTED_VALID_VECTORS
    ), f"Expected {EXPECTED_VALID_VECTORS} valid vectors, got {len(valid_vectors)}"

    print(f"Testing {len(valid_vectors)} valid non-zero vectors...")

    successful_vectors = []
    failed_vectors = []
    timing_results = []

    for i, user_vector in enumerate(valid_vectors, 1):
        if i % 20 == 0:
            print(f"Progress: {i}/{len(valid_vectors)} vectors tested...")

        try:
            start_time = time.time()
            pairs = strategy.generate_pairs(user_vector, n=12, vector_size=3)
            elapsed = time.time() - start_time

            # Basic validation
            if len(pairs) != 12:
                failed_vectors.append(
                    (user_vector, f"Generated {len(pairs)} pairs, expected 12")
                )
                continue

            # Performance validation
            if elapsed >= PERFORMANCE_TIMEOUT:
                failed_vectors.append((user_vector, f"Too slow: {elapsed:.2f}s"))
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
                continue

            # All validations passed
            successful_vectors.append(user_vector)
            timing_results.append((user_vector, elapsed))

        except Exception as e:
            failed_vectors.append((user_vector, str(e)))

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
        print(f"Timing: avg={avg_time:.3f}s, min={min_time:.3f}s, max={max_time:.3f}s")

    # Report failures
    if failed_vectors:
        print(f"\n❌ ALGORITHM FAILURES ({len(failed_vectors)}):")
        for vec, error in failed_vectors[:5]:
            print(f"  {vec}: {error}")
        if len(failed_vectors) > 5:
            print(f"  ... and {len(failed_vectors) - 5} more")

    # STRICT REQUIREMENTS
    assert total_successful == total_tested, (
        f"ALGORITHMIC INCOMPLETENESS: Only {total_successful}/{total_tested} "
        f"vectors succeeded. Algorithm must work for 100% of valid vectors."
    )

    assert (
        success_rate == 100.0
    ), f"Success rate {success_rate:.1f}% is below requirement of 100%"

    if timing_results:
        assert avg_time < MAX_GENERATION_TIME, (
            f"Average time {avg_time:.2f}s exceeds performance requirement "
            f"of {MAX_GENERATION_TIME}s"
        )

    print("✅ COMPREHENSIVE VALIDATION COMPLETE: All 171 valid vectors passed!")


def test_option_labels(strategy):
    """Test option labels generation."""
    labels = strategy.get_option_labels()
    assert labels == ("Concentrated Change", "Distributed Change")


def test_table_columns(strategy):
    """Test table columns definition."""
    columns = strategy.get_table_columns()

    assert isinstance(columns, dict)
    assert "concentrated_preference" in columns
    assert "distributed_preference" in columns
    assert "triangle_consistency" in columns

    # Check column properties
    for column_def in columns.values():
        assert "name" in column_def
        assert "type" in column_def
        assert column_def["type"] == "percentage"
        assert column_def.get("highlight") is True


def test_is_ranking_based(strategy):
    """Test that strategy correctly identifies as not ranking-based."""
    assert strategy.is_ranking_based() is False


def test_logging_behavior(strategy, caplog):
    """Test appropriate logging occurs."""
    user_vector = (20, 30, 50)

    with caplog.at_level("INFO"):
        strategy.generate_pairs(user_vector, n=12, vector_size=3)

    # Should log successful generation
    assert any("Generating" in record.message for record in caplog.records)
    assert any("triangle inequality" in record.message for record in caplog.records)


def test_zero_value_logging(strategy, caplog):
    """Test logging when zero values are detected."""
    user_vector_with_zero = (0, 40, 60)

    with caplog.at_level("INFO"):
        with pytest.raises(UnsuitableForStrategyError):
            strategy.generate_pairs(user_vector_with_zero, n=12, vector_size=3)

    # Should log the zero value detection
    assert any("zero values" in record.message for record in caplog.records)


def test_differences_represent_actual_changes(strategy):
    """Test that stored differences accurately represent the changes."""
    user_vector = (30, 30, 40)
    pairs = strategy.generate_pairs(user_vector, n=12, vector_size=3)

    for pair in pairs:
        # Get the vectors
        vector_keys = [k for k in pair.keys() if "Triangle" in k]
        assert len(vector_keys) == 2

        # Order vectors correctly based on name
        concentrated_key = next(k for k in vector_keys if "Concentrated" in k)
        distributed_key = next(k for k in vector_keys if "Distributed" in k)

        concentrated_vector = pair[concentrated_key]
        distributed_vector = pair[distributed_key]

        # For concentrated: Year 1 should be user_vector, Year 2 should have change
        year1_concentrated = np.array(concentrated_vector[:3])
        year2_concentrated = np.array(concentrated_vector[3:])

        # For distributed: Both years should have changes
        year1_distributed = np.array(distributed_vector[:3])
        year2_distributed = np.array(distributed_vector[3:])

        # Validate differences match actual changes
        diff_concentrated = np.array(pair["option1_differences"])
        diff_distributed = np.array(pair["option2_differences"])

        # Validate concentrated differences
        # Year 1 has no change, Year 2 has the change
        assert np.array_equal(diff_concentrated[:3], [0, 0, 0])
        assert np.array_equal(
            year2_concentrated - np.array(user_vector), diff_concentrated[3:]
        )

        # Validate distributed differences
        assert np.array_equal(
            year1_distributed - np.array(user_vector), diff_distributed[:3]
        )
        assert np.array_equal(
            year2_distributed - np.array(user_vector), diff_distributed[3:]
        )

        # Check Year 1 and Year 2 sums
        assert sum(year1_concentrated) == 100
        assert sum(year2_concentrated) == 100
        assert sum(year1_distributed) == 100
        assert sum(year2_distributed) == 100


def test_no_identical_pairs_generated(strategy):
    """
    Test that no identical pairs are generated.

    This is a critical regression test to catch the degenerate decomposition bug
    where q1 or q2 becomes [0, 0, 0], resulting in identical concentrated and
    distributed options.
    """
    user_vector = (60, 30, 10)

    # Run multiple times to catch probabilistic failures
    for run in range(5):
        pairs = strategy.generate_pairs(user_vector, n=12, vector_size=3)

        for i, pair in enumerate(pairs, 1):
            # Extract the two biennial budget vectors
            vector_keys = [k for k in pair.keys() if "Triangle" in k]
            assert (
                len(vector_keys) == 2
            ), f"Pair {i} should have exactly 2 Triangle vectors"

            concentrated = pair[vector_keys[0]]
            distributed = pair[vector_keys[1]]

            # Verify they are not identical
            assert concentrated != distributed, (
                f"Pair {i} (run {run + 1}) has identical options!\n"
                f"  Concentrated: {concentrated}\n"
                f"  Distributed: {distributed}\n"
                f"  Year 1: {concentrated[:3]} vs {distributed[:3]}\n"
                f"  Year 2: {concentrated[3:]} vs {distributed[3:]}\n"
                f"  This likely indicates a degenerate decomposition (q1 or q2 = [0,0,0])"
            )

            # Also verify at least one year differs between the two options
            year1_same = concentrated[:3] == distributed[:3]
            year2_same = concentrated[3:] == distributed[3:]

            assert not (year1_same and year2_same), (
                f"Pair {i} (run {run + 1}) has identical years in both options!\n"
                f"  Both have Year 1: {concentrated[:3]}\n"
                f"  Both have Year 2: {concentrated[3:]}"
            )


def test_decomposition_never_produces_zero_vectors(strategy):
    """
    Test that decomposition never produces q1=[0,0,0] or q2=[0,0,0].

    This validates that the degenerate case filtering is working correctly.
    """
    user_vector = (30, 40, 30)

    # Test multiple base vectors
    for _ in range(20):
        try:
            q = strategy._generate_base_change_vector(user_vector, 3)
            q1, q2 = strategy._decompose_change_vector(q)

            # Verify neither component is the zero vector
            assert not np.all(q1 == 0), f"q1 is zero vector! q={q}, q1={q1}, q2={q2}"
            assert not np.all(q2 == 0), f"q2 is zero vector! q={q}, q1={q1}, q2={q2}"

            # Verify decomposition correctness
            assert np.allclose(q1 + q2, q), (
                f"Decomposition incorrect: q1 + q2 != q\n" f"  q={q}, q1={q1}, q2={q2}"
            )
        except ValueError as e:
            # This is expected for degenerate cases - they should be caught and raised
            assert "Degenerate decomposition" in str(e), f"Unexpected ValueError: {e}"
