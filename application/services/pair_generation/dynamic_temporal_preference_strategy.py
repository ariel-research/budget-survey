"""
Dynamic Temporal Preference Test strategy for comprehensive temporal
discounting analysis.

This strategy implements a 12-question survey composed of three distinct
4-question sub-surveys to measure not only temporal discounting but also user
preferences for achieving exact ideal states versus mathematically balanced
two-year plans.

Sub-surveys:
1. Simple Discounting (4 questions): (Ideal, Random) vs (Random, Ideal)
2. Second-Year Choice (4 questions): (B, Ideal) vs (B, C) - Year 1 fixed as B
3. First-Year Choice (4 questions): (Ideal, B) vs (C, B) - Year 2 fixed as B

Where B and C are balanced vectors around user's ideal: (B+C)/2 = Ideal
"""

import logging
from typing import Dict, List, Tuple

import numpy as np

from application.exceptions import UnsuitableForStrategyError
from application.services.pair_generation.base import PairGenerationStrategy

logger = logging.getLogger(__name__)


class DynamicTemporalPreferenceStrategy(PairGenerationStrategy):
    """
    Strategy for comprehensive dynamic temporal preference testing in budget
    allocations.

    Implements a 12-question survey with three 4-question sub-surveys:

    1. Simple Discounting: Tests basic temporal discounting with
       (Ideal, Random) vs (Random, Ideal)
    2. Second-Year Choice: Year 1 budget fixed, user chooses Year 2 budget
    3. First-Year Choice: Year 2 budget fixed, user chooses Year 1 budget

    Uses balanced vector pairs (B, C) where (B+C)/2 = user's ideal vector.
    """

    def generate_pairs(
        self, user_vector: tuple, n: int = 12, vector_size: int = 3
    ) -> List[Dict[str, tuple]]:
        """
        Generate 12 pairs for dynamic temporal preference testing across
        3 sub-surveys.

        Args:
            user_vector: User's ideal budget allocation
            n: Number of pairs to generate (ignored, always generates 12)
            vector_size: Size of each allocation vector (default: 3)

        Returns:
            List of 12 dicts containing pairs for three sub-surveys:
            - Pairs 1-4: Simple Discounting
            - Pairs 5-8: Second-Year Choice
            - Pairs 9-12: First-Year Choice

        Raises:
            ValueError: If user_vector is invalid
            UnsuitableForStrategyError: If unable to generate balanced vectors
        """
        # Validate inputs
        self._validate_vector(user_vector, vector_size)

        if 0 in user_vector:
            logger.info(
                f"User vector {user_vector} contains zero values, "
                "unsuitable for DynamicTemporalPreferenceStrategy."
            )
            raise UnsuitableForStrategyError(
                "User vector contains zero values and is unsuitable for this strategy."
            )

        if n != 12:
            logger.warning(f"Strategy designed for 12 pairs but got n={n}, using 12")
            n = 12  # Override to always generate 12 pairs

        logger.info(f"Generating {n} dynamic temporal preference pairs")

        pairs = []

        # Sub-Survey 1: Simple Discounting (pairs 1-4)
        # User chooses between ideal vector and random vector for current year
        random_vectors = self._generate_unique_random_vectors(
            user_vector, 4, vector_size
        )
        for i, random_vector in enumerate(random_vectors, 1):
            pair = {
                "Simple Discounting - Ideal Option": user_vector,
                "Simple Discounting - Random Option": random_vector,
            }
            pairs.append(pair)
            logger.debug(f"Sub-survey 1, pair {i}: Ideal vs Random")

        # Generate balanced vector pairs for sub-surveys 2 & 3
        balanced_pairs = self._generate_balanced_vector_pairs(
            user_vector, vector_size, 4
        )

        # Sub-Survey 2: Second-Year Choice (pairs 5-8)
        # User chooses between ideal vector and vector C for next year
        # Vector B is fixed for current year
        for i, (vector_b, vector_c) in enumerate(balanced_pairs, 5):
            pair = {
                "Second-Year Choice - Ideal Option": user_vector,
                "Second-Year Choice - Balanced Option": vector_c,
                "instruction_context": {"fixed_vector": vector_b},
            }
            pairs.append(pair)
            logger.debug(f"Sub-survey 2, pair {i-4}: Ideal vs C, B={vector_b} fixed")

        # Sub-Survey 3: First-Year Choice (pairs 9-12)
        # User chooses between ideal vector and vector C for current year
        # Vector B is fixed for next year
        for i, (vector_b, vector_c) in enumerate(balanced_pairs, 9):
            pair = {
                "First-Year Choice - Ideal Option": user_vector,
                "First-Year Choice - Balanced Option": vector_c,
                "instruction_context": {"fixed_vector": vector_b},
            }
            pairs.append(pair)
            logger.debug(f"Sub-survey 3, pair {i-8}: Ideal vs C, B={vector_b} fixed")

        # Override logging since we have two-year plans, not single vectors
        logger.info(
            f"Successfully generated {len(pairs)} dynamic temporal preference " "pairs"
        )

        return pairs

    def _generate_balanced_vector_pairs(
        self, user_vector: tuple, vector_size: int, n: int
    ) -> List[Tuple[tuple, tuple]]:
        """
        Generate n unique balanced vector pairs (B, C) where
        (B+C)/2 = user_vector.

        Uses a two-tiered approach:
        1. Primary: Generate pairs where all values are multiples of 5
        2. Fallback: Generate pairs without multiples-of-5 constraint

        Args:
            user_vector: User's ideal budget allocation
            vector_size: Size of each vector
            n: Number of unique pairs to generate

        Returns:
            List of tuples (B, C) where B and C are balanced around user_vector

        Raises:
            UnsuitableForStrategyError: If unable to generate n unique pairs
        """
        logger.info(f"Generating {n} balanced vector pairs around {user_vector}")

        # Primary attempt: multiples of 5
        pairs = self._try_generate_balanced_pairs(
            user_vector, vector_size, n, multiples_of_5=True, max_attempts=100
        )

        if len(pairs) < n:
            logger.info(
                f"Primary attempt generated {len(pairs)}/{n} pairs. " "Trying fallback."
            )
            # Fallback attempt: no multiples of 5 constraint
            additional_pairs = self._try_generate_balanced_pairs(
                user_vector,
                vector_size,
                n - len(pairs),
                multiples_of_5=False,
                max_attempts=100,
                existing_pairs=pairs,
            )
            pairs.extend(additional_pairs)

        if len(pairs) < n:
            logger.error(
                f"Failed to generate {n} balanced pairs. "
                f"Only generated {len(pairs)}"
            )
            raise UnsuitableForStrategyError(
                f"Unable to generate {n} unique balanced vector pairs. "
                f"Only generated {len(pairs)} pairs."
            )

        logger.info(f"Successfully generated {len(pairs)} balanced vector pairs")
        return pairs[:n]

    def _try_generate_balanced_pairs(
        self,
        user_vector: tuple,
        vector_size: int,
        n: int,
        multiples_of_5: bool,
        max_attempts: int,
        existing_pairs: List = None,
    ) -> List[Tuple[tuple, tuple]]:
        """
        Attempt to generate n balanced vector pairs with specified constraints.

        Args:
            user_vector: User's ideal vector
            vector_size: Size of each vector
            n: Number of pairs needed
            multiples_of_5: Whether to enforce multiples of 5
            max_attempts: Maximum generation attempts
            existing_pairs: Already generated pairs to avoid duplicates

        Returns:
            List of generated (B, C) pairs
        """
        if existing_pairs is None:
            existing_pairs = []

        pairs = []
        existing_set = set(existing_pairs)
        attempts = 0

        while len(pairs) < n and attempts < max_attempts:
            attempts += 1

            # Generate random difference vector that sums to 0
            diff = self._generate_zero_sum_difference(
                vector_size, multiples_of_5, user_vector
            )

            # Skip if difference is all zeros (would create identical vectors)
            if all(d == 0 for d in diff):
                continue

            # Calculate balanced vectors (ensure Python integers)
            vector_b = tuple(int(user_vector[i] + diff[i]) for i in range(vector_size))
            vector_c = tuple(int(user_vector[i] - diff[i]) for i in range(vector_size))

            # Validate vectors are within bounds and different from user vector
            if (
                self._is_valid_vector(vector_b)
                and self._is_valid_vector(vector_c)
                and vector_b != user_vector
                and vector_c != user_vector
                and (vector_b, vector_c) not in existing_set
                and (vector_c, vector_b) not in existing_set
            ):
                pairs.append((vector_b, vector_c))
                existing_set.add((vector_b, vector_c))
                existing_set.add((vector_c, vector_b))

        logger.debug(
            f"Generated {len(pairs)} pairs in {attempts} attempts "
            f"(multiples_of_5: {multiples_of_5})"
        )
        return pairs

    def _generate_zero_sum_difference(
        self, vector_size: int, multiples_of_5: bool, user_vector: tuple
    ) -> List[int]:
        """
        Generate a random difference vector that sums to zero.

        Args:
            vector_size: Size of the difference vector
            multiples_of_5: Whether values should be multiples of 5
            user_vector: User's ideal vector (for calculating ranges)

        Returns:
            List of integers that sum to zero
        """
        if multiples_of_5:
            # Generate differences as multiples of 5
            # For extreme vectors, use smaller differences
            max_base_diff = min(
                18, min(user_vector) // 5, (100 - max(user_vector)) // 5
            )
            max_base_diff = max(1, max_base_diff)  # At least 1

            diffs = np.random.randint(
                -max_base_diff, max_base_diff + 1, size=vector_size - 1
            )
            # Make last element balance the sum
            last_diff = -np.sum(diffs)
            diffs = np.append(diffs, last_diff)
            # Scale to multiples of 5
            diffs = diffs * 5
        else:
            # Generate any integer differences
            # For extreme vectors, use more conservative differences
            max_diff = min(95, min(user_vector), 100 - max(user_vector))
            max_diff = max(1, max_diff)  # At least 1

            diffs = np.random.randint(-max_diff, max_diff + 1, size=vector_size - 1)
            # Make last element balance the sum
            last_diff = -np.sum(diffs)
            diffs = np.append(diffs, last_diff)

        np.random.shuffle(diffs)
        return diffs.tolist()

    def _is_valid_vector(self, vector: tuple) -> bool:
        """
        Check if vector has valid budget allocation values.

        Args:
            vector: Vector to validate

        Returns:
            bool: True if values are in [0,100] and sum to 100, False otherwise
        """
        return all(0 <= v <= 100 for v in vector) and sum(vector) == 100

    def _generate_unique_random_vectors(
        self, user_vector: tuple, n: int, vector_size: int
    ) -> List[tuple]:
        """
        Generate n unique random vectors that are different from user_vector.

        Args:
            user_vector: User's ideal vector to avoid
            n: Number of unique vectors to generate
            vector_size: Size of each vector

        Returns:
            List of unique random vectors

        Raises:
            ValueError: If unable to generate enough unique vectors
        """
        unique_vectors = set()
        max_attempts = n * 20  # Allow multiple attempts per required vector
        attempts = 0

        while len(unique_vectors) < n and attempts < max_attempts:
            attempts += 1
            random_vector = self.create_random_vector(vector_size)

            # Ensure Python integers in random vector
            random_vector = tuple(int(v) for v in random_vector)

            # Ensure the random vector is different from user's vector
            if random_vector != user_vector:
                unique_vectors.add(random_vector)

        if len(unique_vectors) < n:
            logger.error(
                f"Could only generate {len(unique_vectors)} unique vectors "
                f"out of {n} required after {attempts} attempts"
            )
            raise ValueError(
                f"Unable to generate {n} unique random vectors. "
                f"Only generated {len(unique_vectors)} vectors."
            )

        result = list(unique_vectors)[:n]  # Take exactly n vectors
        logger.debug(f"Generated {len(result)} unique random vectors")

        return result

    def get_strategy_name(self) -> str:
        """Return unique identifier for this strategy."""
        return "temporal_preference_test"

    def get_option_labels(self) -> Tuple[str, str]:
        """
        Return labels for the two options being compared.

        These labels are used for backend analysis and reporting tables.
        The frontend will show neutral "Option 1 / Option 2" text to users.

        Returns:
            Tuple of generic option labels for the dynamic temporal test
        """
        return ("Option A", "Option B")

    def _get_metric_name(self, metric_type: str) -> str:
        """
        Get the display name for a metric type.

        Note: This method is required by the base class but not used
        in dynamic temporal preference strategy since we don't describe vectors
        with metrics.
        """
        metric_names = {
            "sub1_ideal_y1": "Sub-Survey 1: Ideal Year 1",
            "sub2_ideal_y2": "Sub-Survey 2: Ideal Year 2",
            "sub3_ideal_y1": "Sub-Survey 3: Ideal Year 1",
            "consistency": "Dynamic Temporal Consistency",
        }
        return metric_names.get(metric_type, metric_type.replace("_", " ").title())

    def get_table_columns(self) -> Dict[str, Dict]:
        """
        Get column definitions for the survey response breakdown table.

        Returns:
            Dict: Column definitions for dynamic temporal preference analysis
        """
        return {
            "sub1_ideal_y1": {
                "name": "S1: Ideal in Year 1",
                "type": "percentage",
                "highlight": True,
            },
            "sub2_ideal_y2": {
                "name": "S2: Ideal in Year 2",
                "type": "percentage",
                "highlight": True,
            },
            "sub3_ideal_y1": {
                "name": "S3: Ideal in Year 1",
                "type": "percentage",
                "highlight": True,
            },
        }

    def is_ranking_based(self) -> bool:
        """
        Identify if this strategy uses ranking questions instead of pairs.

        Returns:
            bool: False, as this strategy uses pairwise comparisons
        """
        return False
