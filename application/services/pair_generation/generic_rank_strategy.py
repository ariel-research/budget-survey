"""
Generic ranking-based pair generation strategy.
Uses utility-model-based scoring and normalized ranking to select optimal pairs.
"""

import logging
from typing import Dict, List, Set, Tuple, Type

import numpy as np

from application.services.algorithms.math_utils import (
    get_cached_simplex_pool,
    rankdata,
)
from application.services.algorithms.utility_model_base import UtilityModel
from application.services.pair_generation.base import PairGenerationStrategy
from application.translations import get_translation

logger = logging.getLogger(__name__)


class GenericRankStrategy(PairGenerationStrategy):
    """
    A generic engine that generates pairs by comparing two utility models.
    It ranks all candidates in a grid using both utility models, then selects pairs
    that maximize the minimum rank (MaxMin).
    """

    # Step size for discrete simplex grid (5% increments)
    DEFAULT_GRID_STEP = 5

    # Optimization constants for extreme vector detection
    CONCENTRATION_THRESHOLD = 70  # Max single-category % before relaxation
    RELAXATION_STEP = 5  # Step size for floor reduction
    HIGH_CONCENTRATION_CAP = 5  # Max floor allowed for concentrated vectors

    def __init__(
        self,
        utility_model_a_class: Type[UtilityModel],
        utility_model_b_class: Type[UtilityModel],
        grid_step: int = None,
        min_component: int = 10,
    ):
        """
        Initialize the strategy with two utility model classes.

        Args:
            utility_model_a_class: Class for the first utility model (e.g., L1UtilityModel)
            utility_model_b_class: Class for the second utility model (e.g., LeontiefUtilityModel)
            grid_step: Optional step size for grid generation. Defaults to DEFAULT_GRID_STEP.
            min_component: Minimum value required for each vector component (default 0).
                           Example: If 10, no category can have less than 10% budget.
        """
        self.utility_model_a = utility_model_a_class()
        self.utility_model_b = utility_model_b_class()
        self.grid_step = grid_step if grid_step is not None else self.DEFAULT_GRID_STEP
        self.min_component = min_component

    def generate_vector_pool(
        self, size: int, vector_size: int, min_val_override: int = None
    ) -> Set[tuple]:
        """
        Generate a pool of vectors using a discrete simplex grid.

        Args:
            size: Used as the step size for the grid if > 0, else uses DEFAULT_GRID_STEP.
            vector_size: Number of elements in each vector.
            min_val_override: Optional override for min_component.

        Returns:
            Set of unique vectors summing to 100 on a step=size grid.
        """
        step = size if size > 0 else self.DEFAULT_GRID_STEP
        min_val = (
            min_val_override if min_val_override is not None else self.min_component
        )
        pool = set(
            get_cached_simplex_pool(
                num_variables=vector_size,
                side_length=100,
                step=step,
                min_value=min_val,
            )
        )
        logger.debug(
            f"Generated simplex vector pool (step={step}, min={min_val}) of size {len(pool)}"
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

        # Retry logic for dynamic floor (min_component)
        # Start with configured min_component and reduce by 5 if generation fails
        # This handles extreme user vectors that cause correlation deadlocks

        # Optimization: If user vector is extreme (violates floor or highly
        # concentrated), start with a relaxed floor immediately.
        user_min = min(user_vector)
        user_max = max(user_vector)

        # We start relaxed if:
        # 1. User has a component below the required floor
        # 2. User has a very high concentration which cramps the space
        if user_min < self.min_component or user_max >= self.CONCENTRATION_THRESHOLD:
            # Start at the nearest valid step below their min or straight to 0
            start_min = (user_min // self.RELAXATION_STEP) * self.RELAXATION_STEP
            current_min = min(self.min_component, start_min)
            if user_max >= self.CONCENTRATION_THRESHOLD:
                current_min = min(current_min, self.HIGH_CONCENTRATION_CAP)
        else:
            current_min = self.min_component

        while True:
            try:
                msg = f"Attempting pair generation with min_component={current_min}"
                logger.debug(msg)

                # 1. Generate Pool
                vector_pool_set = self.generate_vector_pool(
                    size=self.grid_step,
                    vector_size=vector_size,
                    min_val_override=current_min,
                )

                # 2. Calculate Utility Scores
                scores_a, scores_b, pool_list = self._calculate_utility_scores(
                    vector_pool_set, user_vector
                )

                # 3. Compute Ranks (Normalized 0-1)
                ranks_a, ranks_b = self._compute_ranks(scores_a, scores_b)

                # 4. Select Pairs (MaxMin Logic)
                pair_indices = self._select_pairs(pool_list, ranks_a, ranks_b, n)

                if len(pair_indices) >= n:
                    # Found enough pairs, proceed to formatting
                    break

                # If we found some pairs but not enough, retry with relaxed floor.
                logger.info(
                    f"Only found {len(pair_indices)}/{n} pairs with "
                    f"min_component={current_min}. Attempting to relax."
                )

            except ValueError as e:
                logger.info(
                    f"Generation failed with min_component={current_min}: "
                    f"{str(e)}. Attempting to relax."
                )

            # Reduce floor and retry
            current_min -= self.RELAXATION_STEP
            if current_min < 0:
                # Exhausted all options
                logger.warning(
                    f"Failed to generate valid pairs even with "
                    f"min_component=0 for vector {user_vector}"
                )
                from application.exceptions import UnsuitableForStrategyError

                raise UnsuitableForStrategyError(
                    "Unable to generate suitable comparison pairs for the "
                    "provided preferences."
                )

        # 5. Format Output using the successful pair_indices
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

            # Add generation metadata
            if "__metadata__" not in pair:
                pair["__metadata__"] = {}
            pair["__metadata__"]["relaxed_min_component"] = current_min

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
        vec_a_wins_utility_a: bool,
    ) -> Dict[str, tuple]:
        """
        Create the formatted pair dictionary with correct utility model descriptions.

        Determines which vector represents the "Utility Model A" option and which represents
        the "Utility Model B" option based on rank comparison.

        Args:
            vec_a: First vector from the pair.
            vec_b: Second vector from the pair.
            score: The MaxMin score for this pair.
            score_a_a: Score of vec_a on Utility Model A.
            score_a_b: Score of vec_b on Utility Model A.
            score_b_a: Score of vec_a on Utility Model B.
            score_b_b: Score of vec_b on Utility Model B.
            vec_a_wins_utility_a: True if vec_a outranks vec_b on Utility Model A.

        Returns:
            Dict containing the two options with descriptive keys and metadata.
        """
        # Determine orientation: Which vector is better for Utility Model A?
        if vec_a_wins_utility_a:
            # vec_a is better on Utility Model A, vec_b is better on Utility Model B
            utility_a_vec, utility_b_vec = vec_a, vec_b

            # Utility Model A stats (Best = vec_a, Worst = vec_b)
            utility_a_best, utility_a_worst = score_a_a, score_a_b

            # Utility Model B stats (Best = vec_b, Worst = vec_a)
            utility_b_best, utility_b_worst = score_b_b, score_b_a
        else:
            # vec_b is better on Utility Model A, vec_a is better on Utility Model B
            utility_a_vec, utility_b_vec = vec_b, vec_a

            # Utility Model A stats (Best = vec_b, Worst = vec_a)
            utility_a_best, utility_a_worst = score_a_b, score_a_a

            # Utility Model B stats (Best = vec_a, Worst = vec_b)
            utility_b_best, utility_b_worst = score_b_a, score_b_b

        return {
            self.get_option_description(
                metric_type=self.utility_model_a.name,
                best_value=utility_a_best,
                worst_value=utility_a_worst,
            ): utility_a_vec,
            self.get_option_description(
                metric_type=self.utility_model_b.name,
                best_value=utility_b_best,
                worst_value=utility_b_worst,
            ): utility_b_vec,
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
        Select optimal pairs maximizing the 'MaxMin' trade-off between utility models.

        Identifies 'complementary' pairs where:
        1. Vector A is better on Utility Model A (positive Gain A).
        2. Vector B is better on Utility Model B (positive Gain B).
        3. The score is min(Gain A, Gain B), favoring balanced trade-offs.

        Example:
            - Pair 1: Gain A = 0.9, Gain B = 0.1 -> Score = 0.1 (Unbalanced, Low Rank)
            - Pair 2: Gain A = 0.5, Gain B = 0.5 -> Score = 0.5 (Balanced, High Rank)

        Args:
            vectors: List of candidate vectors.
            ranks_a: Normalized ranks (0-1) for Utility Model A.
            ranks_b: Normalized ranks (0-1) for Utility Model B.
            target_pairs: Number of pairs to select.

        Returns:
            List of (index_a, index_b, score) tuples, sorted by score descending.
        """
        n = len(vectors)
        if n < 2:
            return []

        # PERFORMANCE ARCHITECTURE: HYBRID ITERATIVE VECTORIZATION
        # --------------------------------------------------------
        # We need to compare ~10,000 vectors against each other. A standard
        # Python nested loop would take ~20 seconds. To optimize, we use a
        # 'Hybrid' approach:
        #
        # 1. OUTER LOOP (Python): Iterates through each vector 'i' one by one.
        #    This keeps memory usage constant (O(N)) and prevents OOM crashes
        #    on low-RAM hardware.
        #
        # 2. INNER "LOOP" (NumPy): Compares vector 'i' against ALL remaining
        #    candidates simultaneously using NumPy slicing and SIMD hardware
        #    acceleration.
        #
        # Result: Execution time drops from 20s to < 0.9s while remaining
        # memory-safe.

        # Convert to float32 to reduce memory bandwidth and improve speed.
        ranks_a_f32 = np.asarray(ranks_a, dtype=np.float32)
        ranks_b_f32 = np.asarray(ranks_b, dtype=np.float32)

        # High-performance candidate collection using list of NumPy arrays.
        # (avoids the overhead of creating millions of Python tuples).
        all_idx_a = []
        all_idx_b = []
        all_scores = []

        for i in range(n - 1):
            # Slice ranks for all remaining candidates (indices > i)
            ranks_a_rest = ranks_a_f32[i + 1 :]
            ranks_b_rest = ranks_b_f32[i + 1 :]

            # gains_a: Advantage of 'i' over the 'rest' on Utility Model A
            gains_a = ranks_a_f32[i] - ranks_a_rest

            # gains_b: Advantage of the 'rest' over 'i' on Utility Model B
            gains_b = ranks_b_rest - ranks_b_f32[i]

            # Case 1: 'i' is better on Utility Model A, Candidate is better on Utility Model B
            mask_i_better_on_a = (gains_a > 0) & (gains_b > 0)
            if np.any(mask_i_better_on_a):
                # Get indices relative to the slice
                indices_rel = np.where(mask_i_better_on_a)[0]
                all_idx_a.append(np.full(len(indices_rel), i, dtype=np.int32))
                all_idx_b.append(indices_rel + i + 1)
                all_scores.append(
                    np.minimum(gains_a[indices_rel], gains_b[indices_rel])
                )

            # Case 2: Candidate is better on Utility Model A, 'i' is better on Utility Model B
            mask_candidate_better_on_a = (gains_a < 0) & (gains_b < 0)
            if np.any(mask_candidate_better_on_a):
                # Get indices relative to the slice
                indices_rel = np.where(mask_candidate_better_on_a)[0]
                all_idx_a.append(indices_rel + i + 1)
                all_idx_b.append(np.full(len(indices_rel), i, dtype=np.int32))
                all_scores.append(
                    np.minimum(-gains_a[indices_rel], -gains_b[indices_rel])
                )

        if not all_scores:
            return []

        # Concatenate and sort using NumPy
        final_idx_a = np.concatenate(all_idx_a)
        final_idx_b = np.concatenate(all_idx_b)
        final_scores = np.concatenate(all_scores)

        # Sort by score descending
        sort_indices = np.argsort(final_scores)[::-1]

        selected: List[Tuple[int, int, float]] = []
        used_indices: Set[int] = set()

        for idx in sort_indices:
            if len(selected) >= target_pairs:
                break

            a_idx = int(final_idx_a[idx])
            b_idx = int(final_idx_b[idx])
            score = float(final_scores[idx])

            if a_idx in used_indices or b_idx in used_indices:
                continue

            selected.append((a_idx, b_idx, score))
            used_indices.add(a_idx)
            used_indices.add(b_idx)

        return selected

    def _calculate_utility_scores(
        self, vector_pool: Set[tuple], user_vector: tuple
    ) -> Tuple[np.ndarray, np.ndarray, List[tuple]]:
        """
        Calculate raw utility scores for all vectors in the pool.

        Args:
            vector_pool: Set of candidate vectors.
            user_vector: The user's ideal vector.

        Returns:
            Tuple containing:
            - Array of scores for utility model A
            - Array of scores for utility model B
            - List of vectors (ordered corresponding to the arrays)

        Example:
            User Vector: (50, 50)
            Pool: [(50, 50), (100, 0)]

            Utility Model A (L1, returns negative distance):
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
            scores_a.append(self.utility_model_a.calculate(user_vector, candidate))
            scores_b.append(self.utility_model_b.calculate(user_vector, candidate))

        return np.array(scores_a), np.array(scores_b), pool_list

    def _compute_ranks(
        self, scores_a: np.ndarray, scores_b: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Convert raw utility scores into normalized ranks (0.0 to 1.0).
        Higher rank indicates better match (closer to 1.0).

        Args:
            scores_a: Raw scores from utility model A.
            scores_b: Raw scores from utility model B.

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
        # Since utility models guarantee Higher Score = Better Match,
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
        Dynamically generated from utility model names.
        """
        return f"{self.utility_model_a.name}_vs_{self.utility_model_b.name}_rank_comparison"

    def get_option_labels(self) -> Tuple[str, str]:
        """
        Return human-readable labels for the two options being compared.
        Dynamically generated from utility model names via the translation system.
        """
        return (
            f"{get_translation(self.utility_model_a.name, 'answers')} (Rank)",
            f"{get_translation(self.utility_model_b.name, 'answers')} (Rank)",
        )

    def get_table_columns(self) -> Dict[str, Dict]:
        """
        Get column definitions for the survey response breakdown table.
        Dynamically generated from utility model names.
        """
        return {
            self.utility_model_a.name: {
                "name": get_translation(self.utility_model_a.name, "answers"),
                "type": "percentage",
                "highlight": True,
            },
            self.utility_model_b.name: {
                "name": get_translation(self.utility_model_b.name, "answers"),
                "type": "percentage",
                "highlight": True,
            },
        }

    def _get_metric_name(self, utility_model_identifier: str) -> str:
        """
        Get the display name for a utility model.
        Matches by name first, then falls back to utility_type.
        """
        if utility_model_identifier == self.utility_model_a.name:
            label = get_translation(self.utility_model_a.name, "answers")
            return f"{label} Optimized Vector"

        if utility_model_identifier == self.utility_model_b.name:
            label = get_translation(self.utility_model_b.name, "answers")
            return f"{label} Optimized Vector"

        # Fallback to type check
        if utility_model_identifier == self.utility_model_a.utility_type:
            label = get_translation(self.utility_model_a.name, "answers")
            return f"{label} Optimized Vector"

        if utility_model_identifier == self.utility_model_b.utility_type:
            label = get_translation(self.utility_model_b.name, "answers")
            return f"{label} Optimized Vector"

        return utility_model_identifier
