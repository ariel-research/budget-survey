from typing import Dict, Tuple

import numpy as np

from application.services.pair_generation.weighted_average_vector import (
    WeightedAverageVectorStrategy,
)
from application.translations import get_translation


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
            np.ndarray: Rounded vector that sums to 100 with all values
            multiples of 5.
        """
        # First round everything to nearest multiple of 5
        rounded = np.round(weighted_vector / 5) * 5

        # Adjust to ensure sum is 100
        current_sum = rounded.sum()
        if current_sum != 100:
            # Find the largest element to adjust
            max_idx = np.argmax(rounded)
            rounded[max_idx] += 100 - current_sum

        return rounded.astype(int)

    def _calculate_weighted_vector(
        self, user_vector: np.ndarray, random_vector: np.ndarray, x_weight: float
    ) -> tuple:
        """
        Calculate weighted combination and round to multiples of 5.
        Ensures the result is different from both input vectors.

        Args:
            user_vector: The user's ideal budget allocation
            random_vector: Random vector to combine with
            x_weight: Weight for user vector (y_weight will be 1 - x_weight)

        Returns:
            tuple: Rounded weighted combination vector

        Raises:
            ValueError: If resulting vector is identical to either input
            vector
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
        result = tuple(rounded_weighted)

        # Check if result is different from both input vectors
        if result == tuple(user_vector) or result == tuple(random_vector):
            raise ValueError("Rounded weighted vector matches one of the input vectors")

        return result

    def get_strategy_name(self) -> str:
        """Get the unique identifier for this strategy."""
        return "rounded_weighted_average_vector"

    def get_option_labels(self) -> Tuple[str, str]:
        return (
            get_translation("random", "answers"),
            get_translation("weighted_average", "answers"),
        )

    def _get_metric_name(self, metric_type: str) -> str:
        if metric_type == "weight":
            return "Rounded Weighted Average Vector"
        return "Random Vector"

    def get_option_description(self, **kwargs) -> str:
        """Override for rounded weight-based description."""
        weight = kwargs.get("weight")
        if weight is None:
            return "Random Vector"
        return f"Rounded Weighted Average Vector: {int(weight * 100)}%"

    def get_table_columns(self) -> Dict[str, Dict]:
        """
        Get column definitions for the rounded weighted average vector
        response breakdown table.

        Returns:
            Dict with column definitions for Random and Weighted Average
            options.
        """
        return {
            "option1": {
                "name": get_translation("random", "answers"),
                "type": "percentage",
                "highlight": True,
            },
            "option2": {
                "name": get_translation("weighted_average", "answers"),
                "type": "percentage",
                "highlight": True,
            },
        }
