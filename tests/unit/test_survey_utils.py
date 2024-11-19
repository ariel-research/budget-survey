import pytest

from utils.survey_utils import generate_awareness_check, is_valid_vector


def test_is_valid_vector():
    """
    Test is_valid_vector function with various input scenarios.
    Checks valid and invalid vectors, including edge cases.
    """
    assert is_valid_vector([50, 30, 20])
    assert not is_valid_vector([33, 33, 34])
    assert is_valid_vector([0, 0, 100])
    assert is_valid_vector([10, 20, 30, 40])
    assert not is_valid_vector([])
    assert not is_valid_vector([101])
    assert not is_valid_vector([50, 50, 1])


def test_generate_awareness_check():
    """
    Test generate_awareness_check function with a specific user vector.
    Verifies structure and content of the returned awareness check.
    """
    user_vector = [50, 30, 20]
    result = generate_awareness_check(user_vector, 3)

    assert isinstance(result, dict)
    assert "option1" in result
    assert "option2" in result
    assert "correct_answer" in result

    assert result["option2"] == user_vector
    assert result["correct_answer"] == 2
    assert sum(result["option1"]) == 100
    assert result["option1"] != user_vector


def test_generate_awareness_check_two_subjects():
    """
    Test generate_awareness_check function with the minimum number of subjects (2).
    Ensures correct behavior for the edge case of two subjects.
    """
    user_vector = [50, 50]
    result = generate_awareness_check(user_vector, 2)

    assert len(result["option1"]) == 2
    assert len(result["option2"]) == 2
    assert sum(result["option1"]) == 100
    assert sum(result["option2"]) == 100
    assert result["option2"] == user_vector
    assert result["option1"] != result["option2"]
    assert result["correct_answer"] == 2


@pytest.mark.parametrize("num_subjects", [3, 4, 5])
def test_generate_awareness_check_different_subjects(num_subjects):
    """
    Parameterized test for generate_awareness_check with different numbers of subjects.
    Verifies function behavior across various subject counts, ensuring consistent output structure and validity.
    """
    # Create a user vector that sums to 100 regardless of num_subjects
    user_vector = [100 // num_subjects] * (num_subjects - 1) + [
        100 - (100 // num_subjects) * (num_subjects - 1)
    ]
    result = generate_awareness_check(user_vector, num_subjects)

    assert len(result["option1"]) == num_subjects
    assert len(result["option2"]) == num_subjects
    assert sum(result["option1"]) == 100
    assert sum(result["option2"]) == 100
    assert result["option2"] == user_vector
    assert result["option1"] != result["option2"]
    assert result["correct_answer"] == 2
