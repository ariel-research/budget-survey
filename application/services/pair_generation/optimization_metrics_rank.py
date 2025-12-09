"""
Implementation of the rank-based optimization metrics pair generation strategy.

This strategy uses rank-based normalization (percentiles) with adaptive
relaxation to generate pairs with complementary trade-offs between
L1 distance and Leontief ratio.
"""

import logging
from typing import Dict, List, Tuple

import numpy as np

from application.services.pair_generation.base import PairGenerationStrategy
from application.translations import get_translation

logger = logging.getLogger(__name__)


def rankdata(a: np.ndarray, method: str = "average") -> np.ndarray:
    """
    Assign ranks to data, handling ties appropriately.

    This is a minimal implementation equivalent to scipy.stats.rankdata
    with method='average'.

    Args:
        a: Array of values to rank
        method: Method for handling ties ('average' supported)

    Returns:
        Array of ranks (1-based, same shape as input)
    """
    arr = np.asarray(a)
    sorter = np.argsort(arr)
    inv = np.empty(sorter.size, dtype=np.intp)
    inv[sorter] = np.arange(sorter.size, dtype=np.intp)

    if method == "average":
        # For average method, we need to handle ties
        arr_sorted = arr[sorter]
        obs = np.r_[True, arr_sorted[1:] != arr_sorted[:-1]]
        dense = obs.cumsum()[inv]

        # Count occurrences of each unique value
        count = np.r_[np.nonzero(obs)[0], len(obs)]

        # Calculate average ranks for tied values
        ranks = np.zeros(len(arr))
        for i in range(len(count) - 1):
            start_rank = count[i] + 1
            end_rank = count[i + 1]
            avg_rank = (start_rank + end_rank) / 2
            ranks[dense == (i + 1)] = avg_rank

        return ranks
    else:
        # Default ordinal ranking
        return inv.astype(float) + 1


class OptimizationMetricsRankStrategy(PairGenerationStrategy):
    """
    Strategy using rank-based normalization for pair generation.

    Instead of comparing raw L1 and Leontief values directly (which are
    on different scales), this strategy normalizes both metrics to
    percentile ranks (0.0 to 1.0). It then uses an adaptive relaxation
    mechanism to find pairs with complementary trade-offs.
    """

    # Constants validated in reference implementation
    POOL_SIZE = 2000
    TARGET_PAIRS = 12

    # Relaxation levels: (epsilon, balance_tolerance)
    # Start strict, progressively relax constraints if needed
    RELAXATION_LEVELS = [
        (0.15, 2.0),  # Level 1: Strict
        (0.10, 2.5),  # Level 2: Moderate
        (0.05, 4.0),  # Level 3: Loose
        (0.01, 6.0),  # Level 4: Last Resort
    ]

    def _calculate_l1_distance(
        self, user_vector: tuple, comparison_vector: tuple
    ) -> int:
        """
        Calculate L1 distance (sum of absolute differences).

        Args:
            user_vector: Reference vector
            comparison_vector: Vector to compare against

        Returns:
            int: Sum of absolute differences
        """
        diff = np.abs(np.array(user_vector) - np.array(comparison_vector))
        return int(np.sum(diff))

    def _calculate_leontief_ratio(
        self, user_vector: tuple, comparison_vector: tuple
    ) -> float:
        """
        Calculate the Leontief ratio (minimal ratio).

        Handles zero values in user_vector by skipping those components.

        Args:
            user_vector: Reference vector
            comparison_vector: Vector to compare against

        Returns:
            float: Min ratio between corresponding elements (skip zeros)
        """
        user_arr = np.array(user_vector, dtype=float)
        comp_arr = np.array(comparison_vector, dtype=float)

        # Create mask for non-zero user values to avoid division by zero
        non_zero_mask = user_arr > 0

        if not np.any(non_zero_mask):
            # All user values are zero - return 0 as worst case
            return 0.0

        ratios = comp_arr[non_zero_mask] / user_arr[non_zero_mask]
        return float(np.min(ratios))

    def _compute_ranks(
        self, l1_distances: np.ndarray, leontief_ratios: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Convert raw metrics to normalized percentile ranks.

        For L1 distance: Lower is better, so we invert the rank
        For Leontief ratio: Higher is better, so we use standard rank

        Args:
            l1_distances: Array of L1 distances
            leontief_ratios: Array of Leontief ratios

        Returns:
            Tuple of (l1_ranks, leontief_ranks) normalized to 0.0-1.0
        """
        n = len(l1_distances)

        # L1 rank: Invert because smaller L1 is better
        # rank gives 1 to smallest, n to largest
        # We want smallest L1 to have highest rank (close to 1.0)
        l1_raw_ranks = rankdata(l1_distances, method="average")
        l1_ranks = (n - l1_raw_ranks + 1) / n

        # Leontief rank: Standard because larger ratio is better
        leontief_raw_ranks = rankdata(leontief_ratios, method="average")
        leontief_ranks = leontief_raw_ranks / n

        return l1_ranks, leontief_ranks

    def _find_complementary_pairs(
        self,
        vectors: List[tuple],
        l1_ranks: np.ndarray,
        leontief_ranks: np.ndarray,
        target_pairs: int,
    ) -> List[Tuple[int, int, int, float, float]]:
        """
        Find pairs with complementary trade-offs using adaptive relaxation.

        A valid pair has one vector better in L1 rank and the other better
        in Leontief rank, with discrepancies within the tolerance.

        Args:
            vectors: List of candidate vectors
            l1_ranks: Normalized L1 ranks
            leontief_ranks: Normalized Leontief ranks
            target_pairs: Number of pairs to find

        Returns:
            List of tuples: (idx1, idx2, level, epsilon, balance_tolerance)
        """
        # Discrepancy: positive = better in L1, negative = better in Leontief
        discrepancies = l1_ranks - leontief_ranks

        found_pairs = []
        used_indices = set()

        for level_idx, (epsilon, balance_tol) in enumerate(self.RELAXATION_LEVELS, 1):
            if len(found_pairs) >= target_pairs:
                break

            # Type A: Better in L1 (positive discrepancy > epsilon)
            type_a_indices = np.where(discrepancies > epsilon)[0]
            # Type B: Better in Leontief (negative discrepancy < -epsilon)
            type_b_indices = np.where(discrepancies < -epsilon)[0]

            # Filter out already used indices
            type_a_available = [i for i in type_a_indices if i not in used_indices]
            type_b_available = [i for i in type_b_indices if i not in used_indices]

            # Try to match Type A with Type B
            for a_idx in type_a_available:
                if len(found_pairs) >= target_pairs:
                    break

                a_disc = discrepancies[a_idx]

                for b_idx in type_b_available:
                    if b_idx in used_indices:
                        continue

                    b_disc = discrepancies[b_idx]

                    # Check balance: ratio of absolute discrepancies
                    # should be within tolerance
                    if abs(b_disc) > 0.001:
                        ratio = abs(a_disc) / abs(b_disc)
                    else:
                        ratio = float("inf")

                    if 1 / balance_tol <= ratio <= balance_tol:
                        found_pairs.append(
                            (a_idx, b_idx, level_idx, epsilon, balance_tol)
                        )
                        used_indices.add(a_idx)
                        used_indices.add(b_idx)
                        break

            logger.debug(
                f"Level {level_idx} (epsilon={epsilon}, tol={balance_tol}): "
                f"Found {len(found_pairs)} pairs so far"
            )

        return found_pairs

    def generate_pairs(
        self, user_vector: tuple, n: int, vector_size: int
    ) -> List[Dict[str, tuple]]:
        """
        Generate pairs using rank-based normalization with adaptive relaxation.

        Args:
            user_vector: The user's ideal budget allocation
            n: Number of pairs to generate
            vector_size: Size of each vector

        Returns:
            List of dicts containing vectors and embedded __metadata__ key
            with generation level information

        Raises:
            ValueError: If unable to generate enough valid pairs
        """
        self._validate_vector(user_vector, vector_size)

        logger.info(
            f"Generating {n} pairs using rank-based strategy "
            f"for user_vector: {user_vector}"
        )

        # Generate pool of random vectors
        vector_pool = list(self.generate_vector_pool(self.POOL_SIZE, vector_size))

        # Calculate metrics for all vectors
        l1_distances = np.array(
            [self._calculate_l1_distance(user_vector, v) for v in vector_pool]
        )
        leontief_ratios = np.array(
            [self._calculate_leontief_ratio(user_vector, v) for v in vector_pool]
        )

        # Convert to normalized ranks
        l1_ranks, leontief_ranks = self._compute_ranks(l1_distances, leontief_ratios)

        # Find complementary pairs with adaptive relaxation
        pair_indices = self._find_complementary_pairs(
            vector_pool, l1_ranks, leontief_ranks, n
        )

        if len(pair_indices) < n:
            logger.warning(
                f"Only found {len(pair_indices)} valid pairs, requested {n}. "
                "Using all available pairs."
            )

        if len(pair_indices) == 0:
            raise ValueError(
                f"Failed to generate any valid pairs for " f"user_vector {user_vector}"
            )

        # Build result pairs with metadata
        result_pairs = []
        for idx_a, idx_b, level, epsilon, balance_tol in pair_indices[:n]:
            vec_a = vector_pool[idx_a]
            vec_b = vector_pool[idx_b]

            # Get actual metrics for description
            l1_a = l1_distances[idx_a]
            l1_b = l1_distances[idx_b]
            leo_a = leontief_ratios[idx_a]
            leo_b = leontief_ratios[idx_b]

            # Determine which is L1-optimized and which is Leontief-optimized
            if l1_a < l1_b:
                l1_vec, leo_vec = vec_a, vec_b
                l1_best, l1_worst = l1_a, l1_b
                leo_best, leo_worst = leo_b, leo_a
            else:
                l1_vec, leo_vec = vec_b, vec_a
                l1_best, l1_worst = l1_b, l1_a
                leo_best, leo_worst = leo_a, leo_b

            # Create pair with strategy descriptions
            pair = {
                self.get_option_description(
                    metric_type="sum", best_value=l1_best, worst_value=l1_worst
                ): l1_vec,
                self.get_option_description(
                    metric_type="ratio",
                    best_value=leo_best,
                    worst_value=leo_worst,
                ): leo_vec,
                # Embed metadata for pipeline to extract and persist
                "__metadata__": {
                    "level": level,
                    "epsilon": epsilon,
                    "balance_tolerance": balance_tol,
                },
            }
            result_pairs.append(pair)

            logger.info(
                f"Generated pair using Level {level} "
                f"(epsilon={epsilon}, balance_tol={balance_tol}): "
                f"L1={l1_best}/{l1_worst}, Leo={leo_best:.2f}/{leo_worst:.2f}"
            )

        self._log_pairs(result_pairs)
        return result_pairs

    def get_strategy_name(self) -> str:
        """Get the unique identifier for this strategy."""
        return "l1_vs_leontief_rank_comparison"

    def get_option_labels(self) -> Tuple[str, str]:
        """Get the unique labels for this strategy's options."""
        return ("Sum (Rank)", "Ratio (Rank)")

    def get_metric_types(self) -> Tuple[str, str]:
        """Get the metric types used by this strategy."""
        return "sum", "ratio"

    def _get_metric_name(self, metric_type: str) -> str:
        """Get the display name for a metric type."""
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
