"""Test suite for survey vector generator module."""

import pytest

from application.services.survey_vector_generator import (
    calculate_optimization_metrics,
    create_random_vector,
    generate_survey_pairs,
    generate_vector_pool,
    is_valid_pair,
    minimal_ratio,
    sum_of_differences,
)


def test_create_random_vector():
    """Test if create_random_vector generates valid vectors."""
    vector = create_random_vector()
    assert sum(vector) == 100
    assert all(v % 5 == 0 for v in vector)
    assert len(vector) == 3


@pytest.mark.parametrize("size", [3, 4, 5])
def test_create_random_vector_different_sizes(size):
    """Test if create_random_vector works with different vector sizes."""
    vector = create_random_vector(size)
    assert sum(vector) == 100
    assert all(v % 5 == 0 for v in vector)
    assert len(vector) == size


def test_sum_of_differences():
    """Test if sum_of_differences calculates correctly."""
    user_vector = (10, 20, 70)
    generated_vector = (15, 25, 60)
    assert sum_of_differences(user_vector, generated_vector) == 20


def test_minimal_ratio():
    """Test if minimal_ratio calculates correctly."""
    user_vector = (50, 30, 20)
    generated_vector = (30, 40, 30)
    assert minimal_ratio(user_vector, generated_vector) == 0.6


def test_calculate_optimization_metrics():
    """Test if optimization metrics are calculated correctly."""
    user_vector = (50, 30, 20)
    v1 = (30, 40, 30)
    v2 = (60, 20, 20)
    metrics = calculate_optimization_metrics(user_vector, v1, v2)
    assert len(metrics) == 4
    assert isinstance(metrics[0], (int, float))


def test_is_valid_pair():
    """Test if pair validation works correctly."""
    # Test case where first vector is better in sum, worse in ratio
    metrics = (30, 40, 0.6, 0.8)  # s1, s2, r1, r2
    assert is_valid_pair(metrics)

    # Test case where neither vector dominates
    metrics = (30, 40, 0.8, 0.6)
    assert not is_valid_pair(metrics)


def test_generate_vector_pool():
    """Test if vector pool generation works correctly."""
    pool = generate_vector_pool(5, 3)
    assert len(pool) <= 5
    assert all(sum(v) == 100 for v in pool)
    assert all(all(x % 5 == 0 for x in v) for v in pool)


def test_generate_survey_pairs():
    """Test if survey pair generation works correctly."""
    user_vector = (60, 20, 20)
    n_pairs = 5
    pairs = generate_survey_pairs(user_vector, n=n_pairs)

    assert len(pairs) == n_pairs
    assert all(len(pair) == 2 for pair in pairs)
    assert all(len(v) == 3 for pair in pairs for v in pair)
    assert all(sum(v) == 100 for pair in pairs for v in pair)


@pytest.mark.parametrize("n_pairs", [5, 10, 15])
def test_generate_survey_pairs_different_sizes(n_pairs):
    """Test if pair generation works with different numbers of pairs."""
    user_vector = (60, 20, 20)
    pairs = generate_survey_pairs(user_vector, n=n_pairs)
    assert len(pairs) == n_pairs


def test_generate_survey_pairs_error_handling():
    """Test if pair generation handles errors correctly."""
    invalid_vector = (0, 0, 0)
    with pytest.raises(ValueError):
        generate_survey_pairs(invalid_vector)
