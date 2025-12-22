"""
Generic ranking-based pair generation strategy.
Uses metric-based scoring and normalized ranking to select optimal pairs.
"""

import logging
from typing import Dict, List, Set, Tuple, Type

import numpy as np

from application.services.algorithms.math_utils import rankdata, simplex_points
from application.services.algorithms.metric_base import Metric
from application.services.pair_generation.base import PairGenerationStrategy

logger = logging.getLogger(__name__)


class GenericRankStrategy(PairGenerationStrategy):
    """
    A generic engine that generates pairs by comparing two metrics.
    It ranks all candidates in a grid using both metrics, then selects pairs
    that maximize the minimum rank (MaxMin).
    """

    def __init__(self, metric_a_class: Type[Metric], metric_b_class: Type[Metric]):
        """
        Initialize the strategy with two metric classes.

        Args:
            metric_a_class: Class for the first metric (e.g., L1Metric)
            metric_b_class: Class for the second metric (e.g., LeontiefMetric)
        """
        self.metric_a = metric_a_class()
        self.metric_b = metric_b_class()

    def generate_vector_pool(self, size: int, vector_size: int) -> Set[tuple]:
        """
        Generate a pool of vectors using a discrete simplex grid.

        Args:
            size: Used as the step size for the grid (default is 5).
                  If 5 doesn't provide enough options, a smaller step (like 1) can be used.
            vector_size: Number of elements in each vector.

        Returns:
            Set of unique vectors summing to 100 on a step=size grid.
        """
        step = size if size > 0 else 5
        pool = set(simplex_points(num_variables=vector_size, step=step))
        logger.debug(f"Generated simplex vector pool (step={step}) of size {len(pool)}")
        return pool

    def generate_pairs(
        self, user_vector: tuple, n: int, vector_size: int
    ) -> List[Dict[str, tuple]]:
        """
        Generate pairs based on the generic ranking logic.
        (Implementation will follow in Task 6).
        """
        # Placeholder for Task 4
        return []

    def _calculate_metrics(
        self, vector_pool: Set[tuple], user_vector: tuple
    ) -> Tuple[np.ndarray, np.ndarray, List[tuple]]:
        """
        Calculate raw metric scores for all vectors in the pool.

        Args:
            vector_pool: Set of candidate vectors.
            user_vector: The user's ideal vector.

        Returns:
            Tuple containing:
            - Array of scores for metric A
            - Array of scores for metric B
            - List of vectors (ordered corresponding to the arrays)

        Example:
            User Vector: (50, 50)
            Pool: [(50, 50), (100, 0)]

            Metric A (L1, returns negative distance):
                (50,50) vs (50,50)   -> dist=0   -> score=0
                (50,50) vs (100,0)   -> dist=100 -> score=-100

            Output:
                scores_a: [0, -100]
                scores_b: [1.0, 0.0] (assuming Leontief for B)
                pool_list: [(50, 50), (100, 0)]
        """
        # Convert set to list for stable ordering and indexing
        pool_list = list(vector_pool)

        scores_a = []
        scores_b = []

        for candidate in pool_list:
            scores_a.append(self.metric_a.calculate(user_vector, candidate))
            scores_b.append(self.metric_b.calculate(user_vector, candidate))

        return np.array(scores_a), np.array(scores_b), pool_list

    def _compute_ranks(
        self, scores_a: np.ndarray, scores_b: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Convert raw metric scores into normalized ranks (0.0 to 1.0).
        Higher rank indicates better match (closer to 1.0).

        Args:
            scores_a: Raw scores from metric A.
            scores_b: Raw scores from metric B.

        Returns:
            Tuple of (normalized_ranks_a, normalized_ranks_b)

        Example:
            Input (scores_a): [10, 20, 30] (N=3)

            Step 1 - Ordinal Rank (Smallest to Largest):
                10 -> Rank 1
                20 -> Rank 2
                30 -> Rank 3

            Step 2 - Normalization Formula: (Rank - 1) / (N - 1)
                Item 1: (1 - 1) / 2 = 0.0
                Item 2: (2 - 1) / 2 = 0.5
                Item 3: (3 - 1) / 2 = 1.0

            Output: [0.0, 0.5, 1.0]
        """
        n = len(scores_a)
        if n <= 1:
            # If only 0 or 1 item, rank is max (1.0)
            return np.ones(n), np.ones(n)

        # rankdata returns 1-based ranks (lowest score = 1, highest score = N)
        # Since metrics guarantee Higher Score = Better Match,
        # we can directly use rankdata to get ordinal ranks.
        raw_ranks_a = rankdata(scores_a)
        raw_ranks_b = rankdata(scores_b)

        # Normalize to 0-1 range: (rank - 1) / (N - 1)
        # Lowest rank (1) -> 0.0
        # Highest rank (N) -> 1.0
        norm_ranks_a = (raw_ranks_a - 1) / (n - 1)
        norm_ranks_b = (raw_ranks_b - 1) / (n - 1)

        return norm_ranks_a, norm_ranks_b

    def get_strategy_name(self) -> str:
        """Return unique identifier for this strategy."""
        # This will be overridden by concrete subclasses in Task 7/8
        return "generic_rank_strategy"

    def get_option_labels(self) -> Tuple[str, str]:
        """Return labels for the two options being compared."""
        return (self.metric_a.name, self.metric_b.name)

    def _get_metric_name(self, metric_type: str) -> str:
        """Get the display name for a metric type."""
        if metric_type == self.metric_a.metric_type:
            return self.metric_a.name
        if metric_type == self.metric_b.metric_type:
            return self.metric_b.name
        return metric_type
