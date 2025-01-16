"""Test suite for base pair generation strategy."""

import pytest

from application.services.pair_generation.base import PairGenerationStrategy


# Create concrete class for testing abstract base
class TestStrategy(PairGenerationStrategy):
    def generate_pairs(self, user_vector, n, vector_size):
        return []

    def get_strategy_name(self):
        return "test_strategy"

    def get_option_labels(self):
        return ("Option 1", "Option 2")


@pytest.fixture
def strategy():
    return TestStrategy()


def test_create_random_vector(strategy):
    """Test if create_random_vector generates valid vectors."""
    vector = strategy.create_random_vector()
    assert sum(vector) == 100
    assert all(v % 5 == 0 for v in vector)
    assert len(vector) == 3


@pytest.mark.parametrize("size", [3, 4, 5])
def test_create_random_vector_different_sizes(strategy, size):
    """Test if create_random_vector works with different vector sizes."""
    vector = strategy.create_random_vector(size)
    assert sum(vector) == 100
    assert all(v % 5 == 0 for v in vector)
    assert len(vector) == size


def test_generate_vector_pool(strategy):
    """Test if vector pool generation works correctly."""
    pool = strategy.generate_vector_pool(5, 3)
    assert len(pool) <= 5
    assert all(sum(v) == 100 for v in pool)
    assert all(all(x % 5 == 0 for x in v) for v in pool)
