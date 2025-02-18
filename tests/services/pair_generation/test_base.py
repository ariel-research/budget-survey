"""Test suite for base pair generation strategy."""

import pytest

from application.services.pair_generation.base import PairGenerationStrategy


class TestStrategy(PairGenerationStrategy):
    def generate_pairs(self, user_vector, n, vector_size):
        """Generate test pairs with strategy descriptions."""
        vectors = list(self.generate_vector_pool(n * 2, vector_size))
        pairs = []
        for i in range(min(n, len(vectors) // 2)):
            pair = {
                self.get_option_description(type="random"): vectors[i * 2],
                self.get_option_description(type="test"): vectors[i * 2 + 1],
            }
            pairs.append(pair)
        return pairs

    def get_strategy_name(self):
        return "test_strategy"

    def get_option_labels(self):
        return ("Option 1", "Option 2")

    def get_option_description(self, **kwargs):
        type_str = kwargs.get("type", "default")
        return f"Test {type_str.capitalize()} Vector"

    def _get_metric_name(self, metric_type: str) -> str:
        """Get the display name for a metric type."""
        return f"Test {metric_type.capitalize()} Vector"


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


def test_generate_pairs_format(strategy):
    """Test if generated pairs have correct format with strategy descriptions."""
    pairs = strategy.generate_pairs((20, 30, 50), n=3, vector_size=3)

    assert isinstance(pairs, list), "Should return a list"
    assert len(pairs) == 3, "Should generate requested number of pairs"

    for pair in pairs:
        assert isinstance(pair, dict), "Each pair should be a dictionary"
        assert len(pair) == 2, "Each pair should have exactly two entries"

        # Check keys and values
        for key, value in pair.items():
            assert isinstance(key, str), "Strategy description should be string"
            assert isinstance(value, tuple), "Vector should be tuple"
            assert len(value) == 3, "Vector should have correct size"
            assert sum(value) == 100, "Vector should sum to 100"
            assert all(v % 5 == 0 for v in value), "All values should be multiples of 5"


def test_option_description_generation(strategy):
    """Test if option descriptions are generated correctly."""
    description1 = strategy.get_option_description(type="random")
    description2 = strategy.get_option_description(type="test")

    assert description1 == "Test Random Vector"
    assert description2 == "Test Test Vector"
    assert strategy.get_option_description() == "Test Default Vector"
