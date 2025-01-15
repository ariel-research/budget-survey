"""Implementation of the weighted average vector pair generation strategy."""

import logging
import random
from typing import List, Set, Tuple

import numpy as np

from application.services.pair_generation.base import PairGenerationStrategy

logger = logging.getLogger(__name__)


class WeightedAverageVectorStrategy(PairGenerationStrategy):
    """Strategy using weighted combinations of user vector and random vectors.

    Example:
        >>> strategy = WeightedAverageVectorStrategy()
        >>> user_vector = np.array([60, 25, 15])
        >>> random_vector = np.array([30, 45, 25])
        >>> result = strategy._calculate_weighted_vector(user_vector, random_vector, 0.3)
        >>> print(result)  # (39, 39, 22):
            # Calculation:
            #   - (60*0.3 + 30*0.7 = 39)
            #   - (25*0.3 + 45*0.7 = 39)
            #   - (15*0.3 + 25*0.7 = 22)
            #   - After rounding to integers and adjusting sum: [39, 39, 22]
    """

    # Class constants
    MAX_ATTEMPTS = 1000
    WEIGHTS = [0.1, 0.2, 0.3, 0.4, 0.5, 0.5, 0.6, 0.7, 0.8, 0.9]

    def _validate_weight(self, weight: float) -> None:
        """
        Validate weight value.

        Args:
            weight: Weight value to validate

        Raises:
            ValueError: If weight is invalid
        """
        if not isinstance(weight, float) or not 0 <= weight <= 1:
            raise ValueError("Weight must be a float between 0 and 1")

    def _generate_different_random_vector(
        self, user_vector: tuple, vector_size: int, existing_vectors: Set[tuple]
    ) -> tuple:
        """
        Generate a random vector that's different from the user vector and existing vectors.

        Args:
            user_vector: The user's ideal budget allocation
            vector_size: Size of the vector
            existing_vectors: Set of already generated vectors to avoid duplicates

        Returns:
            tuple: A new random vector

        Raises:
            ValueError: If unable to generate unique vector after max attempts
        """
        attempts = 0

        while attempts < self.MAX_ATTEMPTS:
            new_vector = self.create_random_vector(vector_size)
            if new_vector != user_vector and new_vector not in existing_vectors:
                return new_vector
            attempts += 1

        raise ValueError(
            f"Could not generate unique random vector after {self.MAX_ATTEMPTS} attempts"
        )

    def _calculate_weighted_vector(
        self, user_vector: np.ndarray, random_vector: np.ndarray, x_weight: float
    ) -> tuple:
        """
        Calculate weighted combination of user vector and random vector.

        Args:
            user_vector: The user's ideal budget allocation
            random_vector: Random vector to combine with
            x_weight: Weight for user vector (y_weight will be 1 - x_weight)

        Returns:
            tuple: Weighted combination vector
        """
        self._validate_weight(x_weight)
        y_weight = 1 - x_weight
        weighted = user_vector * x_weight + random_vector * y_weight
        # Round to integers and ensure sum is 100
        weighted = np.round(weighted).astype(int)
        # Adjust last element to ensure sum is exactly 100
        weighted[-1] = 100 - weighted[:-1].sum()
        return tuple(weighted)

    def _format_vector_for_logging(self, vector: tuple) -> Tuple[tuple, int]:
        """
        Format vector for logging, converting values to integers.

        Args:
            vector: Vector to format

        Returns:
            Tuple containing formatted vector and its sum
        """
        formatted = tuple(int(v) for v in vector)
        return formatted, sum(formatted)

    def _log_pairs(self, pairs: List[Tuple[tuple, tuple]]) -> None:
        """
        Log generated pairs with their sums.

        Args:
            pairs: List of vector pairs to log
        """
        for i, (vec_a, vec_b) in enumerate(pairs, 1):
            vec_a_fmt, sum_a = self._format_vector_for_logging(vec_a)
            vec_b_fmt, sum_b = self._format_vector_for_logging(vec_b)
            logger.info(
                f"pair {i}: {vec_a_fmt} (sum: {sum_a}), {vec_b_fmt} (sum: {sum_b})"
            )

    def generate_pairs(
        self, user_vector: tuple, n: int = 10, vector_size: int = 3
    ) -> List[Tuple[tuple, tuple]]:
        """
        Generate pairs using weighted combinations.

        Args:
            user_vector: The user's ideal budget allocation
            n: Number of pairs to generate (default: 10)
            vector_size: Size of each vector (default: 3)

        Returns:
            List of pairs, each containing [random_vector, weighted_vector]

        Raises:
            ValueError: If parameters are invalid or generation fails
        """
        try:
            # Validate input vector
            self._validate_vector(user_vector, vector_size)

            user_vector_array = np.array(user_vector)
            pairs = []
            existing_vectors = {
                user_vector
            }  # Track generated vectors to avoid duplicates

            for x_weight in self.WEIGHTS:
                # Generate new random vector
                random_vector = self._generate_different_random_vector(
                    user_vector, vector_size, existing_vectors
                )
                existing_vectors.add(random_vector)
                random_vector_array = np.array(random_vector)

                weighted_vector = self._calculate_weighted_vector(
                    user_vector_array, random_vector_array, x_weight
                )

                pair = (random_vector, weighted_vector)
                # pair = {"Random": random_vector, f"Weighted {x_weight}": weighted_vector}
                pairs.append(pair)

            # Shuffle pairs for random presentation order
            random.shuffle(pairs)

            logger.info(
                f"Successfully generated {len(pairs)} pairs using {self.__class__.__name__}"
            )
            self._log_pairs(pairs)

            return pairs

        except Exception as e:
            logger.error(
                f"Error generating pairs for user_vector={user_vector}, "
                f"n={n}, vector_size={vector_size}: {str(e)}"
            )
            raise ValueError("Failed to generate weighted vector pairs") from e

    def get_strategy_name(self) -> str:
        """Get the unique identifier for this strategy."""
        return "weighted_average_vector"

    def get_option_labels(self) -> Tuple[str, str]:
        return ("Random Vector", "Weighted Average Vector")
