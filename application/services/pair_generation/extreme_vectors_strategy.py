"""Implementation of the extreme vectors comparison strategy."""

import logging
from typing import Dict, List, Tuple

import numpy as np

from application.services.pair_generation.base import PairGenerationStrategy
from application.translations import get_translation

logger = logging.getLogger(__name__)


class ExtremeVectorsStrategy(PairGenerationStrategy):
    """
    Strategy comparing extreme vectors and their weighted averages with the user's ideal vector.

    This strategy tests if users who prefer one extreme vector over another also prefer
    weighted averages that incorporate their preferred extreme vector.

    The extreme vectors are generated such that each vector has one large value and small
    equal values for the rest, ensuring the total sums to 100. For a vector size of 3,
    each extreme vector will have values of [80,10,10], [10,80,10], and [10,10,80].

    Example:
        For a survey with 3 departments and user_vector = (70, 20, 10):

        Extreme comparisons:
        - [80, 10, 10] vs [10, 80, 10]
        - [80, 10, 10] vs [10, 10, 80]
        - [10, 80, 10] vs [10, 10, 80]

        Weighted average comparisons (25%, 50%, 75%):
        - [77, 12, 11] (75% [80,10,10] + 25% [70,20,10]) vs [25, 65, 10]
    """

    # Class constants
    EXTREME_WEIGHTS = [0.25, 0.5, 0.75]  # Weights for mixing extreme and user vectors

    def _generate_extreme_vectors(self, vector_size: int) -> List[np.ndarray]:
        """
        Generate extreme vectors that sum to 100, with one large value and equal small values.

        For each vector, one element will be 100 - 10*(n-1) where n is vector_size,
        and all other elements will be 10. This ensures the sum is always 100.

        Args:
            vector_size: Size of the vector

        Returns:
            List of extreme vectors as numpy arrays, each summing to 100
        """
        extremes = []
        for i in range(vector_size):
            extreme = np.ones(vector_size, dtype=int) * 10
            extreme[i] = 100 - 10 * (vector_size - 1)
            extremes.append(extreme)
        return extremes

    def _calculate_weighted_vector(
        self, user_vector: np.ndarray, extreme_vector: np.ndarray, extreme_weight: float
    ) -> tuple:
        """
        Calculate weighted average of user vector and extreme vector.

        Args:
            user_vector: User's ideal budget allocation
            extreme_vector: Extreme vector (e.g., [100,0,0])
            extreme_weight: Weight for extreme vector (user_weight = 1 - extreme_weight)

        Returns:
            tuple: Weighted average vector
        """
        user_weight = 1 - extreme_weight
        weighted = extreme_vector * extreme_weight + user_vector * user_weight

        # Round to integers and ensure sum is 100
        weighted = np.round(weighted).astype(int)

        # Adjust last element to ensure sum is exactly 100
        weighted[-1] = 100 - weighted[:-1].sum()

        return tuple(weighted)

    def generate_pairs(
        self, user_vector: tuple, n: int = None, vector_size: int = 3
    ) -> List[Dict[str, tuple]]:
        """
        Generate pairs for comparison.

        First generates pairs of extreme vectors, then weighted combinations
        of the user's vector with each extreme vector at various weights.

        For a vector of size 3, this always generates:
        - 3 extreme vector pairs
        - 9 weighted vector pairs (3 pairs for each of the 3 weights)

        Args:
            user_vector: The user's ideal budget allocation
            n: Number of pairs (unused, included for compatibility with base class)
            vector_size: Size of each vector (default: 3)

        Returns:
            List[Dict[str, tuple]]: List of pairs for comparison
        """
        user_vector_array = np.array(user_vector)
        extreme_vectors = self._generate_extreme_vectors(vector_size)
        pairs = []

        # Generate pairs of extreme vectors
        for i in range(len(extreme_vectors)):
            for j in range(i + 1, len(extreme_vectors)):
                extreme1 = extreme_vectors[i]
                extreme2 = extreme_vectors[j]

                # Store with English keys internally, display text will be handled in the UI
                pair = {
                    f"Extreme Vector {i+1}": tuple(extreme1),
                    f"Extreme Vector {j+1}": tuple(extreme2),
                }

                # Add metadata to help UI with translation
                pair["option1_strategy"] = f"Extreme Vector {i+1}"
                pair["option2_strategy"] = f"Extreme Vector {j+1}"

                pairs.append(pair)

        # Generate weighted average pairs for each weight
        for weight in self.EXTREME_WEIGHTS:
            for i in range(len(extreme_vectors)):
                for j in range(i + 1, len(extreme_vectors)):
                    weighted1 = self._calculate_weighted_vector(
                        user_vector_array, extreme_vectors[i], weight
                    )
                    weighted2 = self._calculate_weighted_vector(
                        user_vector_array, extreme_vectors[j], weight
                    )

                    weight_percent = int(weight * 100)

                    # Use English keys for internal storage
                    key1 = f"{weight_percent}% Weighted Average (Extreme {i+1})"
                    key2 = f"{weight_percent}% Weighted Average (Extreme {j+1})"

                    pair = {
                        key1: weighted1,
                        key2: weighted2,
                    }

                    # Add metadata to help UI with translation
                    pair["option1_strategy"] = key1
                    pair["option2_strategy"] = key2

                    pairs.append(pair)

        logger.info(f"Generated {len(pairs)} pairs using {self.__class__.__name__}")
        self._log_pairs(pairs)

        return pairs

    def get_strategy_name(self) -> str:
        """Get the unique identifier for this strategy."""
        return "extreme_vectors"

    def get_option_labels(self) -> Tuple[str, str]:
        """Get labels for the two options being compared."""
        return (
            get_translation("extreme_1", "answers"),
            get_translation("extreme_2", "answers"),
        )

    def _get_metric_name(self, metric_type: str) -> str:
        """Get descriptive name for metrics."""
        return f"{metric_type} Vector"

    def get_table_columns(self) -> Dict[str, Dict]:
        """
        Get column definitions for the extreme vectors response breakdown table.

        Returns:
            Dict with column definitions for consistency percentage.
        """
        return {
            "consistency": {
                "name": get_translation("overall_consistency", "answers"),
                "type": "percentage",
                "highlight": True,
            }
        }
