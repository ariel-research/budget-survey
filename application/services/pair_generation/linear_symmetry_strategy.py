"""Implementation of the linear symmetry strategy."""

import logging
from typing import Dict, List, Tuple

import numpy as np

from application.exceptions import UnsuitableForStrategyError
from application.services.pair_generation.base import PairGenerationStrategy
from application.translations import get_translation

logger = logging.getLogger(__name__)


class LinearSymmetryStrategy(PairGenerationStrategy):
    """
    Strategy that generates 12 comparison pairs organized into 6 groups to test
    linear symmetry hypothesis.

    Each group contains 2 pairs that test whether users treat positive and
    negative distances from their ideal allocation as equivalent:
    1. Generate two distance vectors v1 and v2 that sum to zero
    2. Create pair A: (ideal + v1) vs (ideal + v2)
    3. Create pair B: (ideal - v1) vs (ideal - v2)

    The hypothesis is that users should treat these pairs equivalently since
    they represent equal distances from the ideal allocation.

    Example:
        For user_vector = (40, 30, 30):
        v1 = [15, -10, -5], v2 = [-10, 5, 5]

        Group 1:
        - Pair A: [55, 20, 25] vs [30, 35, 35]  (ideal + v1 vs ideal + v2)
        - Pair B: [25, 40, 35] vs [50, 25, 25]  (ideal - v1 vs ideal - v2)
    """

    def _generate_distance_vectors(
        self, user_vector: tuple, vector_size: int
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate two different distance vectors that sum to zero.

        Args:
            user_vector: User's ideal budget allocation
            vector_size: Size of each vector

        Returns:
            Tuple of two distance vectors that sum to zero

        Raises:
            ValueError: If unable to generate valid distance vectors after
                many attempts
        """
        user_array = np.array(user_vector)
        min_val = min(user_vector)
        max_val = max(user_vector)

        for _ in range(1000):  # Try up to 1000 times
            # Step 1: Generate first distance vector
            v1 = []
            for _ in range(vector_size - 1):  # All except last element
                min_diff = -min_val
                max_diff = 100 - max_val
                diff = np.random.randint(min_diff, max_diff + 1)
                v1.append(diff)

            # Last element ensures sum = 0
            v1.append(-sum(v1))
            v1 = np.array(v1)

            # Check if v1 is all zeros (invalid)
            if np.all(v1 == 0):
                continue

            # Check meaningful differences for v1
            if not any(abs(d) >= 5 for d in v1):
                continue

            # Validate that both addition and subtraction produce valid vectors
            vec_plus = user_array + v1
            vec_minus = user_array - v1
            if not (
                np.all(vec_plus >= 0)
                and np.all(vec_plus <= 100)
                and np.all(vec_minus >= 0)
                and np.all(vec_minus <= 100)
            ):
                continue

            # Step 2: Generate second distance vector
            for _ in range(100):  # Inner loop for v2 generation
                v2 = []
                for _ in range(vector_size - 1):
                    min_diff = -min_val
                    max_diff = 100 - max_val
                    diff = np.random.randint(min_diff, max_diff + 1)
                    v2.append(diff)

                # Last element ensures sum = 0
                v2.append(-sum(v2))
                v2 = np.array(v2)

                # Check if v2 is all zeros (invalid)
                if np.all(v2 == 0):
                    continue

                # Check meaningful differences for v2
                if not any(abs(d) >= 5 for d in v2):
                    continue

                # Check if vectors are different
                if np.array_equal(v1, v2):
                    continue

                # Validate that both addition and subtraction produce valid vectors
                vec2_plus = user_array + v2
                vec2_minus = user_array - v2
                if (
                    np.all(vec2_plus >= 0)
                    and np.all(vec2_plus <= 100)
                    and np.all(vec2_minus >= 0)
                    and np.all(vec2_minus <= 100)
                ):
                    return v1, v2

        raise ValueError("Unable to generate valid distance vectors")

    def _generate_group(
        self,
        user_vector: tuple,
        vector_size: int,
        group_num: int,
        used_pairs: set = None,
    ) -> List[Dict[str, tuple]]:
        """
        Generate one group of 2 pairs testing linear symmetry.

        Args:
            user_vector: User's ideal budget allocation
            vector_size: Size of each vector
            group_num: Group number for labeling (1-6)
            used_pairs: Set of already used pair combinations to avoid
                duplicates

        Returns:
            List of 2 unique pairs for this group
        """
        if used_pairs is None:
            used_pairs = set()

        user_array = np.array(user_vector)
        max_attempts = 1000

        for _ in range(max_attempts):
            try:
                v1, v2 = self._generate_distance_vectors(user_vector, vector_size)

                # Calculate the four vectors
                vec_a1 = user_array + v1  # ideal + v1
                vec_a2 = user_array + v2  # ideal + v2
                vec_b1 = user_array - v1  # ideal - v1
                vec_b2 = user_array - v2  # ideal - v2

                # Apply multiples of 5 constraint if needed
                if 5 not in user_vector:
                    vec_a1 = np.round(vec_a1 / 5) * 5
                    vec_a2 = np.round(vec_a2 / 5) * 5
                    vec_b1 = np.round(vec_b1 / 5) * 5
                    vec_b2 = np.round(vec_b2 / 5) * 5

                    # Adjust to ensure sum is exactly 100
                    vec_a1[-1] = 100 - np.sum(vec_a1[:-1])
                    vec_a2[-1] = 100 - np.sum(vec_a2[:-1])
                    vec_b1[-1] = 100 - np.sum(vec_b1[:-1])
                    vec_b2[-1] = 100 - np.sum(vec_b2[:-1])

                # Convert to integers and tuples
                vec_a1 = tuple(int(v) for v in vec_a1)
                vec_a2 = tuple(int(v) for v in vec_a2)
                vec_b1 = tuple(int(v) for v in vec_b1)
                vec_b2 = tuple(int(v) for v in vec_b2)

                # Check for any invalid vectors after rounding
                all_vectors = [vec_a1, vec_a2, vec_b1, vec_b2]
                if any(
                    sum(vec) != 100 or any(v < 0 or v > 100 for v in vec)
                    for vec in all_vectors
                ):
                    continue

                # Check for identical vectors in each pair
                if vec_a1 == vec_a2 or vec_b1 == vec_b2:
                    continue

                # Check for duplicates by creating canonical representations
                pair_a = tuple(sorted([vec_a1, vec_a2]))
                pair_b = tuple(sorted([vec_b1, vec_b2]))

                if pair_a in used_pairs or pair_b in used_pairs:
                    continue

                # Calculate ACTUAL differences between user vector and final vectors
                actual_diff_a1 = [
                    int(vec_a1[i] - user_vector[i]) for i in range(len(user_vector))
                ]
                actual_diff_a2 = [
                    int(vec_a2[i] - user_vector[i]) for i in range(len(user_vector))
                ]
                actual_diff_b1 = [
                    int(vec_b1[i] - user_vector[i]) for i in range(len(user_vector))
                ]
                actual_diff_b2 = [
                    int(vec_b2[i] - user_vector[i]) for i in range(len(user_vector))
                ]

                # Create the pairs
                group_pairs = [
                    {
                        f"Linear Pattern + (v{group_num})": vec_a1,
                        f"Linear Pattern + (w{group_num})": vec_a2,
                        # Store actual differences for each option for display
                        "option1_differences": actual_diff_a1,
                        "option2_differences": actual_diff_a2,
                    },
                    {
                        f"Linear Pattern - (v{group_num})": vec_b1,
                        f"Linear Pattern - (w{group_num})": vec_b2,
                        # Store actual differences for each option for display
                        "option1_differences": actual_diff_b1,
                        "option2_differences": actual_diff_b2,
                    },
                ]

                # Mark these pairs as used
                used_pairs.add(pair_a)
                used_pairs.add(pair_b)

                return group_pairs

            except ValueError:
                continue  # Try again

        # If we couldn't generate valid pairs after max_attempts
        logger.warning(f"Could not generate 2 unique pairs for group {group_num}")
        return []

    def generate_pairs(
        self, user_vector: tuple, n: int = 12, vector_size: int = 3
    ) -> List[Dict[str, tuple]]:
        """
        Generate 12 comparison pairs organized into 6 groups using linear symmetry.

        Args:
            user_vector: User's ideal budget allocation
            n: Number of pairs to generate (always 12 for this strategy)
            vector_size: Size of each allocation vector (always 3)

        Returns:
            List of 12 dictionaries containing comparison pairs

        Raises:
            UnsuitableForStrategyError: If user vector contains zero values
            ValueError: If unable to generate required number of unique pairs
        """
        # Check for zero values in user vector
        if 0 in user_vector:
            logger.info(f"User vector {user_vector} contains zero values")
            raise UnsuitableForStrategyError(
                "User vector contains zero values and is unsuitable for "
                "linear symmetry strategy"
            )

        # Validate inputs
        self._validate_vector(user_vector, vector_size)

        all_pairs = []
        used_pairs = set()

        # Generate 6 groups of 2 pairs each
        for group_num in range(1, 7):
            group_pairs = self._generate_group(
                user_vector, vector_size, group_num, used_pairs
            )
            all_pairs.extend(group_pairs)

        # Ensure we have exactly 12 pairs
        if len(all_pairs) < 12:
            logger.warning(f"Only generated {len(all_pairs)} unique pairs, need 12")
            # Try to generate additional pairs if needed
            total_attempts = 0
            max_total_attempts = 600  # 6 groups × 100 attempts each
            while len(all_pairs) < 12 and total_attempts < max_total_attempts:
                additional_pairs = self._generate_group(
                    user_vector, vector_size, (total_attempts // 100) + 1, used_pairs
                )
                all_pairs.extend(additional_pairs)
                total_attempts += 1

        if len(all_pairs) < 12:
            raise ValueError(
                f"Unable to generate 12 unique pairs, only got {len(all_pairs)}"
            )

        # Take exactly 12 pairs
        final_pairs = all_pairs[:12]

        logger.info(
            f"Generated {len(final_pairs)} total pairs using "
            f"{self.__class__.__name__}"
        )
        self._log_pairs(final_pairs)

        return final_pairs

    def get_strategy_name(self) -> str:
        """Get the unique identifier for this strategy."""
        return "linear_symmetry"

    def get_option_labels(self) -> Tuple[str, str]:
        """Get labels for the two options being compared."""
        return (
            get_translation("linear_positive", "answers"),
            get_translation("linear_negative", "answers"),
        )

    def _get_metric_name(self, metric_type: str) -> str:
        """Get descriptive name for metrics."""
        return f"Linear {metric_type}"

    def get_table_columns(self) -> Dict[str, Dict]:
        """
        Get column definitions for the linear symmetry response breakdown table.

        Returns:
            Dict with column definitions for linear consistency.
        """
        return {
            "linear_consistency": {
                "name": get_translation(
                    "linear_consistency", "answers", fallback="Linear Consistency"
                ),
                "type": "percentage",
                "highlight": True,
            },
        }
