"""
Generic ranking-based pair generation strategy.
Uses metric-based scoring and normalized ranking to select optimal pairs.
"""

import logging
from typing import Dict, List, Set, Tuple, Type

from application.services.algorithms.math_utils import simplex_points
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
