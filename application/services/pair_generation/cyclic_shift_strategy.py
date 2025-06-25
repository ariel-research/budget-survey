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
        Generate two random difference vectors for cyclic shift strategy.

        Creates difference vectors that sum to zero and are not absolute
        canonical identical, ensuring meaningful comparisons across all
        cyclic shifts.

        Args:
            user_vector: User's ideal budget allocation (must sum to 100)
            vector_size: Size of each vector (typically 3)

        Returns:
            Tuple[np.ndarray, np.ndarray]: Two difference vectors that:
                - Sum to zero
                - Are not absolute canonical identical
                - Produce valid budget vectors when added to user_vector

        Raises:
            ValueError: If unable to generate valid differences after 1000 attempts

        Example:
            >>> user_vector = (30, 40, 30)
            >>> diff1, diff2 = _generate_random_differences(user_vector, 3)
            >>> sum(diff1), sum(diff2)  # Both sum to zero
            (0, 0)
            >>> tuple(sorted(abs(x) for x in diff1)) != tuple(sorted(abs(x) for x in diff2))
            True  # Different absolute canonical forms
        """
        user_array = np.array(user_vector)

        # Constraints
        min_val = min(user_vector)
        max_val = max(user_vector)

        for _ in range(1000):  # Outer loop attempts
            # Generate first difference vector
            diff1 = []
            for _ in range(vector_size - 1):  # All except last element
                min_diff = -min_val
                max_diff = 100 - max_val
                diff = np.random.randint(min_diff, max_diff + 1)
                diff1.append(diff)

            # Last element ensures sum = 0
            diff1.append(-sum(diff1))
            diff1 = np.array(diff1)

            # Check meaningful differences for diff1
            if not any(abs(d) >= 5 for d in diff1):
                continue  # Try again if all differences are too small

            # Validate first vector
            vec1 = user_array + diff1
            if not (np.all(vec1 >= 0) and np.all(vec1 <= 100) and np.sum(vec1) == 100):
                continue

            # Try to find a valid diff2
            for _ in range(100):  # Inner loop for diff2
                diff2 = []
                for _ in range(vector_size - 1):
                    min_diff = -min_val
                    max_diff = 100 - max_val
                    diff = np.random.randint(min_diff, max_diff + 1)
                    diff2.append(diff)

                # Last element ensures sum = 0
                diff2.append(-sum(diff2))
                diff2 = np.array(diff2)

                # Check meaningful differences for diff2
                if not any(abs(d) >= 5 for d in diff2):
                    continue

                # Check absolute canonical form
                if self._are_absolute_canonical_identical(diff1, diff2):
                    continue

                # Validate second vector
                vec2 = user_array + diff2
                if (
                    np.all(vec2 >= 0)
                    and np.all(vec2 <= 100)
                    and np.sum(vec2) == 100
                    and not np.array_equal(vec1, vec2)
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
        used_differences: set = None,
    ) -> List[Dict[str, tuple]]:
        """
        Generate one group of 3 pairs using cyclic shift pattern.

        Creates 3 pairs by applying cyclic shifts (0, 1, 2 positions) to
        the same base difference vectors. Tracks uniqueness by difference
        vectors rather than final budget vectors to maintain cyclic
        relationships within groups.

        Args:
            user_vector: User's ideal budget allocation
            vector_size: Size of each vector
            group_num: Group number for labeling
            used_differences: Set of already used difference combinations

        Returns:
            List[Dict[str, tuple]]: List of 3 pairs with proper cyclic shifts

        Example:
            For base differences [-20, +15, +5] and [-30, -10, +40]:
            - Shift 0: [-20, +15, +5] and [-30, -10, +40]
            - Shift 1: [+5, -20, +15] and [+40, -30, -10]
            - Shift 2: [+15, +5, -20] and [-10, +40, -30]
        """
        if used_differences is None:
            used_differences = set()

        user_array = np.array(user_vector)
        max_attempts = 1000

        for _ in range(max_attempts):
            diff1, diff2 = self._generate_random_differences(user_vector, vector_size)

            group_pairs = []
            temp_used_diffs = set()
            all_shifts_valid = True

            for shift in range(3):
                shifted_diff1 = self._apply_cyclic_shift(diff1, shift)
                shifted_diff2 = self._apply_cyclic_shift(diff2, shift)

                # Check if shifted patterns are absolute canonical identical
                if self._are_absolute_canonical_identical(shifted_diff1, shifted_diff2):
                    all_shifts_valid = False
                    break

                # Verify shifted differences produce valid vectors
                if not self._verify_differences(
                    user_vector, shifted_diff1, shifted_diff2
                ):
                    all_shifts_valid = False
                    break

                vec1 = user_array + shifted_diff1
                vec2 = user_array + shifted_diff2

                # Apply rounding if needed
                if 5 not in user_vector:
                    vec1 = np.round(vec1 / 5) * 5
                    vec2 = np.round(vec2 / 5) * 5

                    # Adjust to ensure sum is exactly 100
                    vec1[-1] = 100 - np.sum(vec1[:-1])
                    vec2[-1] = 100 - np.sum(vec2[:-1])

                    # Recalculate actual differences after rounding
                    actual_diff1 = vec1 - user_array
                    actual_diff2 = vec2 - user_array

                    # Check if rounding created absolute canonical identical patterns
                    if self._are_absolute_canonical_identical(
                        actual_diff1, actual_diff2
                    ):
                        all_shifts_valid = False
                        break

                    # Use actual differences after rounding
                    final_diff1 = actual_diff1
                    final_diff2 = actual_diff2
                else:
                    # No rounding needed
                    final_diff1 = shifted_diff1
                    final_diff2 = shifted_diff2

                # Convert to tuples
                vec1 = tuple(int(v) for v in vec1)
                vec2 = tuple(int(v) for v in vec2)

                # Check for identical vectors
                if vec1 == vec2:
                    all_shifts_valid = False
                    break

                # Check uniqueness by difference vectors (not final vectors)
                def to_tuple(diff):
                    return tuple(
                        diff.tolist() if isinstance(diff, np.ndarray) else diff
                    )

                diff_pair = tuple(
                    sorted([to_tuple(final_diff1), to_tuple(final_diff2)])
                )

                if diff_pair in used_differences or diff_pair in temp_used_diffs:
                    all_shifts_valid = False
                    break

                temp_used_diffs.add(diff_pair)
                pair = {
                    f"Cyclic Pattern A (shift {shift})": vec1,
                    f"Cyclic Pattern B (shift {shift})": vec2,
                    "option1_differences": (
                        final_diff1.tolist()
                        if isinstance(final_diff1, np.ndarray)
                        else list(final_diff1)
                    ),
                    "option2_differences": (
                        final_diff2.tolist()
                        if isinstance(final_diff2, np.ndarray)
                        else list(final_diff2)
                    ),
                }
                group_pairs.append(pair)

            if all_shifts_valid and len(group_pairs) == 3:
                used_differences.update(temp_used_diffs)
                return group_pairs

        logger.warning(
            f"Could not generate 3 valid pairs for group {group_num} "
            f"after {max_attempts} attempts"
        )
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
        used_differences = set()

        # Generate 4 groups of 3 pairs each
        for group_num in range(1, 5):
            group_pairs = self._generate_group(
                user_vector, vector_size, group_num, used_differences
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
                    user_vector,
                    vector_size,
                    total_attempts // 100 + 1,
                    used_differences,
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
            Dict with column definitions for group consistency.
        """
        return {
            "group_consistency": {
                "name": get_translation("group_consistency", "answers"),
                "type": "percentage",
                "highlight": True,
            },
        }
