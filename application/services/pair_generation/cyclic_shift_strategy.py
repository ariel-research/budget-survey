"""Implementation of the cyclic shift comparison strategy."""

import logging
from typing import Dict, List, Tuple

import numpy as np

from application.exceptions import UnsuitableForStrategyError
from application.services.pair_generation.base import PairGenerationStrategy
from application.translations import get_translation

logger = logging.getLogger(__name__)


class CyclicShiftStrategy(PairGenerationStrategy):
    """
    Strategy that generates 12 comparison pairs organized into 4 groups using
    cyclic shifts.

    Each group contains 3 pairs created by:
    1. Generating two random difference vectors that sum to zero
    2. Applying these differences to create the first pair
    3. Creating the second and third pairs by cyclically shifting the
       differences right by one and two positions respectively

    The strategy rejects users whose ideal budget vectors contain zero values
    by raising UnsuitableForStrategyError.

    Example:
        For user_vector = (20, 30, 50):

        Group 1:
        - Pair 1: differences [-10, +5, +5] and [+15, -10, -5]
          Results: [10, 35, 55] vs [35, 20, 45]
        - Pair 2: shift right by 1: [+5, -10, +5] and [-5, +15, -10]
          Results: [25, 20, 55] vs [15, 45, 40]
        - Pair 3: shift right by 2: [+5, +5, -10] and [-10, -5, +15]
          Results: [25, 35, 40] vs [10, 25, 65]
    """

    def _generate_random_differences(
        self, user_vector: tuple, vector_size: int
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate two random difference vectors that sum to zero and produce
        meaningfully different results.

        Args:
            user_vector: User's ideal budget allocation
            vector_size: Size of each vector

        Returns:
            Tuple of two difference vectors that sum to zero

        Raises:
            ValueError: If unable to generate valid differences after many
                attempts

        Example:
            User vector: [20, 30, 50] (sum = 100)
            Min value in vector = 20, Max value = 50

            Step 1: Generate first difference vector
            - Since we apply cyclic shifts, use global constraints
            - For [20, 30, 50]: min=20, max=50, so range is [-20, +50] for all
            - Ensure at least one element has meaningful difference (>=5)
            - Generate random diffs: [+10, -15, ?]
            - Adjust last element so sum = 0: [+10, -15, +5]

            Step 2: Generate second difference vector
            - Start with negation: [-10, +15, -5]
            - Shuffle for variety: [-5, -10, +15]

            Step 3: Validate meaningful differences
            - Check that at least one element has |diff| >= 5
            - Ensures resulting vectors are meaningfully different

            Result:
            - diff1 = [+10, -15, +5] → vector1 = [30, 15, 55]
            - diff2 = [-5, -10, +15] → vector2 = [15, 20, 65]
            Both vectors sum to 100 and are meaningfully different
        """
        user_array = np.array(user_vector)

        # Constraints
        min_val = min(user_vector)
        max_val = max(user_vector)

        for _ in range(1000):  # Try up to 1000 times
            # Step 1: Generate first difference vector
            diff1 = []
            for _ in range(vector_size - 1):  # All except last element
                min_diff = -min_val
                max_diff = 100 - max_val
                diff = np.random.randint(min_diff, max_diff + 1)
                diff1.append(diff)

            # Last element ensures sum = 0
            diff1.append(-sum(diff1))
            diff1 = np.array(diff1)

            # Step 2: Generate second difference vector (negated + shuffled)
            diff2 = -diff1.copy()
            np.random.shuffle(diff2)

            # Step 3: Simple check - ensure at least one meaningful difference
            if not any(abs(d) >= 5 for d in diff1):
                continue  # Try again if all differences are too small

            # Step 4: Validate both resulting vectors
            vec1 = user_array + diff1
            vec2 = user_array + diff2

            if (
                np.all(vec1 >= 0)
                and np.all(vec1 <= 100)
                and np.all(vec2 >= 0)
                and np.all(vec2 <= 100)
                and np.sum(vec1) == 100
                and np.sum(vec2) == 100
                and not np.array_equal(vec1, vec2)  # Ensure vectors are different
            ):
                return diff1, diff2

        raise ValueError("Unable to generate valid difference vectors")

    def _apply_cyclic_shift(
        self, differences: np.ndarray, shift_amount: int
    ) -> np.ndarray:
        """
        Apply cyclic right shift to difference vector.

        Args:
            differences: Original difference vector
            shift_amount: Number of positions to shift right

        Returns:
            Shifted difference vector
        """
        return np.roll(differences, shift_amount)

    def _verify_differences(
        self, user_vector: tuple, diff1: np.ndarray, diff2: np.ndarray
    ) -> bool:
        """
        Verify that difference vectors produce valid budget vectors.

        Args:
            user_vector: User's ideal budget allocation
            diff1: First difference vector
            diff2: Second difference vector

        Returns:
            True if both resulting vectors are valid, False otherwise
        """
        user_array = np.array(user_vector)
        vec1 = user_array + diff1
        vec2 = user_array + diff2

        return (
            np.all(vec1 >= 0)
            and np.all(vec1 <= 100)
            and np.sum(vec1) == 100
            and np.all(vec2 >= 0)
            and np.all(vec2 <= 100)
            and np.sum(vec2) == 100
        )

    def _generate_group(
        self,
        user_vector: tuple,
        vector_size: int,
        group_num: int,
        used_pairs: set = None,
    ) -> List[Dict[str, tuple]]:
        """
        Generate one group of 3 pairs using cyclic shift pattern.

        Args:
            user_vector: User's ideal budget allocation
            vector_size: Size of each vector
            group_num: Group number for labeling (1-4)
            used_pairs: Set of already used pair combinations to avoid duplicates

        Returns:
            List of 3 unique pairs for this group
        """
        if used_pairs is None:
            used_pairs = set()

        user_array = np.array(user_vector)
        max_attempts = 1000

        for _ in range(max_attempts):
            diff1, diff2 = self._generate_random_differences(user_vector, vector_size)

            group_pairs = []
            temp_used = set()  # Track pairs within this group attempt

            # Generate 3 pairs with different shift amounts
            for shift in range(3):
                shifted_diff1 = self._apply_cyclic_shift(diff1, shift)
                shifted_diff2 = self._apply_cyclic_shift(diff2, shift)

                # Verify the shifted differences are still valid
                if not self._verify_differences(
                    user_vector, shifted_diff1, shifted_diff2
                ):
                    break

                vec1 = user_array + shifted_diff1
                vec2 = user_array + shifted_diff2

                # Ensure multiples of 5 constraint unless user vector contains 5
                if 5 not in user_vector:
                    vec1 = np.round(vec1 / 5) * 5
                    vec2 = np.round(vec2 / 5) * 5

                    # Adjust to ensure sum is exactly 100
                    vec1[-1] = 100 - np.sum(vec1[:-1])
                    vec2[-1] = 100 - np.sum(vec2[:-1])

                # Convert to integers and tuples
                vec1 = tuple(int(v) for v in vec1)
                vec2 = tuple(int(v) for v in vec2)

                # Check if rounding made the vectors identical
                if vec1 == vec2:
                    break  # Skip this pair and try again

                # Check for duplicates by creating a canonical representation
                vectors = tuple(sorted([vec1, vec2]))
                if vectors in used_pairs or vectors in temp_used:
                    break

                temp_used.add(vectors)
                pair = {
                    f"Cyclic Pattern A (shift {shift})": vec1,
                    f"Cyclic Pattern B (shift {shift})": vec2,
                }
                group_pairs.append(pair)

            if len(group_pairs) == 3:
                used_pairs.update(temp_used)
                return group_pairs

        # If we couldn't generate 3 unique pairs after max_attempts
        logger.warning(f"Could not generate 3 unique pairs for group {group_num}")
        return []

    def generate_pairs(
        self, user_vector: tuple, n: int = 12, vector_size: int = 3
    ) -> List[Dict[str, tuple]]:
        """
        Generate 12 comparison pairs organized into 4 groups using cyclic
        shifts.

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
                "cyclic shift strategy"
            )

        # Validate inputs
        self._validate_vector(user_vector, vector_size)

        all_pairs = []
        used_pairs = set()

        # Generate 4 groups of 3 pairs each
        for group_num in range(1, 5):
            group_pairs = self._generate_group(
                user_vector, vector_size, group_num, used_pairs
            )
            all_pairs.extend(group_pairs)

        # Ensure we have exactly 12 pairs
        if len(all_pairs) < 12:
            logger.warning(f"Only generated {len(all_pairs)} unique pairs, need 12")
            # Try to generate additional pairs if needed
            total_attempts = 0
            max_total_attempts = 400  # 4 groups × 100 attempts each
            while len(all_pairs) < 12 and total_attempts < max_total_attempts:
                additional_pairs = self._generate_group(
                    user_vector, vector_size, total_attempts // 100 + 1, used_pairs
                )
                all_pairs.extend(additional_pairs)
                total_attempts += 1

        if len(all_pairs) < 12:
            raise ValueError(
                f"Unable to generate 12 unique pairs, only got " f"{len(all_pairs)}"
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
        return "cyclic_shift"

    def get_option_labels(self) -> Tuple[str, str]:
        """Get labels for the two options being compared."""
        return (
            get_translation("cyclic_pattern_a", "answers"),
            get_translation("cyclic_pattern_b", "answers"),
        )

    def _get_metric_name(self, metric_type: str) -> str:
        """Get descriptive name for metrics."""
        return f"Cyclic {metric_type}"

    def get_table_columns(self) -> Dict[str, Dict]:
        """
        Get column definitions for the cyclic shift response breakdown table.

        Returns:
            Dict with column definitions for pattern preferences.
        """
        return {
            "pattern_a_preference": {
                "name": get_translation("cyclic_pattern_a", "answers"),
                "type": "percentage",
                "highlight": True,
            },
            "pattern_b_preference": {
                "name": get_translation("cyclic_pattern_b", "answers"),
                "type": "percentage",
                "highlight": True,
            },
        }
