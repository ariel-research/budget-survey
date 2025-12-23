"""
Concrete implementations of ranking-based pair generation strategies.
Defines specific metric combinations (e.g., L1 vs Leontief) used in surveys.
"""

import logging

from application.services.algorithms.metrics import L1Metric, LeontiefMetric
from application.services.pair_generation.generic_rank_strategy import (
    GenericRankStrategy,
)

logger = logging.getLogger(__name__)


class L1VsLeontiefRankStrategy(GenericRankStrategy):
    """
    Strategy comparing L1 distance (Sum) against Leontief ratio (Ratio).
    Replaces the original OptimizationMetricsRankStrategy using the generic engine.
    """

    def __init__(self, grid_step: int = None):
        """
        Initialize with L1 and Leontief metrics.

        Note: GenericRankStrategy defaults to step=5.
        """
        super().__init__(
            metric_a_class=L1Metric, metric_b_class=LeontiefMetric, grid_step=grid_step
        )
