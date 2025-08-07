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
       - Type B (Fallback): Uses fixed difference vectors with cyclic rotations.
    """

    # Fixed difference vectors for Type B fallback
    TYPE_B_VECTORS = {
        1: [(1, -2, 1), (-1, 2, -1)],
        2: [(2, -4, 2), (-2, 4, -2)],
        3: [(1, -3, 2), (-1, 3, -2)],
        4: [(2, -5, 3), (-2, 5, -3)],
    }

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
                "User vector contains zero values and is unsuitable for "
                "this strategy."
            )

        self._validate_vector(user_vector, vector_size)

        pairs = []
        user_array = np.array(user_vector)

        base_unit = max(1, round(min(user_vector) / 10))
        x_levels = [round(base_unit * i) for i in [1, 2, 3, 4]]

        for target_idx in range(vector_size):
            for level_idx, x in enumerate(x_levels, 1):
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
                    # Type B (Fallback): Use fixed difference vectors with rotation
                    pair_type = "B"

                    # Get the fixed difference vectors for this magnitude level
                    diff_concentrated, diff_distributed = self.TYPE_B_VECTORS[level_idx]

                    # Apply cyclic rotation based on target_idx
                    diff_concentrated = self._rotate_vector(
                        diff_concentrated, target_idx
                    )
                    diff_distributed = self._rotate_vector(diff_distributed, target_idx)

                    # Apply differences directly to user vector (no scaling)
                    vec_b1 = user_array + np.array(diff_concentrated)
                    vec_b2 = user_array + np.array(diff_distributed)

                    # Validate the generated vectors
                    if not (
                        np.all(vec_b1 >= 0)
                        and np.all(vec_b1 <= 100)
                        and np.all(vec_b2 >= 0)
                        and np.all(vec_b2 <= 100)
                        and np.sum(vec_b1) == 100
                        and np.sum(vec_b2) == 100
                    ):
                        # If fixed vectors don't work, skip this pair
                        logger.warning(
                            f"Could not generate valid Type B pair for "
                            f"user_vector={user_vector}, target_idx={target_idx}, "
                            f"x={x}, level_idx={level_idx}"
                        )
                        continue

                    option1_vec, option2_vec = tuple(vec_b1.tolist()), tuple(
                        vec_b2.tolist()
                    )

                # Create strategy labels with magnitude information
                concentrated_label = get_translation("concentrated_changes", "answers")
                distributed_label = get_translation("distributed_changes", "answers")

                # Add magnitude and type in parentheses for display
                option1_strategy = f"{concentrated_label} ({x}, Type {pair_type})"
                option2_strategy = f"{distributed_label} ({x}, Type {pair_type})"

                pairs.append(
                    {
                        "Concentrated Changes": option1_vec,
                        "Distributed Changes": option2_vec,
                        "pair_type": pair_type,
                        "magnitude": x,
                        "target_category": target_idx,
                        "option1_strategy": option1_strategy,
                        "option2_strategy": option2_strategy,
                    }
                )

        self._log_pairs(pairs)
        return pairs

    def _rotate_vector(self, vector: tuple, positions: int) -> tuple:
        """
        Rotate a vector to the right by the specified number of positions.

        Args:
            vector: The vector to rotate.
            positions: Number of positions to rotate right.

        Returns:
            The rotated vector.
        """
        positions = positions % len(vector)
        if positions == 0:
            return vector
        return vector[-positions:] + vector[:-positions]

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
            "concentrated_changes": {
                "name": get_translation("concentrated_changes", "answers"),
                "type": "percentage",
                "highlight": True,
            },
            "distributed_changes": {
                "name": get_translation("distributed_changes", "answers"),
                "type": "percentage",
                "highlight": True,
            },
        }
