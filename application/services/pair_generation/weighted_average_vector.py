"""Implementation of the weighted average vector pair generation strategy."""

import logging
import random
from typing import Dict, List, Set, Tuple

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
        Ensures the result is different from both input vectors.

        Args:
            user_vector: The user's ideal budget allocation
            random_vector: Random vector to combine with
            x_weight: Weight for user vector (y_weight will be 1 - x_weight)

        Returns:
            tuple: Weighted combination vector

        Raises:
            ValueError: If resulting vector is identical to either input vector
        """
        self._validate_weight(x_weight)
        y_weight = 1 - x_weight
        weighted = user_vector * x_weight + random_vector * y_weight
        # Round to integers and ensure sum is 100
        weighted = np.round(weighted).astype(int)
        # Adjust last element to ensure sum is exactly 100
        weighted[-1] = 100 - weighted[:-1].sum()
        result = tuple(weighted)

        # Check if result is different from both input vectors
        if result == tuple(user_vector) or result == tuple(random_vector):
            raise ValueError("Weighted vector matches one of the input vectors")

        return result

    def generate_pairs(
        self, user_vector: tuple, n: int = 10, vector_size: int = 3
    ) -> List[Dict[str, tuple]]:
        """
        Generate pairs using weighted combinations.
        Ensures vectors in each pair are different from each other.

        Args:
            user_vector: The user's ideal budget allocation
            n: Number of pairs to generate (default: 10)
            vector_size: Size of each vector (default: 3)

        Returns:
            List[Dict[str, tuple]]: List of pairs with different vectors

        Raises:
            ValueError: If parameters are invalid or generation fails
        """
        try:
            # Validate input vector
            self._validate_vector(user_vector, vector_size)

            user_vector_array = np.array(user_vector)
            pairs = []
            existing_vectors = {user_vector}  # Track generated vectors
            attempts = 0
            max_attempts = self.MAX_ATTEMPTS

            while len(pairs) < n and attempts < max_attempts:
                try:
                    # Generate new random vector
                    random_vector = self._generate_different_random_vector(
                        user_vector, vector_size, existing_vectors
                    )
                    random_vector_array = np.array(random_vector)

                    x_weight = self.WEIGHTS[len(pairs)]
                    weighted_vector = self._calculate_weighted_vector(
                        user_vector_array, random_vector_array, x_weight
                    )

                    # Ensure weighted vector is different from random vector
                    if weighted_vector != random_vector:
                        pair = {
                            self.get_option_description(): random_vector,
                            self.get_option_description(
                                weight=x_weight
                            ): weighted_vector,
                        }
                        pairs.append(pair)
                        existing_vectors.add(weighted_vector)

                except ValueError:
                    # If vector generation or weighting fails, try again
                    pass

                attempts += 1

            if len(pairs) < n:
                raise ValueError(
                    f"Could not generate {n} unique pairs after {max_attempts} attempts"
                )

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
        return ("Random", "Weighted Average")

    def _get_metric_name(self, metric_type: str) -> str:
        if metric_type == "weight":
            return "Average Weighted Vector"
        return "Random Vector"

    def get_option_description(self, **kwargs) -> str:
        """Override for weight-based description."""
        weight = kwargs.get("weight")
        if weight is None:
            return "Random Vector"
        return f"Average Weighted Vector: {int(weight * 100)}%"
