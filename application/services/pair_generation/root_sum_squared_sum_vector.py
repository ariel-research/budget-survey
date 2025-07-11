"""Implementation of root sum squared vs sum differences strategy."""

import logging
from typing import Dict, Tuple

import numpy as np

from application.services.pair_generation.optimization_metrics_vector import (
    OptimizationMetricsStrategy,
)
from application.translations import get_translation

logger = logging.getLogger(__name__)


class RootSumSquaredSumStrategy(OptimizationMetricsStrategy):
    """
    Strategy comparing root of sum of squared differences vs regular sum of differences.

    This strategy generates pairs where one option minimizes the root of sum of squared
    differences while the other minimizes the regular sum of absolute differences.
    A valid pair will have complementary properties: when one vector is better in
    root sum squared, it must be worse in regular sum, and vice versa.

    Example:
        For user_vector = (50, 25, 25):
        - Root Sum Squared Optimized Vector: 55.23 → (25, 70, 5)
            * RSS: 55.23, Sum Diff: 90
        - Sum Optimized Vector: 80 → (10, 25, 65)
            * RSS: 56.57, Sum Diff: 80
        Valid because:
            RSS₁ (55.23) < RSS₂ (56.57) AND SumDiff₁ (90) > SumDiff₂ (80)
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
        Calculate both types of differences for a pair of vectors.

        Args:
            user_vector: Reference vector
            v1, v2: Vectors to compare

        Returns:
            Tuple of (rss_1, rss_2, sum_1, sum_2) where:
            - rss_* is the root sum squared difference
            - sum_* is the regular sum of differences
        """
        rss1 = self.root_sum_squared_differences(user_vector, v1)
        rss2 = self.root_sum_squared_differences(user_vector, v2)
        sum1 = self.sum_of_differences(user_vector, v1)
        sum2 = self.sum_of_differences(user_vector, v2)
        return rss1, rss2, sum1, sum2

    def _is_valid_pair(self, metrics: Tuple[float, float, float, float]) -> bool:
        """
        Check if pair has complementary optimization properties.

        A valid pair is one where one vector is better in terms of root sum squared
        differences while the other is better in terms of regular sum of differences.

        Args:
            metrics: Tuple of (rss_1, rss_2, sum_1, sum_2)

        Returns:
            bool: True if pair shows valid optimization trade-off
        """
        rss1, rss2, sum1, sum2 = metrics
        return (rss1 < rss2 and sum1 > sum2) or (rss2 < rss1 and sum2 > sum1)

    def get_metric_types(self) -> tuple[str, str]:
        """Get the metric types used by this strategy."""
        return "rss", "sum"

    def get_strategy_name(self) -> str:
        """Get the unique identifier for this strategy."""
        return "root_sum_squared_sum"

    def get_option_labels(self) -> Tuple[str, str]:
        """Get the labels for the two types of optimization."""
        return ("Root Sum Squared", "Sum")

    def _get_metric_name(self, metric_type: str) -> str:
        if metric_type == "rss":
            return "Root Sum Squared Optimized Vector"
        elif metric_type == "sum":
            return "Sum Optimized Vector"
        return "Unknown Vector"

    def get_table_columns(self) -> Dict[str, Dict]:
        """
        Get column definitions for the survey response breakdown table.

        Returns:
            Dict with column definitions for Root Sum Squared and Sum columns.
        """
        return {
            "rss": {
                "name": get_translation("root_sum_squared", "answers"),
                "type": "percentage",
                "highlight": True,
            },
            "sum": {
                "name": get_translation("sum", "answers"),
                "type": "percentage",
                "highlight": True,
            },
        }
