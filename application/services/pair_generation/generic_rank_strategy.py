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
from application.translations import get_translation

logger = logging.getLogger(__name__)


class GenericRankStrategy(PairGenerationStrategy):
    """
    A generic engine that generates pairs by comparing two metrics.
    It ranks all candidates in a grid using both metrics, then selects pairs
    that maximize the minimum rank (MaxMin).
    """

    # Step size for discrete simplex grid (5% increments)
    DEFAULT_GRID_STEP = 5

    def __init__(
        self,
        metric_a_class: Type[Metric],
        metric_b_class: Type[Metric],
        grid_step: int = None,
        min_component: int = 0,
    ):
        """
        Initialize the strategy with two metric classes.

        Args:
            metric_a_class: Class for the first metric (e.g., L1Metric)
            metric_b_class: Class for the second metric (e.g., LeontiefMetric)
            grid_step: Optional step size for grid generation. Defaults to DEFAULT_GRID_STEP.
            min_component: Minimum value required for each vector component (default 0).
                           Example: If 10, no category can have less than 10% budget.
        """
        self.metric_a = metric_a_class()
        self.metric_b = metric_b_class()
        self.grid_step = grid_step if grid_step is not None else self.DEFAULT_GRID_STEP
        self.min_component = min_component

    def generate_vector_pool(self, size: int, vector_size: int) -> Set[tuple]:
        """
        Generate a pool of vectors using a discrete simplex grid.

        Args:
            size: Used as the step size for the grid if > 0, else uses DEFAULT_GRID_STEP.
            vector_size: Number of elements in each vector.

        Returns:
            Set of unique vectors summing to 100 on a step=size grid.
        """
        step = size if size > 0 else self.DEFAULT_GRID_STEP
        pool = set(
            simplex_points(
                num_variables=vector_size, step=step, min_value=self.min_component
            )
        )
        logger.debug(
            f"Generated simplex vector pool (step={step}, min={self.min_component}) of size {len(pool)}"
        )
        return pool

    def generate_pairs(
        self, user_vector: tuple, n: int, vector_size: int
    ) -> List[Dict[str, tuple]]:
        """
        Generate pairs based on the generic ranking logic.

        Args:
            user_vector: The user's ideal budget allocation.
            n: Number of pairs to generate.
            vector_size: Size of each vector.

        Returns:
            List of dicts containing vectors and embedded __metadata__ key
            with score and strategy information.

        Note on __metadata__:
            The __metadata__ dictionary contains internal scoring details (e.g., "score")
            that are useful for analysis or debugging.
        """
        self._validate_vector(user_vector, vector_size)

        logger.info(
            f"Generating {n} pairs using GenericRankStrategy "
            f"for user_vector: {user_vector}"
        )

        # 1. Generate Pool
        vector_pool_set = self.generate_vector_pool(
            size=self.grid_step, vector_size=vector_size
        )

        # 2. Calculate Metrics
        scores_a, scores_b, pool_list = self._calculate_metrics(
            vector_pool_set, user_vector
        )

        # 3. Compute Ranks (Normalized 0-1)
        ranks_a, ranks_b = self._compute_ranks(scores_a, scores_b)

        # 4. Select Pairs (MaxMin Logic)
        pair_indices = self._select_pairs(pool_list, ranks_a, ranks_b, n)

        if len(pair_indices) < n:
            logger.warning(
                f"Only found {len(pair_indices)} valid pairs, "
                f"requested {n}. Using all available pairs."
            )

        if not pair_indices:
            raise ValueError(
                f"Failed to generate any valid pairs for user_vector {user_vector}"
            )

        # 5. Format Output
        result_pairs = []
        for idx_a, idx_b, score in pair_indices:
            pair = self._create_pair_output(
                pool_list[idx_a],
                pool_list[idx_b],
                score,
                scores_a[idx_a],
                scores_a[idx_b],
                scores_b[idx_a],
                scores_b[idx_b],
                ranks_a[idx_a] > ranks_a[idx_b],
            )
            result_pairs.append(pair)

        self._log_pairs(result_pairs)
        return result_pairs

    def _create_pair_output(
        self,
        vec_a: tuple,
        vec_b: tuple,
        score: float,
        score_a_a: float,
        score_a_b: float,
        score_b_a: float,
        score_b_b: float,
        vec_a_wins_metric_a: bool,
    ) -> Dict[str, tuple]:
        """
        Create the formatted pair dictionary with correct metric descriptions.

        Determines which vector represents the "Metric A" option and which represents
        the "Metric B" option based on rank comparison.

        Args:
            vec_a: First vector from the pair.
            vec_b: Second vector from the pair.
            score: The MaxMin score for this pair.
            score_a_a: Score of vec_a on Metric A.
            score_a_b: Score of vec_b on Metric A.
            score_b_a: Score of vec_a on Metric B.
            score_b_b: Score of vec_b on Metric B.
            vec_a_wins_metric_a: True if vec_a outranks vec_b on Metric A.

        Returns:
            Dict containing the two options with descriptive keys and metadata.
        """
        # Determine orientation: Which vector is better for Metric A?
        if vec_a_wins_metric_a:
            # vec_a is better on Metric A, vec_b is better on Metric B
            metric_a_vec, metric_b_vec = vec_a, vec_b

            # Metric A stats (Best = vec_a, Worst = vec_b)
            metric_a_best, metric_a_worst = score_a_a, score_a_b

            # Metric B stats (Best = vec_b, Worst = vec_a)
            metric_b_best, metric_b_worst = score_b_b, score_b_a
        else:
            # vec_b is better on Metric A, vec_a is better on Metric B
            metric_a_vec, metric_b_vec = vec_b, vec_a

            # Metric A stats (Best = vec_b, Worst = vec_a)
            metric_a_best, metric_a_worst = score_a_b, score_a_a

            # Metric B stats (Best = vec_a, Worst = vec_b)
            metric_b_best, metric_b_worst = score_b_a, score_b_b

        return {
            self.get_option_description(
                metric_type=self.metric_a.name,
                best_value=metric_a_best,
                worst_value=metric_a_worst,
            ): metric_a_vec,
            self.get_option_description(
                metric_type=self.metric_b.name,
                best_value=metric_b_best,
                worst_value=metric_b_worst,
            ): metric_b_vec,
            "__metadata__": {
                "score": round(float(score), 2),
                "strategy": "max_min_rank",
            },
        }

    def _select_pairs(
        self,
        vectors: List[tuple],
        ranks_a: np.ndarray,
        ranks_b: np.ndarray,
        target_pairs: int,
    ) -> List[Tuple[int, int, float]]:
        """
        Select optimal pairs based on rank analysis.

        Default implementation finds pairs maximizing the trade-off between the two
        metrics (MaxMin logic), identifying complementary candidates.

        Args:
            vectors: List of candidate vectors.
            ranks_a: Normalized ranks (0-1) for Metric A.
            ranks_b: Normalized ranks (0-1) for Metric B.
            target_pairs: Number of pairs to select.

        Returns:
            List of (index_a, index_b, score) tuples, sorted by score descending.
            Score is calculated as min(Gain_A, Gain_B).
        """
        n = len(vectors)
        candidates: List[Tuple[int, int, float]] = []

        # Iterate all pairs
        for i in range(n):
            for j in range(i + 1, n):
                # Calculate gain for Metric A (i vs j)
                # If positive, i is better than j on A
                gain_a = ranks_a[i] - ranks_a[j]

                # Calculate gain for Metric B (j vs i)
                # If positive, j is better than i on B
                gain_b = ranks_b[j] - ranks_b[i]

                if gain_a > 0 and gain_b > 0:
                    # i wins on A, j wins on B
                    score = min(gain_a, gain_b)
                    candidates.append((i, j, score))
                elif gain_a < 0 and gain_b < 0:
                    # j wins on A (gain_a is neg), i wins on B (gain_b is neg)
                    # We want positive gains
                    score = min(-gain_a, -gain_b)
                    candidates.append((j, i, score))

        # Sort by score descending
        candidates.sort(key=lambda x: x[2], reverse=True)

        selected: List[Tuple[int, int, float]] = []
        used_indices: Set[int] = set()

        for idx_a, idx_b, score in candidates:
            if len(selected) >= target_pairs:
                break
            if idx_a in used_indices or idx_b in used_indices:
                continue

            selected.append((idx_a, idx_b, score))
            used_indices.add(idx_a)
            used_indices.add(idx_b)

        return selected

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
        """
        Return unique identifier for this strategy.
        Dynamically generated from metric names.
        """
        return f"{self.metric_a.name}_vs_{self.metric_b.name}_rank_comparison"

    def get_option_labels(self) -> Tuple[str, str]:
        """
        Return human-readable labels for the two options being compared.
        Dynamically generated from metric names via the translation system.
        """
        return (
            f"{get_translation(self.metric_a.name, 'answers')} (Rank)",
            f"{get_translation(self.metric_b.name, 'answers')} (Rank)",
        )

    def get_table_columns(self) -> Dict[str, Dict]:
        """
        Get column definitions for the survey response breakdown table.
        Dynamically generated from metric names.
        """
        return {
            self.metric_a.name: {
                "name": get_translation(self.metric_a.name, "answers"),
                "type": "percentage",
                "highlight": True,
            },
            self.metric_b.name: {
                "name": get_translation(self.metric_b.name, "answers"),
                "type": "percentage",
                "highlight": True,
            },
        }

    def _get_metric_name(self, metric_identifier: str) -> str:
        """
        Get the display name for a metric.
        Matches by name first, then falls back to metric_type.
        """
        if metric_identifier == self.metric_a.name:
            label = get_translation(self.metric_a.name, "answers")
            return f"{label} Optimized Vector"

        if metric_identifier == self.metric_b.name:
            label = get_translation(self.metric_b.name, "answers")
            return f"{label} Optimized Vector"

        # Fallback to type check (for robust identification)
        if metric_identifier == self.metric_a.metric_type:
            label = get_translation(self.metric_a.name, "answers")
            return f"{label} Optimized Vector"

        if metric_identifier == self.metric_b.metric_type:
            label = get_translation(self.metric_b.name, "answers")
            return f"{label} Optimized Vector"

        return metric_identifier
