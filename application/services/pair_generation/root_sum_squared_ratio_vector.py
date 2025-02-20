"""Implementation of root sum squared vs minimal ratio strategy."""

import logging
from typing import Tuple

import numpy as np

from application.services.pair_generation.optimization_metrics_vector import (
    OptimizationMetricsStrategy,
)

logger = logging.getLogger(__name__)


class RootSumSquaredRatioStrategy(OptimizationMetricsStrategy):
    """
    Strategy comparing root of sum of squared differences vs minimal ratio.

    This strategy generates pairs where one option minimizes the root of sum of squared
    differences while the other maximizes the minimal ratio between corresponding elements.

    Example:
        For user_vector = (60, 25, 15):
        - Vector1 (50, 30, 20): Better minimal ratio
            * Root squared: sqrt((60-50)² + (25-30)² + (15-20)²) = sqrt(100 + 25 + 25) = 12.25
            * Min ratio: min(50/60, 30/25, 20/15) = min(0.83, 1.20, 1.33) = 0.83
        - Vector2 (65, 25, 10): Better root sum squared
            * Root squared: sqrt((60-65)² + (25-25)² + (15-10)²) = sqrt(25 + 0 + 25) = 7.07
            * Min ratio: min(65/60, 25/25, 10/15) = min(1.08, 1.00, 0.67) = 0.67
    """

    def root_sum_squared_differences(
        self, user_vector: tuple, comparison_vector: tuple
    ) -> float:
        """
        Calculate root of sum of squared differences between two vectors.

        Args:
            user_vector: Reference vector
            comparison_vector: Vector to compare against

        Returns:
            float: Square root of sum of squared differences
        """
        squared_diff = np.sum(
            np.square(np.array(user_vector) - np.array(comparison_vector))
        )
        return float(np.sqrt(squared_diff))

    def _calculate_optimization_metrics(
        self, user_vector: tuple, v1: tuple, v2: tuple
    ) -> Tuple[float, float, float, float]:
        """
        Calculate root sum squared difference and minimal ratio metrics.

        Args:
            user_vector: Reference vector
            v1, v2: Vectors to compare

        Returns:
            Tuple of (rss_1, rss_2, ratio_1, ratio_2) where:
            - rss_* is the root sum squared difference
            - ratio_* is the minimal ratio
        """
        rss1 = self.root_sum_squared_differences(user_vector, v1)
        rss2 = self.root_sum_squared_differences(user_vector, v2)
        ratio1 = self.minimal_ratio(user_vector, v1)
        ratio2 = self.minimal_ratio(user_vector, v2)
        return rss1, rss2, ratio1, ratio2

    def _is_valid_pair(self, metrics: Tuple[float, float, float, float]) -> bool:
        """
        Check if pair has complementary optimization properties.

        A valid pair is one where one vector is better in terms of root sum squared
        differences while the other is better in terms of minimal ratio.

        Args:
            metrics: Tuple of (rss_1, rss_2, ratio_1, ratio_2)

        Returns:
            bool: True if pair shows valid optimization trade-off
        """
        rss1, rss2, ratio1, ratio2 = metrics
        return (rss1 < rss2 and ratio1 < ratio2) or (rss2 < rss1 and ratio2 < ratio1)

    def get_metric_types(self) -> tuple[str, str]:
        """Get the metric types used by this strategy."""
        return "rss", "ratio"

    def get_strategy_name(self) -> str:
        """Get the unique identifier for this strategy."""
        return "root_sum_squared_ratio"

    def get_option_labels(self) -> Tuple[str, str]:
        """Get the labels for the two types of optimization."""
        return ("Root Sum Squared", "Ratio")

    def _get_metric_name(self, metric_type: str) -> str:
        if metric_type == "rss":
            return "Root Sum Squared Optimized Vector"
        elif metric_type == "ratio":
            return "Ratio Optimized Vector"
        return "Unknown Vector"
