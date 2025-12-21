from application.services.algorithms.metrics import L1Metric, LeontiefMetric
from application.services.pair_generation.generic_rank_strategy import (
    GenericRankStrategy,
)


def test_generic_rank_strategy_initialization():
    """
    Test that GenericRankStrategy can be initialized with two metric classes.
    """
    strategy = GenericRankStrategy(L1Metric, LeontiefMetric)
    assert isinstance(strategy.metric_a, L1Metric)
    assert isinstance(strategy.metric_b, LeontiefMetric)
    assert strategy.get_strategy_name() == "generic_rank_strategy"


def test_generic_rank_strategy_generate_vector_pool():
    """
    Test that GenericRankStrategy generates a valid vector pool using simplex_points,
    with configurable step (passed via 'size' parameter).
    """
    strategy = GenericRankStrategy(L1Metric, LeontiefMetric)
    vector_size = 3

    # Test default step=5
    pool_5 = strategy.generate_vector_pool(size=5, vector_size=vector_size)
    assert len(pool_5) > 0
    for vector in pool_5:
        assert len(vector) == vector_size
        assert sum(vector) == 100
        for val in vector:
            assert val % 5 == 0

    # Test step=1 (more options)
    pool_1 = strategy.generate_vector_pool(size=1, vector_size=vector_size)
    assert len(pool_1) > len(pool_5)
    for vector in pool_1:
        assert len(vector) == vector_size
        assert sum(vector) == 100


def test_generic_rank_strategy_option_labels():
    """
    Test that get_option_labels returns correct names.
    """
    strategy = GenericRankStrategy(L1Metric, LeontiefMetric)
    labels = strategy.get_option_labels()
    assert labels == ("l1", "leontief")


def test_generic_rank_strategy_metric_name_lookup():
    """
    Test that _get_metric_name correctly identifies metrics.
    """
    strategy = GenericRankStrategy(L1Metric, LeontiefMetric)
    assert strategy._get_metric_name("distance") == "l1"
    assert strategy._get_metric_name("ratio") == "leontief"
    assert strategy._get_metric_name("unknown") == "unknown"
