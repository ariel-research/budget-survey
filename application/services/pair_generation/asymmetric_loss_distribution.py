"""Implementation of the Asymmetric Loss Distribution strategy."""

import logging
from typing import Dict, List, Tuple

import numpy as np

from application.exceptions import UnsuitableForStrategyError
from application.services.pair_generation.base import PairGenerationStrategy
from application.translations import get_translation

logger = logging.getLogger(__name__)


class AsymmetricLossDistributionStrategy(PairGenerationStrategy):
    """
    Strategy testing user preferences for concentrated vs. distributed changes.

    This strategy generates 12 pairs based on a "calibrated-magnitude" approach
    to test whether users prefer budget changes to be concentrated in one
    category or distributed across multiple categories.

    Algorithm:
    1. Calibrated Magnitude: base_unit = max(1, round(min(ideal_budget) / 10))
    2. Four Levels: x_levels = {1, 2, 3, 4} * base_unit
    3. 12 Pairs Total: 3 target categories * 4 magnitude levels
    4. Two Comparison Types:
       - Type A (Primary): target loses 2x vs. target gains 2x.
       - Type B (Fallback): Funds for target boost come from one vs. many sources.
    """

    def generate_pairs(
        self, user_vector: tuple, n: int = 12, vector_size: int = 3
    ) -> List[Dict[str, tuple]]:
        """
        Generate 12 pairs testing concentrated vs. distributed changes.

        Args:
            user_vector: User's ideal budget allocation.
            n: Number of pairs to generate (always 12 for this strategy).
            vector_size: Size of each allocation vector (must be 3).

        Returns:
            List of 12 dictionaries containing comparison pairs.

        Raises:
            UnsuitableForStrategyError: If user vector contains zero values.
            ValueError: If vector_size is not 3 or pair generation fails.
        """
        if vector_size != 3:
            raise ValueError(
                "AsymmetricLossDistributionStrategy only supports vector_size=3."
            )

        if 0 in user_vector:
            logger.info(f"User vector {user_vector} contains zero values, unsuitable.")
            raise UnsuitableForStrategyError(
                "User vector contains zero values and is unsuitable for this strategy."
            )

        self._validate_vector(user_vector, vector_size)

        pairs = []
        user_array = np.array(user_vector)

        base_unit = max(1, round(min(user_vector) / 10))
        x_levels = [base_unit * i for i in [1, 2, 3, 4]]

        for target_idx in range(vector_size):
            for x in x_levels:
                other_indices = [i for i in range(vector_size) if i != target_idx]

                # Type A (Primary): target loses 2x vs. target gains 2x
                vec_a1 = user_array.copy()
                vec_a1[target_idx] -= 2 * x
                vec_a1[other_indices[0]] += x
                vec_a1[other_indices[1]] += x

                vec_a2 = user_array.copy()
                vec_a2[target_idx] += 2 * x
                vec_a2[other_indices[0]] -= x
                vec_a2[other_indices[1]] -= x

                if (
                    np.all(vec_a1 >= 0)
                    and np.all(vec_a2 >= 0)
                    and np.all(vec_a1 <= 100)
                    and np.all(vec_a2 <= 100)
                ):
                    pair_type = "A"
                    option1_vec, option2_vec = tuple(vec_a1.tolist()), tuple(
                        vec_a2.tolist()
                    )
                else:
                    # Type B (Fallback): Concentrated vs. Distributed Funding
                    pair_type = "B"

                    other_budgets = user_array[other_indices]
                    local_index_of_largest = np.argmax(other_budgets)
                    global_index_of_largest = other_indices[local_index_of_largest]

                    # Option 1: Concentrated Funding
                    vec_b1 = user_array.copy()
                    vec_b1[target_idx] += 2 * x
                    vec_b1[global_index_of_largest] -= 2 * x

                    # Option 2: Distributed Funding
                    vec_b2 = user_array.copy()
                    vec_b2[target_idx] += 2 * x
                    vec_b2[other_indices[0]] -= x
                    vec_b2[other_indices[1]] -= x

                    if not (
                        np.all(vec_b1 >= 0)
                        and np.all(vec_b1 <= 100)
                        and np.all(vec_b2 >= 0)
                        and np.all(vec_b2 <= 100)
                    ):
                        raise ValueError(
                            f"Could not generate valid Type B fallback pair for user_vector={user_vector}, target_idx={target_idx}, x={x}"
                        )

                    option1_vec, option2_vec = tuple(vec_b1.tolist()), tuple(
                        vec_b2.tolist()
                    )

                pairs.append(
                    {
                        "Concentrated Changes": option1_vec,
                        "Distributed Changes": option2_vec,
                        "pair_type": pair_type,
                        "magnitude": x,
                        "target_category": target_idx,
                    }
                )

        self._log_pairs(pairs)
        return pairs

    def get_strategy_name(self) -> str:
        """Return unique identifier for this strategy."""
        return "asymmetric_loss_distribution"

    def get_option_labels(self) -> Tuple[str, str]:
        """Return labels for the two options being compared."""
        return (
            get_translation("concentrated_changes", "answers"),
            get_translation("distributed_changes", "answers"),
        )

    def _get_metric_name(self, metric_type: str) -> str:
        """Get the display name for a metric type."""
        return f"Asymmetric {metric_type}"

    def get_table_columns(self) -> Dict[str, Dict]:
        """Get column definitions for the survey response breakdown table."""
        return {
            "preference_consistency": {
                "name": get_translation("preference_consistency", "answers"),
                "type": "percentage",
                "highlight": True,
            },
            "magnitude_sensitivity": {
                "name": get_translation("magnitude_sensitivity", "answers"),
                "type": "text",
                "highlight": False,
            },
        }
