"""Implementation of the multi-dimensional single-peaked (MDSP) strategy."""

import logging
import random
from typing import Dict, List, Set, Tuple

import numpy as np

from application.exceptions import UnsuitableForStrategyError
from application.services.pair_generation.base import PairGenerationStrategy
from application.translations import get_translation

logger = logging.getLogger(__name__)


class MultiDimensionalSinglePeakedStrategy(PairGenerationStrategy):
    """Generate pairs that test multi-dimensional single-peaked preferences."""

    MAX_ATTEMPTS = 10000

    def _is_unambiguously_closer(
        self,
        peak: Tuple[int, ...],
        q_near: Tuple[int, ...],
        q_far: Tuple[int, ...],
    ) -> bool:
        """
        Determine if q_near is unambiguously closer to peak than q_far.

        Implements the MDSP definition: every dimension must deviate from the
        peak in the same direction (no overshoot), q_near's deviation magnitude
        must not exceed q_far's, and it must be strictly smaller somewhere.
        Handles np.sign(0) edge cases:
            - If d_far[j] = 0 and d_near[j] ≠ 0, signs differ → False.
            - If both deviations are zero, the dimension passes.

        Returns:
            True if q_near is unambiguously closer under MDSP.
        """
        peak_arr = np.asarray(peak)
        near_arr = np.asarray(q_near)
        far_arr = np.asarray(q_far)

        diff_near = near_arr - peak_arr
        diff_far = far_arr - peak_arr

        strictly_closer_found = False

        for d_near, d_far in zip(diff_near, diff_far):
            sign_near = np.sign(d_near)
            sign_far = np.sign(d_far)

            if sign_near != sign_far:
                return False

            abs_near = abs(d_near)
            abs_far = abs(d_far)

            if abs_near > abs_far:
                return False

            if abs_near < abs_far:
                strictly_closer_found = True

        return strictly_closer_found

    def create_random_vector_unrestricted(self, size: int = 3) -> tuple:
        """
        Generate a random vector summing to 100 without divisibility limits.

        Used by MDSP to broaden the candidate space for extreme user vectors.
        """
        max_attempts = 100

        for _ in range(max_attempts):
            vector = np.random.rand(size)
            vector = np.floor(vector / vector.sum() * 100).astype(int)
            vector[-1] = 100 - vector[:-1].sum()

            if np.all(vector >= 0) and np.all(vector <= 100):
                np.random.shuffle(vector)
                return tuple(int(v) for v in vector)

        raise ValueError("Could not generate valid random vector")

    def generate_pairs(
        self, user_vector: tuple, n: int = 10, vector_size: int = 3
    ) -> List[Dict[str, tuple]]:
        """
        Generate MDSP test pairs using rejection sampling.

        Args:
            user_vector: The user's ideal budget allocation (peak).
            n: Number of pairs to generate (default: 10).
            vector_size: Number of dimensions in the allocation vectors.

        Returns:
            List of dicts mapping option descriptions to allocation vectors.

        Raises:
            UnsuitableForStrategyError: If user_vector contains zero values.
            ValueError: If unable to generate the required number of pairs.
        """
        self._validate_vector(user_vector, vector_size)

        if any(value == 0 for value in user_vector):
            raise UnsuitableForStrategyError(
                "User vector has zero entries; unsuitable for MDSP strategy."
            )

        pairs: List[Dict[str, tuple]] = []
        seen_pairs: Set[Tuple[tuple, tuple]] = set()

        attempts = 0
        max_attempts = self.MAX_ATTEMPTS

        while len(pairs) < n and attempts < max_attempts:
            attempts += 1

            q_a = self.create_random_vector_unrestricted(vector_size)
            q_b = self.create_random_vector_unrestricted(vector_size)

            if q_a == q_b:
                continue
            if q_a == user_vector or q_b == user_vector:
                continue

            candidate_pair = None
            if self._is_unambiguously_closer(user_vector, q_a, q_b):
                candidate_pair = (q_b, q_a)
            elif self._is_unambiguously_closer(user_vector, q_b, q_a):
                candidate_pair = (q_a, q_b)

            if candidate_pair is None:
                continue

            if candidate_pair in seen_pairs:
                continue

            seen_pairs.add(candidate_pair)
            far_vector, near_vector = candidate_pair

            pair_entry = {
                self.get_option_description(role="far"): far_vector,
                self.get_option_description(role="near"): near_vector,
            }
            pairs.append(pair_entry)

        if len(pairs) < n:
            raise ValueError(
                f"Could not generate {n} unique MDSP pairs after "
                f"{max_attempts} attempts."
            )

        random.shuffle(pairs)
        success_rate = 100 * len(pairs) / attempts if attempts > 0 else 0
        logger.info(
            "Generated %d MDSP pairs in %d attempts using %s " "(success rate: %.2f%%)",
            len(pairs),
            attempts,
            self.__class__.__name__,
            success_rate,
        )
        self._log_pairs(pairs)
        return pairs

    def get_strategy_name(self) -> str:
        """Return the strategy identifier."""
        return "multi_dimensional_single_peaked_test"

    def get_option_labels(self) -> Tuple[str, str]:
        return (
            get_translation("far_vector", "answers"),
            get_translation("near_vector", "answers"),
        )

    def get_option_description(self, **kwargs) -> str:
        role = kwargs.get("role")
        if role == "far":
            return "Further Vector"
        return "Nearer Vector"

    def _get_metric_name(self, metric_type: str) -> str:
        """Provide metric display name required by the base class."""
        return "Vector"
