import os
import sys

# Add the parent directory to the system path to allow importing from the backend module.
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

import pytest

from utils.generate_examples import (
    create_random_vector,
    generate_user_example,
    get_user_vector_str,
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


def test_get_user_vector_str():
    """Test if get_user_vector_str formats the vector correctly."""
    user_vector = (10, 20, 70)
    assert get_user_vector_str(user_vector) == "-10-20-70"


def test_generate_user_example():
    """Test if generate_user_example produces the expected number of edges."""
    user_vector = (10, 20, 70)
    edges = generate_user_example(user_vector, n=5, plot=False, save_txt=False)
    assert len(edges) == 5
    assert all(isinstance(edge, tuple) and len(edge) == 2 for edge in edges)
