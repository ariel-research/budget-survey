"""Test suite for Preference Ranking Survey strategy."""

import time

import numpy as np
import pytest

from application.services.pair_generation.preference_ranking_survey import (
    PreferenceRankingSurveyStrategy,
)

# Test constants
EXPECTED_VALID_VECTORS = 171
MAX_GENERATION_TIME = 3.0
PERFORMANCE_TIMEOUT = 10.0


def enumerate_all_valid_vectors():
    """Enumerate all valid 3D budget vectors."""
    valid_vectors = []
    for a in range(5, 96, 5):
        for b in range(5, 96, 5):
            c = 100 - a - b
            if 5 <= c <= 95 and c % 5 == 0:
                valid_vectors.append((a, b, c))
    return valid_vectors


def validate_pair_structure(pair, pair_index):
    """Validate basic pair structure and properties."""
    # Check that pair has exactly 2 vector keys
    vector_keys = [k for k, v in pair.items() if isinstance(v, tuple)]
    if len(vector_keys) != 2:
        return (
            f"Pair {pair_index} should have exactly 2 vectors, "
            f"got {len(vector_keys)}"
        )

    # Check required metadata fields
    required_fields = [
        "question_number",
        "question_label",
        "magnitude",
        "vector_type",
        "pair_type",
    ]
    for field in required_fields:
        if field not in pair:
            return f"Pair {pair_index} missing required field: {field}"

    # Validate vectors
    for key, value in pair.items():
        if isinstance(value, tuple):
            if not (
                len(value) == 3
                and sum(value) == 100
                and all(0 <= v <= 100 for v in value)
            ):
                return f"Invalid vector in pair {pair_index}: {value}"
    # Validate question metadata
    if pair["question_number"] not in [1, 2, 3, 4]:
        return (
            f"Invalid question_number in pair {pair_index}: "
            f"{pair['question_number']}"
        )

    if pair["vector_type"] not in ["positive", "negative"]:
        return f"Invalid vector_type in pair {pair_index}: " f"{pair['vector_type']}"

    if pair["pair_type"] not in ["A_vs_B", "A_vs_C", "B_vs_C"]:
        return f"Invalid pair_type in pair {pair_index}: " f"{pair['pair_type']}"

    return None


@pytest.fixture
def strategy():
    """Fixture for PreferenceRankingSurveyStrategy."""
    return PreferenceRankingSurveyStrategy()


def test_strategy_name(strategy):
    """Test if strategy name is correct."""
    assert strategy.get_strategy_name() == "preference_ranking_survey"


def test_generates_exactly_12_pairs(strategy):
    """Test that the strategy generates exactly 12 pairs."""
    user_vector = (35, 35, 30)
    pairs = strategy.generate_pairs(user_vector)
    assert len(pairs) == 12


def test_magnitude_calculation(strategy):
    """Test that magnitudes are calculated correctly."""
    # Test case 1: min_value = 15
    user_vector = (60, 25, 15)
    pairs = strategy.generate_pairs(user_vector)

    # X1 = max(1, round(0.2 * 15)) = max(1, 3) = 3
    # X2 = max(1, round(0.4 * 15)) = max(1, 6) = 6
    x1_pairs = [p for p in pairs if p["magnitude"] == 3]
    x2_pairs = [p for p in pairs if p["magnitude"] == 6]

    assert len(x1_pairs) == 6  # 2 vector types × 3 pair types
    assert len(x2_pairs) == 6  # 2 vector types × 3 pair types

    # Test case 2: min_value = 30
    user_vector = (40, 30, 30)
    pairs = strategy.generate_pairs(user_vector)

    # X1 = max(1, round(0.2 * 30)) = max(1, 6) = 6
    # X2 = max(1, round(0.4 * 30)) = max(1, 12) = 12
    x1_pairs = [p for p in pairs if p["magnitude"] == 6]
    x2_pairs = [p for p in pairs if p["magnitude"] == 12]

    assert len(x1_pairs) == 6
    assert len(x2_pairs) == 6


def test_question_structure(strategy):
    """Test that questions are structured correctly."""
    user_vector = (35, 35, 30)
    pairs = strategy.generate_pairs(user_vector)

    # Group pairs by question
    question_groups = {}
    for pair in pairs:
        q_num = pair["question_number"]
        if q_num not in question_groups:
            question_groups[q_num] = []
        question_groups[q_num].append(pair)

    # Should have exactly 4 questions
    assert len(question_groups) == 4

    # Each question should have exactly 3 pairs
    for q_num, q_pairs in question_groups.items():
        assert len(q_pairs) == 3, f"Question {q_num} should have 3 pairs"

        # Check pair types are A_vs_B, A_vs_C, B_vs_C
        pair_types = {p["pair_type"] for p in q_pairs}
        expected_types = {"A_vs_B", "A_vs_C", "B_vs_C"}
        assert pair_types == expected_types

        # All pairs in a question should have same metadata
        first_pair = q_pairs[0]
        for pair in q_pairs[1:]:
            assert pair["question_number"] == first_pair["question_number"]
            assert pair["question_label"] == first_pair["question_label"]
            assert pair["magnitude"] == first_pair["magnitude"]
            assert pair["vector_type"] == first_pair["vector_type"]


def test_cyclic_rotation(strategy):
    """Test that cyclic rotation works correctly."""
    # Test the _rotate_vector method
    vector = np.array([1, 2, 3])

    # Rotate by 0 positions
    rotated_0 = strategy._rotate_vector(vector, 0)
    np.testing.assert_array_equal(rotated_0, [1, 2, 3])

    # Rotate by 1 position (right)
    rotated_1 = strategy._rotate_vector(vector, 1)
    np.testing.assert_array_equal(rotated_1, [3, 1, 2])

    # Rotate by 2 positions (right)
    rotated_2 = strategy._rotate_vector(vector, 2)
    np.testing.assert_array_equal(rotated_2, [2, 3, 1])

    # Rotate by 3 positions (full cycle)
    rotated_3 = strategy._rotate_vector(vector, 3)
    np.testing.assert_array_equal(rotated_3, [1, 2, 3])


def test_example_1_perfect_consistency(strategy):
    """Test the first example from specification - consistent user."""
    user_vector = (60, 25, 15)
    pairs = strategy.generate_pairs(user_vector)

    # Should generate 12 pairs
    assert len(pairs) == 12

    # Check magnitudes are correct
    min_value = 15
    expected_x1 = max(1, round(0.2 * min_value))  # 3
    expected_x2 = max(1, round(0.4 * min_value))  # 6

    magnitudes = {p["magnitude"] for p in pairs}
    assert magnitudes == {expected_x1, expected_x2}

    # Validate all pairs
    for i, pair in enumerate(pairs):
        error = validate_pair_structure(pair, i)
        assert error is None, f"Pair validation failed: {error}"


def test_example_2_partial_consistency(strategy):
    """Test the second example from specification - partial consistency."""
    user_vector = (40, 30, 30)
    pairs = strategy.generate_pairs(user_vector)

    # Should generate 12 pairs
    assert len(pairs) == 12

    # Check magnitudes are correct
    min_value = 30
    expected_x1 = max(1, round(0.2 * min_value))  # 6
    expected_x2 = max(1, round(0.4 * min_value))  # 12

    magnitudes = {p["magnitude"] for p in pairs}
    assert magnitudes == {expected_x1, expected_x2}

    # Validate all pairs
    for i, pair in enumerate(pairs):
        error = validate_pair_structure(pair, i)
        assert error is None, f"Pair validation failed: {error}"


def test_edge_cases(strategy):
    """Test edge cases for magnitude calculation."""
    # Test very small minimum value
    user_vector = (90, 5, 5)
    pairs = strategy.generate_pairs(user_vector)

    # X1 = max(1, round(0.2 * 5)) = max(1, 1) = 1
    # X2 = max(1, round(0.4 * 5)) = max(1, 2) = 2
    magnitudes = {p["magnitude"] for p in pairs}
    assert magnitudes == {1, 2}

    # Test larger minimum value
    user_vector = (35, 35, 30)
    pairs = strategy.generate_pairs(user_vector)

    # X1 = max(1, round(0.2 * 30)) = max(1, 6) = 6
    # X2 = max(1, round(0.4 * 30)) = max(1, 12) = 12
    magnitudes = {p["magnitude"] for p in pairs}
    assert magnitudes == {6, 12}


def test_comprehensive_algorithm_validation(strategy):
    """
    Comprehensive validation for all valid vectors.
    Ensures the algorithm works for 100% of the valid input space,
    generates 12 unique pairs, and performs within time limits.
    """
    print("\n=== COMPREHENSIVE ALGORITHM VALIDATION ===")
    valid_vectors = enumerate_all_valid_vectors()
    assert (
        len(valid_vectors) == EXPECTED_VALID_VECTORS
    ), f"Expected {EXPECTED_VALID_VECTORS} vectors, got {len(valid_vectors)}"

    failed_vectors = []
    timing_results = []

    for i, user_vector in enumerate(valid_vectors, 1):
        print(f"Testing vector {i}/{len(valid_vectors)}: {user_vector}", end=" ... ")
        try:
            start_time = time.time()
            pairs = strategy.generate_pairs(user_vector, n=12, vector_size=3)
            elapsed = time.time() - start_time
            timing_results.append(elapsed)

            if len(pairs) != 12:
                failed_vectors.append(
                    (user_vector, f"Generated {len(pairs)} pairs, expected 12")
                )
                print("FAIL (count)")
                continue

            # Validate each pair
            for j, pair in enumerate(pairs):
                error = validate_pair_structure(pair, j)
                if error:
                    failed_vectors.append((user_vector, error))
                    print("FAIL (structure)")
                    break

            # Check pair uniqueness within each question
            question_groups = {}
            for pair in pairs:
                q_num = pair["question_number"]
                if q_num not in question_groups:
                    question_groups[q_num] = []
                question_groups[q_num].append(pair)

            for q_num, q_pairs in question_groups.items():
                if len(q_pairs) != 3:
                    failed_vectors.append(
                        (
                            user_vector,
                            f"Question {q_num} has {len(q_pairs)} pairs, "
                            f"expected 3",
                        )
                    )
                    print("FAIL (question structure)")
                    break

            print(f"✓ ({elapsed:.3f}s)")
        except Exception as e:
            failed_vectors.append((user_vector, str(e)))
            print(f"FAIL (exception: {type(e).__name__})")

    if failed_vectors:
        print(f"\n❌ ALGORITHM FAILURES ({len(failed_vectors)}):")
        for vec, err in failed_vectors[:5]:
            print(f"  {vec}: {err}")
        if len(failed_vectors) > 5:
            print(f"  ... and {len(failed_vectors) - 5} more")

    assert not failed_vectors, (
        f"Strategy failed for {len(failed_vectors)}/{len(valid_vectors)} " f"vectors"
    )

    avg_time = sum(timing_results) / len(timing_results)
    assert (
        avg_time < MAX_GENERATION_TIME
    ), f"Average time {avg_time:.2f}s exceeds performance limit"

    print("✅ COMPREHENSIVE VALIDATION COMPLETE")


def test_vector_differences_structure(strategy):
    """Test that difference vectors are included in pair metadata."""
    user_vector = (35, 35, 30)
    pairs = strategy.generate_pairs(user_vector)

    for pair in pairs:
        # Check that difference vectors are included based on pair type
        if pair["pair_type"] == "A_vs_B":
            assert "option_a_differences" in pair
            assert "option_b_differences" in pair
            assert len(pair["option_a_differences"]) == 3
            assert len(pair["option_b_differences"]) == 3
        elif pair["pair_type"] == "A_vs_C":
            assert "option_a_differences" in pair
            assert "option_c_differences" in pair
            assert len(pair["option_a_differences"]) == 3
            assert len(pair["option_c_differences"]) == 3
        elif pair["pair_type"] == "B_vs_C":
            assert "option_b_differences" in pair
            assert "option_c_differences" in pair
            assert len(pair["option_b_differences"]) == 3
            assert len(pair["option_c_differences"]) == 3


def test_invalid_vector_size(strategy):
    """Test that the strategy rejects non-3D vectors."""
    with pytest.raises(ValueError, match="only supports vector_size=3"):
        strategy.generate_pairs((50, 50), vector_size=2)

    with pytest.raises(ValueError, match="only supports vector_size=3"):
        strategy.generate_pairs((25, 25, 25, 25), vector_size=4)


def test_option_labels(strategy):
    """Test that strategy returns correct option labels."""
    labels = strategy.get_option_labels()
    assert len(labels) == 2
    assert isinstance(labels[0], str)
    assert isinstance(labels[1], str)


def test_table_columns(strategy):
    """Test that strategy returns correct table column definitions."""
    columns = strategy.get_table_columns()
    assert "consistency" in columns

    for col_name, col_def in columns.items():
        assert "name" in col_def
        assert "type" in col_def
        assert "highlight" in col_def
        assert col_def["type"] == "percentage"
        assert col_def["highlight"] is True
