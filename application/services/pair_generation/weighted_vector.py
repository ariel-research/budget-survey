"""Implementation of the weighted vector pair generation strategy."""

import logging
import random
from typing import List, Set, Tuple

import numpy as np

from application.services.pair_generation.base import PairGenerationStrategy

logger = logging.getLogger(__name__)


class WeightedVectorStrategy(PairGenerationStrategy):
    """Strategy using weighted combinations of user vector and random vectors."""

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
        """
        MAX_ATTEMPTS = 1000
        attempts = 0

        while attempts < MAX_ATTEMPTS:
            new_vector = self.create_random_vector(vector_size)
            if new_vector != user_vector and new_vector not in existing_vectors:
                return new_vector
            attempts += 1

        raise ValueError("Could not generate a unique random vector after max attempts")

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
        y_weight = 1 - x_weight
        weighted = user_vector * x_weight + random_vector * y_weight
        # Round to integers and ensure sum is 100
        weighted = np.round(weighted).astype(int)
        # Adjust last element to ensure sum is exactly 100
        weighted[-1] = 100 - weighted[:-1].sum()
        return tuple(weighted)

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
            ValueError: If user_vector is invalid (sum not 100)
        """
        # Validate input vector
        if not user_vector or len(user_vector) != vector_size:
            raise ValueError(f"User vector must have length {vector_size}")

        if sum(user_vector) != 100:
            raise ValueError("User vector must sum to 100")

        try:
            user_vector_array = np.array(user_vector)
            pairs = []
            existing_vectors = {
                user_vector
            }  # Track generated vectors to avoid duplicates

            # Calculate weights for each round
            weights = [0.1, 0.2, 0.3, 0.4, 0.5, 0.5, 0.6, 0.7, 0.8, 0.9]

            for x_weight in weights:
                # Generate new random vector
                random_vector = self._generate_different_random_vector(
                    user_vector, vector_size, existing_vectors
                )
                existing_vectors.add(random_vector)
                random_vector_array = np.array(random_vector)

                weighted_vector = self._calculate_weighted_vector(
                    user_vector_array, random_vector_array, x_weight
                )

                pairs.append((random_vector, weighted_vector))

            random.shuffle(pairs)

            logger.info(f"Successfully generated {len(pairs)} weighted vector pairs")

            # Log each pair with their sums
            pairs_list = [
                (
                    (int(a1), int(a2), int(a3)),
                    sum((int(a1), int(a2), int(a3))),
                    (int(b1), int(b2), int(b3)),
                    sum((int(b1), int(b2), int(b3))),
                )
                for (a1, a2, a3), (b1, b2, b3) in pairs
            ]
            for i, (vec_a, sum_a, vec_b, sum_b) in enumerate(pairs_list):
                logger.debug(
                    f"pair {i + 1}: {vec_a} (sum: {sum_a}), {vec_b} (sum: {sum_b})"
                )

            return pairs

        except Exception as e:
            logger.error(f"Error generating weighted vector pairs: {str(e)}")
            raise ValueError("Failed to generate weighted vector pairs") from e

        except Exception as e:
            logger.error(f"Error generating weighted vector pairs: {str(e)}")
            raise ValueError("Failed to generate weighted vector pairs") from e

    def get_strategy_name(self) -> str:
        """Get the unique identifier for this strategy."""
        return "weighted_vector"
