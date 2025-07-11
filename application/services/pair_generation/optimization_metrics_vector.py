"""Implementation of the optimization metrics pair generation strategy."""

import logging
import random
from typing import Dict, List, Tuple

import numpy as np

from application.services.pair_generation.base import PairGenerationStrategy
from application.translations import get_translation

logger = logging.getLogger(__name__)


class OptimizationMetricsStrategy(PairGenerationStrategy):
    """Strategy using optimization metrics for pair generation."""

    def sum_of_differences(self, user_vector: tuple, comparison_vector: tuple) -> int:
        """
        Calculate total absolute differences between two vectors.

        Args:
            user_vector: Reference vector
            comparison_vector: Vector to compare against

        Returns:
            int: Sum of absolute differences

        Example:
            >>> sum_of_differences((10, 20, 30), (15, 25, 35))
            15
        """
        return int(np.sum(np.abs(np.array(user_vector) - np.array(comparison_vector))))

    def minimal_ratio(self, user_vector: tuple, comparison_vector: tuple) -> float:
        """
        Calculate the minimal ratio between corresponding elements.

        Args:
            user_vector: Reference vector
            comparison_vector: Vector to compare against

        Returns:
            float: Minimum ratio between corresponding elements

        Example:
            >>> minimal_ratio((50, 30, 20), (30, 40, 30))
            0.6
        """
        ratios = np.array(comparison_vector) / np.array(user_vector)
        return float(np.min(ratios[np.isfinite(ratios)]))

    def _calculate_optimization_metrics(
        self, user_vector: tuple, v1: tuple, v2: tuple
    ) -> Tuple[float, float, float, float]:
        """
        Calculate optimization metrics for a pair of vectors against the user vector.

        Args:
            user_vector: Reference vector
            v1, v2: Vectors to compare

        Returns:
            Tuple of (sum_diff_1, sum_diff_2, ratio_1, ratio_2)
        """
        s1 = self.sum_of_differences(user_vector, v1)
        s2 = self.sum_of_differences(user_vector, v2)
        r1 = self.minimal_ratio(user_vector, v1)
        r2 = self.minimal_ratio(user_vector, v2)
        return s1, s2, r1, r2

    def _is_valid_pair(self, metrics: Tuple[float, float, float, float]) -> bool:
        """
        Check if pair has complementary optimization properties. A valid pair is one where
        neither vector dominates the other in both metrics (sum and ratio).

        A pair is considered to have complementary properties when:
        1. First vector has better sum (lower sum_diff) but worse ratio (lower ratio), OR
        2. Second vector has better sum but worse ratio

        This ensures that users must make a trade-off between optimizing for sum of
        differences or minimal ratio.

        Args:
            metrics: Tuple of (sum_diff_1, sum_diff_2, ratio_1, ratio_2)
                    where sum_diff_* represents the sum of differences from ideal vector
                    and ratio_* represents the minimal ratio to ideal vector

        Returns:
            bool: True if pair has valid optimization trade-off

        Example:
            # Case 1: v1 better in sum, worse in ratio (valid pair)
            >>> _is_valid_pair((30, 40, 0.6, 0.8))  # s1 < s2, r1 < r2
            True

            # Case 2: v2 better in sum, worse in ratio (valid pair)
            >>> _is_valid_pair((50, 30, 0.8, 0.5))  # s1 > s2, r1 > r2
            True

            # Case 3: v1 better in both metrics (invalid pair)
            >>> _is_valid_pair((30, 40, 0.8, 0.6))  # s1 < s2, r1 > r2
            False

            # Case 4: v2 better in both metrics (invalid pair)
            >>> _is_valid_pair((50, 30, 0.5, 0.8))  # s1 > s2, r1 < r2
            False
        """
        s1, s2, r1, r2 = metrics
        return (s1 < s2 and r1 < r2) or (s2 < s1 and r2 < r1)

    def _generate_pairs_attempt(
        self, user_vector: tuple, n: int, vector_size: int, attempt: int = 0
    ) -> List[Dict[str, tuple]]:
        """
        Helper function with recursion tracking.

        Returns:
            List[Dict[str, tuple]]: List of pairs with strategy descriptions
        """
        MAX_ATTEMPTS = 3
        POOL_MULTIPLIER = 20

        if attempt >= MAX_ATTEMPTS:
            msg = f"Failed to generate {n} valid pairs after {MAX_ATTEMPTS} attempts"
            logger.error(msg)
            raise ValueError(msg)

        # Generate vector pool
        pool_size = n * POOL_MULTIPLIER * (attempt + 1)
        logger.info(
            f"Attempting to generate pairs (attempt {attempt + 1}/{MAX_ATTEMPTS}, pool size: {pool_size})"
        )
        vector_pool = self.generate_vector_pool(pool_size, vector_size)

        # Find valid pairs
        valid_pairs = []
        vectors = list(vector_pool)

        for i in range(len(vectors)):
            for j in range(i + 1, len(vectors)):
                v1, v2 = vectors[i], vectors[j]
                metrics = self._calculate_optimization_metrics(user_vector, v1, v2)

                if self._is_valid_pair(metrics):
                    pair = self._create_pair_description(metrics, v1, v2)
                    valid_pairs.append(pair)

        logger.debug(f"Found {len(valid_pairs)} valid pairs")

        if len(valid_pairs) < n:
            logger.warning(
                f"Insufficient valid pairs (found: {len(valid_pairs)}, needed: {n}). Retrying with larger pool."
            )
            return self._generate_pairs_attempt(
                user_vector, n, vector_size, attempt + 1
            )

        selected_pairs = random.sample(valid_pairs, n)
        logger.info(f"Successfully generated {n} diverse pairs")
        return selected_pairs

    def generate_pairs(
        self, user_vector: tuple, n: int, vector_size: int
    ) -> List[Dict[str, tuple]]:
        """
        Generate pairs optimized for sum of differences and minimal ratio metrics.

        Each pair contains two vectors where one is better in terms of sum_of_differences
        while the other is better in terms of minimal_ratio.

        Args:
            user_vector: The user's ideal budget allocation
            n: Number of pairs to generate (default: 10)
            vector_size: Size of each vector (default: 3)

        Returns:
            List[Dict[str, tuple]]: List of pairs, each containing:
                {
                    'Sum Optimized Vector: X': sum_optimized_vector,
                    'Ratio Optimized Vector: Y': ratio_optimized_vector
                }
                where X is the sum difference and Y is the minimal ratio

        Raises:
            ValueError: If unable to generate enough valid pairs
        """
        try:
            pairs = self._generate_pairs_attempt(user_vector, n, vector_size)
            self._log_pairs(pairs)
            return pairs

        except Exception as e:
            logger.error(f"Pair generation failed: {str(e)}")
            raise

    def _create_pair_description(
        self, metrics: tuple[float, float, float, float], v1: tuple, v2: tuple
    ) -> dict[str, tuple]:
        """
        Create pair description with appropriate metrics.

        Args:
            metrics: Tuple of (m1_1, m1_2, m2_1, m2_2) where:
                    m1_* is the first metric for each vector
                    m2_* is the second metric for each vector
            v1, v2: The vectors to compare

        Returns:
            Dict containing vector descriptions and values
        """
        m1_1, m1_2, m2_1, m2_2 = metrics
        metric_type1, metric_type2 = self.get_metric_types()

        if m1_1 < m1_2:  # v1 is better in first metric
            return {
                self.get_option_description(
                    metric_type=metric_type1, best_value=m1_1, worst_value=m1_2
                ): v1,
                self.get_option_description(
                    metric_type=metric_type2, best_value=m2_2, worst_value=m2_1
                ): v2,
            }
        else:  # v2 is better in first metric
            return {
                self.get_option_description(
                    metric_type=metric_type1, best_value=m1_2, worst_value=m1_1
                ): v2,
                self.get_option_description(
                    metric_type=metric_type2, best_value=m2_1, worst_value=m2_2
                ): v1,
            }

    def get_metric_types(self) -> tuple[str, str]:
        """Get the metric types used by this strategy."""
        return "sum", "ratio"

    def get_strategy_name(self) -> str:
        """Get the unique identifier for this strategy."""
        return "optimization_metrics"

    def get_option_labels(self) -> Tuple[str, str]:
        """Get the unique labels for this strategy's options."""
        return ("Sum", "Ratio")

    def _get_metric_name(self, metric_type: str) -> str:
        if metric_type == "sum":
            return "Sum Optimized Vector"
        elif metric_type == "ratio":
            return "Ratio Optimized Vector"
        return "Unknown Vector"

    def get_table_columns(self) -> Dict[str, Dict]:
        """
        Get column definitions for the survey response breakdown table.

        Returns:
            Dict with column definitions for Sum and Ratio columns.
        """
        return {
            "sum": {
                "name": get_translation("sum", "answers"),
                "type": "percentage",
                "highlight": True,
            },
            "ratio": {
                "name": get_translation("ratio", "answers"),
                "type": "percentage",
                "highlight": True,
            },
        }
