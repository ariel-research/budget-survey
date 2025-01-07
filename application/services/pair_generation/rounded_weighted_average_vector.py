import numpy as np

from application.services.pair_generation import WeightedAverageVectorStrategy


class RoundedWeightedAverageVectorStrategy(WeightedAverageVectorStrategy):
    """Strategy using rounded weighted combinations of user vector and random vectors.

    Example:
        >>> strategy = RoundedWeightedAverageVectorStrategy()
        >>> user_vector = np.array([60, 25, 15])
        >>> random_vector = np.array([30, 45, 25])
        >>> result = strategy._calculate_weighted_vector(user_vector, random_vector, 0.3)
        >>> print(result)  # (40, 40, 20):
            # Calculation:
            #   - Before rounding: [39, 39, 22]
            #   - (60*0.3 + 30*0.7 = 39)
            #   - (25*0.3 + 45*0.7 = 39)
            #   - (15*0.3 + 25*0.7 = 22)
            #   - After rounding to multiples of 5: [40, 40, 20]
    """

    def _rounded_vector(self, weighted_vector: np.ndarray) -> np.ndarray:
        """
        Ensures all values in the vector are multiples of 5 and sum to 100.

        Args:
            weighted_vector: The weighted vector to be rounded.

        Returns:
            np.ndarray: Rounded vector that sums to 100 with all values multiples of 5.
        """
        # First round everything to nearest multiple of 5
        rounded = np.round(weighted_vector / 5) * 5

        # Adjust to ensure sum is 100
        current_sum = rounded.sum()
        if current_sum != 100:
            # Find the largest element to adjust
            max_idx = np.argmax(rounded)
            rounded[max_idx] += 100 - current_sum

        return rounded

    def _calculate_weighted_vector(
        self, user_vector: np.ndarray, random_vector: np.ndarray, x_weight: float
    ) -> tuple:
        """
        Calculate weighted combination of user vector and random vector, and round to the nearest multiple of 5.

        Args:
            user_vector: The user's ideal budget allocation
            random_vector: Random vector to combine with
            x_weight: Weight for user vector (y_weight will be 1 - x_weight)

        Returns:
            tuple: Rounded weighted combination vector
        """
        self._validate_weight(x_weight)
        y_weight = 1 - x_weight
        weighted = user_vector * x_weight + random_vector * y_weight
        # Round to integers and ensure sum is 100
        weighted = np.round(weighted).astype(int)
        # Adjust last element to ensure sum is exactly 100
        weighted[-1] = 100 - weighted[:-1].sum()
        # Round to nearest multiple of 5
        rounded_weighted = self._rounded_vector(weighted)
        return tuple(rounded_weighted)

    def get_strategy_name(self) -> str:
        """Get the unique identifier for this strategy."""
        return "rounded_weighted_average_vector"
