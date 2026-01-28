"""Implementation of the Identity Asymmetry strategy."""

import logging
from typing import Dict, List, Tuple

from application.exceptions import UnsuitableForStrategyError
from application.services.pair_generation.base import PairGenerationStrategy
from application.translations import get_translation

logger = logging.getLogger(__name__)


class IdentityAsymmetryStrategy(PairGenerationStrategy):
    """
    Strategy testing Project Identity Bias by shifting budget between equal-valued projects.

    This strategy identifies two subjects with mathematically identical starting
    budget allocations (minimum value defined by number of pairs (n)) and generates
    n comparison pairs with increasing magnitude transfers between them.
    """

    def generate_pairs(
        self, user_vector: tuple, n: int = 10, vector_size: int = 3
    ) -> List[Dict]:
        """
        Generate n pairs testing identity bias.

        Args:
            user_vector: User's ideal budget allocation.
            n: Number of pairs to generate (default 10).
            vector_size: Size of each allocation vector.

        Returns:
            List of dictionaries containing comparison pairs and metadata.
        """
        self._validate_vector(user_vector, vector_size)

        # 1. Selection: Find the largest equal pair
        try:
            (idx_a, idx_b), target_value = self._find_largest_equal_pair(
                user_vector, min_val=n
            )
        except UnsuitableForStrategyError as e:
            logger.info(f"IdentityAsymmetryStrategy unsuitable: {str(e)}")
            raise

        pairs = []
        # 2. Calculate the step size
        step_size = target_value / float(n)

        for i in range(1, n + 1):
            # 3. Math Integrity: Round the magnitude
            m_float = step_size * i
            magnitude = max(1, int(round(m_float)))

            # Option 1: A loses magnitude, B gains magnitude (Favors B)
            vec_1 = list(user_vector)
            vec_1[idx_a] -= magnitude
            vec_1[idx_b] += magnitude

            # Option 2: B loses magnitude, A gains magnitude (Favors A)
            vec_2 = list(user_vector)
            vec_2[idx_b] -= magnitude
            vec_2[idx_a] += magnitude

            # Ensure values are within [0, 100]
            vec_1 = tuple(max(0, min(100, v)) for v in vec_1)
            vec_2 = tuple(max(0, min(100, v)) for v in vec_2)

            # Construct strategy labels (placeholders for now, will be mapped to "Favor {Subject}")
            # Note: favor_subject translation key expects {subject_name}
            # The actual interpolation will happen in the renderer or survey service.
            option1_strategy = f"favor_subject_index_{idx_b}"
            option2_strategy = f"favor_subject_index_{idx_a}"

            metadata = {
                "pair_type": "identity_test",
                "subject_a_idx": idx_a,
                "subject_b_idx": idx_b,
                "step_number": i,
                "magnitude": magnitude,
                "option_1_favors_idx": idx_b,
                "option_2_favors_idx": idx_a,
            }

            pairs.append(
                {
                    "Option 1": vec_1,
                    "Option 2": vec_2,
                    "option1_strategy": option1_strategy,
                    "option2_strategy": option2_strategy,
                    "__metadata__": metadata,
                }
            )

        self._log_pairs(pairs)
        return pairs

    def _find_largest_equal_pair(
        self, vector: tuple, min_val: int
    ) -> Tuple[Tuple[int, int], int]:
        """
        Find the pair of indices with the same value >= min_val.
        If multiple exist, pick the one with the largest value.

        Args:
            vector: The budget allocation vector.
            min_val: Minimum value required for the items in the pair.
                This ensures that n integer steps are mathematically possible
                when transferring budget between them.
        """
        equal_pairs = []
        for i in range(len(vector)):
            for j in range(i + 1, len(vector)):
                if vector[i] == vector[j] and vector[i] >= min_val:
                    equal_pairs.append(((i, j), vector[i]))

        if not equal_pairs:
            raise UnsuitableForStrategyError(
                get_translation("no_equal_pair_error", "messages")
            )

        # Sort by value DESC, then by indices ASC
        equal_pairs.sort(key=lambda x: (-x[1], x[0]))
        return equal_pairs[0]

    def get_strategy_name(self) -> str:
        """Return unique identifier for this strategy."""
        return "identity_asymmetry"

    def get_option_labels(self) -> Tuple[str, str]:
        """
        Return labels for the options.
        Note: These are generic and will be replaced by dynamic 'Favor {Subject}'
        in the renderer or survey service if possible.
        """
        return ("Favor B", "Favor A")

    def _get_metric_name(self, metric_type: str) -> str:
        """Get the display name for a metric type."""
        return f"Identity {metric_type}"

    def get_table_columns(self) -> Dict[str, Dict]:
        """Get column definitions for the survey response breakdown table."""
        return {
            "identity_consistency": {
                "name": get_translation("identity_consistency", "answers"),
                "type": "percentage",
                "highlight": True,
            },
            "preferred_subject_idx": {
                "name": get_translation("preferred_subject", "answers"),
                "type": "text",
                "highlight": False,
            },
        }
