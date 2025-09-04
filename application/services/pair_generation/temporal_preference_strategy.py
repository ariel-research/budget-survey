"""
Temporal preference strategy for testing temporal discounting in budget
allocations.

This strategy tests the hypothesis that users prefer receiving their ideal
budget allocation this year over receiving it next year by generating pairs
where users choose between their ideal vector and random vectors.
"""

import logging
from typing import Dict, List, Tuple

from application.services.pair_generation.base import PairGenerationStrategy

logger = logging.getLogger(__name__)


class TemporalPreferenceStrategy(PairGenerationStrategy):
    """
    Strategy for testing temporal preference in budget allocations.

    Tests temporal discounting by having users choose between:
    - Option 1: Their ideal vector (representing "ideal this year")
    - Option 2: A random vector (representing "ideal next year")
    """

    def generate_pairs(
        self, user_vector: tuple, n: int = 10, vector_size: int = 3
    ) -> List[Dict[str, tuple]]:
        """
        Generate pairs for temporal preference testing.

        Args:
            user_vector: User's ideal budget allocation
            n: Number of pairs to generate (default: 10)
            vector_size: Size of each allocation vector (default: 3)

        Returns:
            List of dicts containing {'option_description': vector} pairs

        Raises:
            ValueError: If user_vector is invalid or n is not positive
        """
        # Validate inputs
        self._validate_vector(user_vector, vector_size)
        if n <= 0:
            raise ValueError("Number of pairs must be positive")
        if n > 50:  # Reasonable upper limit to prevent excessive generation
            raise ValueError("Number of pairs must not exceed 50")

        logger.info(f"Generating {n} temporal preference pairs")

        # Generate unique random vectors that are different from user_vector
        random_vectors = self._generate_unique_random_vectors(
            user_vector, n, vector_size
        )

        pairs = []
        for i, random_vector in enumerate(random_vectors, 1):
            # Option 1 is always the user's ideal vector
            # Option 2 is always the random vector
            pair = {
                f"{self.get_option_labels()[0]}": user_vector,
                f"{self.get_option_labels()[1]}": random_vector,
            }
            pairs.append(pair)

        self._log_pairs(pairs)
        logger.info(f"Successfully generated {len(pairs)} temporal preference pairs")

        return pairs

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
            Tuple of ("Ideal This Year", "Ideal Next Year")
        """
        return ("Ideal This Year", "Ideal Next Year")

    def _get_metric_name(self, metric_type: str) -> str:
        """
        Get the display name for a metric type.

        Note: This method is required by the base class but not used
        in temporal preference strategy since we don't describe vectors
        with metrics.
        """
        metric_names = {
            "consistency": "Temporal Consistency",
            "ideal_this_year": "Ideal This Year Preference",
            "ideal_next_year": "Ideal Next Year Preference",
        }
        return metric_names.get(metric_type, metric_type.replace("_", " ").title())

    def get_table_columns(self) -> Dict[str, Dict]:
        """
        Get column definitions for the survey response breakdown table.

        Returns:
            Dict: Column definitions for temporal preference analysis
        """
        return {
            "ideal_this_year": {
                "name": "Ideal This Year (%)",
                "type": "percentage",
                "highlight": True,
            },
            "ideal_next_year": {
                "name": "Ideal Next Year (%)",
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
