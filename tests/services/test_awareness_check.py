"""Test suite for awareness check functionality."""

import pytest

from application.services.awareness_check import generate_awareness_check


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
