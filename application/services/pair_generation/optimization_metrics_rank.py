"""
Implementation of the rank-based optimization metrics pair generation strategy.

This strategy uses rank-based normalization (percentiles) with adaptive
relaxation to generate pairs with complementary trade-offs between
L1 distance and Leontief ratio.

Enumerates the discrete simplex (step=5) to ensure full coverage of corners,
edges, and centers of the vector space without sampling bias.
"""

import logging
import math
from typing import Dict, Generator, List, Optional, Set, Tuple

import numpy as np

from application.services.pair_generation.base import PairGenerationStrategy
from application.translations import get_translation

logger = logging.getLogger(__name__)


def simplex_points(
    num_variables: int,
    side_length: int = 100,
    step: int = 5,
    min_value: int = 0,
) -> Generator[Tuple[int, ...], None, None]:
    """
    Generate lattice points on a discrete simplex grid.

    Args:
        num_variables: Number of coordinates per vector.
        side_length: Total sum required across coordinates.
        step: Grid resolution.
        min_value: Minimum allowed value per coordinate (rounded up to step).

    Yields:
        Tuples that satisfy the simplex constraints.
    """
    if num_variables <= 0:
        raise ValueError("num_variables must be positive")
    if side_length % step != 0:
        raise ValueError(
            f"side_length ({side_length}) must be divisible by step ({step})"
        )

    total_steps = side_length // step
    min_steps_per_var = math.ceil(min_value / step)

    if num_variables * min_steps_per_var > total_steps:
        return

    def generate(
        vars_left: int, remaining_steps: int
    ) -> Generator[Tuple[int, ...], None, None]:
        if vars_left == 1:
            yield (remaining_steps * step,)
            return

        min_needed_for_rest = (vars_left - 1) * min_steps_per_var
        start = min_steps_per_var
        end = remaining_steps - min_needed_for_rest

        for steps_taken in range(start, end + 1):
            value = steps_taken * step
            for rest in generate(vars_left - 1, remaining_steps - steps_taken):
                yield (value,) + rest

    yield from generate(num_variables, total_steps)


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
    POOL_SIZE = 10000
    TARGET_PAIRS = 10
    STEP_SIZE = 5
    MIN_COMPONENT = 10
    MAX_COMPONENT = 100

    # Relaxation levels: (epsilon, balance_tolerance)
    # Start strict, progressively relax constraints if needed
    RELAXATION_LEVELS = [
        (0.25, 1.5),  # Level 1: Excellent separation
        (0.20, 2.0),  # Level 2: Strong separation
        (0.15, 3.0),  # Level 3: Moderate separation
        (0.10, 4.0),  # Level 4: Minimum viable signal
        (0.05, 5.0),  # Level 5: SAFETY NET
    ]

    def generate_vector_pool(self, size: int, vector_size: int) -> Set[tuple]:
        """
        Enumerate all valid vectors within the discrete simplex.

        Args:
            size: Ignored; kept for compatibility with the base signature.
            vector_size: Number of coordinates per vector.

        Returns:
            Set containing every lattice point (step=5) that sums to 100 and
            falls within the allowed min/max bounds.
        """
        _ = size
        simplex_iter = simplex_points(
            num_variables=vector_size,
            side_length=100,
            step=self.STEP_SIZE,
            min_value=self.MIN_COMPONENT,
        )

        vector_pool: Set[tuple] = {
            vector
            for vector in simplex_iter
            if all(
                self.MIN_COMPONENT <= value <= self.MAX_COMPONENT for value in vector
            )
        }

        if not vector_pool:
            raise ValueError(
                f"No valid vectors found for vector_size={vector_size} "
                f"with step={self.STEP_SIZE}"
            )

        logger.debug(
            "Generated full simplex vector pool of size %s for vector_size=%s",
            len(vector_pool),
            vector_size,
        )
        return vector_pool

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
        Find pairs with complementary trade-offs using Best-First Search.
        Scans all candidates and selects those with maximum metric separation.
        """
        discrepancies = l1_ranks - leontief_ranks
        found_pairs = []
        used_indices = set()

        # Iterate through relaxation levels
        for level_idx, (epsilon, balance_tol) in enumerate(self.RELAXATION_LEVELS, 1):
            if len(found_pairs) >= target_pairs:
                break

            # Identify all potential candidates for this level
            type_a_indices = np.where(discrepancies > epsilon)[0]
            type_b_indices = np.where(discrepancies < -epsilon)[0]

            # Store candidates with a quality score
            level_candidates = []

            for a_idx in type_a_indices:
                if a_idx in used_indices:
                    continue

                # Performance opt: Don't scan B's that are already used
                # We can filter type_b_indices dynamically if this is too slow,
                # but with 10k vectors, this nested loop is acceptable (~0.5s).

                a_disc = discrepancies[a_idx]

                for b_idx in type_b_indices:
                    if b_idx in used_indices or b_idx == a_idx:
                        continue
                    b_disc = discrepancies[b_idx]

                    # Check Balance Ratio
                    if abs(b_disc) > 0.001:
                        ratio = abs(a_disc) / abs(b_disc)
                    else:
                        ratio = float("inf")

                    if 1 / balance_tol <= ratio <= balance_tol:
                        # QUALITY METRIC: Total Separation
                        # We want pairs that are FAR apart in rank space.
                        # Score = (A's L1 advantage) + (B's Leontief advantage)
                        # This maximizes the trade-off clarity for the user.
                        score = (l1_ranks[a_idx] - l1_ranks[b_idx]) + (
                            leontief_ranks[b_idx] - leontief_ranks[a_idx]
                        )

                        level_candidates.append(
                            {
                                "indices": (a_idx, b_idx),
                                "meta": (level_idx, epsilon, balance_tol),
                                "score": score,
                            }
                        )

            # Sort candidates by score (Best First)
            # This ensures we pick the "Diamonds" from the pool,
            # not just the first matches.
            level_candidates.sort(key=lambda x: x["score"], reverse=True)

            # Select the best pairs, respecting usage constraints
            for cand in level_candidates:
                if len(found_pairs) >= target_pairs:
                    break

                a, b = cand["indices"]
                if a not in used_indices and b not in used_indices:
                    found_pairs.append((*cand["indices"], *cand["meta"]))
                    used_indices.add(a)
                    used_indices.add(b)

        return found_pairs

    def _generate_fallback_pairs(
        self,
        l1_ranks: np.ndarray,
        leontief_ranks: np.ndarray,
        target_pairs: int,
        excluded: Optional[Set[int]] = None,
    ) -> List[Tuple[int, int, int, float, float]]:
        """
        Deterministic fallback pairing when rank discrepancies collapse.

        Pairs best L1-ranked vectors with best Leontief-ranked vectors while
        respecting uniqueness constraints so we can still surface options.
        """
        if target_pairs <= 0:
            return []

        excluded = set(excluded or set())
        epsilon, balance_tol = self.RELAXATION_LEVELS[-1]
        level = len(self.RELAXATION_LEVELS)

        l1_order = np.argsort(-l1_ranks)
        leo_order = np.argsort(-leontief_ranks)

        pairs: List[Tuple[int, int, int, float, float]] = []
        leo_ptr = 0

        for a_idx in l1_order:
            if len(pairs) >= target_pairs or leo_ptr >= len(leo_order):
                break
            if a_idx in excluded:
                continue

            while leo_ptr < len(leo_order):
                b_idx = leo_order[leo_ptr]
                leo_ptr += 1
                if b_idx in excluded or b_idx == a_idx:
                    continue

                pairs.append((a_idx, b_idx, level, epsilon, balance_tol))
                excluded.update({a_idx, b_idx})
                break

        return pairs

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

        # Enumerate the simplex (step=5) to build the candidate pool
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
            used_indices = {idx for pair in pair_indices for idx in pair[:2]}
            fallback_pairs = self._generate_fallback_pairs(
                l1_ranks,
                leontief_ranks,
                n - len(pair_indices),
                excluded=used_indices,
            )
            pair_indices.extend(fallback_pairs)

        if len(pair_indices) < n:
            logger.warning(
                f"Only found {len(pair_indices)} valid pairs, "
                f"requested {n}. Using all available pairs."
            )

        if len(pair_indices) == 0:
            raise ValueError(
                "Failed to generate any valid pairs for " f"user_vector {user_vector}"
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
