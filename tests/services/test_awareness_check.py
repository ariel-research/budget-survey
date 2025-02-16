"""Test suite for awareness check functionality."""

import pytest

from application.services.awareness_check import (
    generate_awareness_check,
    generate_awareness_questions,
)


def test_generate_awareness_check():
    """Test if awareness check generation produces valid and distinct options."""
    user_vector = [95, 5, 0]
    result = generate_awareness_check(user_vector, 3)

    # Check structure
    assert "option1" in result
    assert "option2" in result
    assert "correct_answer" in result
    assert result["correct_answer"] == 2  # Correct is always option2

    # Validate options
    assert result["option2"] == user_vector  # option2 should be original vector
    assert result["option1"] != result["option2"]  # Options must be different
    assert sum(result["option1"]) == 100  # Sum must still be 100
    assert all(0 <= v <= 100 for v in result["option1"])  # Values in valid range
    assert all(v % 5 == 0 for v in result["option1"])  # Multiples of 5


@pytest.mark.parametrize(
    "user_vector, num_subjects", [([50, 50, 0], 3), ([40, 30, 30], 3), ([95, 5, 0], 3)]
)
def test_generate_awareness_check_various_inputs(user_vector, num_subjects):
    """Test awareness check generation with various valid inputs."""
    result = generate_awareness_check(user_vector, num_subjects)
    assert sum(result["option1"]) == 100
    assert sum(result["option2"]) == 100


def test_generate_awareness_questions():
    """Test generation of multiple awareness questions."""
    user_vector = [60, 20, 20]
    questions = generate_awareness_questions(user_vector, 3)

    # Verify structure
    assert len(questions) == 2, "Should generate exactly 2 questions"
    for q in questions:
        assert "option1" in q
        assert "option2" in q
        assert "correct_answer" in q
        assert q["correct_answer"] == 2
        assert q["option2"] == user_vector
        assert sum(q["option1"]) == 100
        assert all(0 <= v <= 95 for v in q["option1"])

    # Verify questions are different
    assert questions[0]["option1"] != questions[1]["option1"]


def test_awareness_questions_validation():
    """Test validation constraints for awareness questions."""
    # Test with incorrect number of subjects
    with pytest.raises(ValueError):
        generate_awareness_questions([50, 50], 3)  # Wrong vector length

    # Test vector sum not 100
    with pytest.raises(ValueError):
        generate_awareness_questions([40, 40, 40], 3)  # Sum exceeds 100
