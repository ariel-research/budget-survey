import numpy as np

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


def test_generic_rank_strategy_calculate_metrics():
    """
    Test _calculate_metrics calculates scores for a pool of vectors.
    """
    strategy = GenericRankStrategy(L1Metric, LeontiefMetric)
    user_vector = (50, 50)
    pool = {(50, 50), (100, 0), (0, 100)}  # Set of tuples

    scores_a, scores_b, pool_list = strategy._calculate_metrics(pool, user_vector)

    assert len(scores_a) == 3
    assert len(scores_b) == 3
    assert len(pool_list) == 3
    assert isinstance(scores_a, np.ndarray)
    assert isinstance(scores_b, np.ndarray)

    # Find index of perfect match
    perfect_idx = pool_list.index((50, 50))

    # L1 metric: 0 distance -> score 0
    # L1: distance = |50-50| + |50-50| = 0. score = -0 = 0.
    assert scores_a[perfect_idx] == 0

    # Leontief: min(50/50, 50/50) = 1.0
    assert scores_b[perfect_idx] == 1.0


def test_generic_rank_strategy_compute_ranks():
    """
    Test _compute_ranks normalizes scores to 0.0-1.0 range correctly.
    """
    strategy = GenericRankStrategy(L1Metric, LeontiefMetric)

    # 5 scores: 10, 20, 30, 40, 50
    # Ranks: 1, 2, 3, 4, 5
    # Norm: 0, 0.25, 0.5, 0.75, 1.0
    scores_a = np.array([10, 20, 30, 40, 50])
    scores_b = np.array([5, 4, 3, 2, 1])  # Reverse order

    ranks_a, ranks_b = strategy._compute_ranks(scores_a, scores_b)

    expected_a = np.array([0.0, 0.25, 0.5, 0.75, 1.0])
    expected_b = np.array([1.0, 0.75, 0.5, 0.25, 0.0])

    np.testing.assert_allclose(ranks_a, expected_a)
    np.testing.assert_allclose(ranks_b, expected_b)


def test_generic_rank_strategy_compute_ranks_ties():
    """
    Test _compute_ranks handles ties by averaging.
    """
    strategy = GenericRankStrategy(L1Metric, LeontiefMetric)

    # Scores: 10, 20, 20, 30
    # Ranks (1-based): 1, 2.5, 2.5, 4
    # Norm (N=4): (r-1)/3 -> 0/3, 1.5/3, 1.5/3, 3/3 -> 0.0, 0.5, 0.5, 1.0
    scores = np.array([10, 20, 20, 30])

    ranks_a, ranks_b = strategy._compute_ranks(scores, scores)

    expected = np.array([0.0, 0.5, 0.5, 1.0])

    np.testing.assert_allclose(ranks_a, expected)
    np.testing.assert_allclose(ranks_b, expected)


def test_generic_rank_strategy_compute_ranks_single_item():
    """
    Test _compute_ranks handles single item pool (should be 1.0).
    """
    strategy = GenericRankStrategy(L1Metric, LeontiefMetric)
    scores = np.array([10])

    ranks_a, ranks_b = strategy._compute_ranks(scores, scores)

    assert ranks_a[0] == 1.0
    assert ranks_b[0] == 1.0
