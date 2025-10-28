"""
Triangle Inequality Test strategy for biennial budget allocations.

This strategy tests whether users' distance metrics satisfy the triangle inequality:
||q|| ≤ ||q1|| + ||q2|| where q = q1 + q2

Implements Algorithm 12 from the research paper with a screening phase to filter
participants who use balancing utility models rather than additive models.
"""

import logging
from typing import Dict, List, Tuple

import numpy as np

from application.exceptions import UnsuitableForStrategyError
from application.services.pair_generation.base import PairGenerationStrategy

logger = logging.getLogger(__name__)


class TriangleInequalityStrategy(PairGenerationStrategy):
    """
    Strategy that generates 12 comparison pairs to test triangle inequality.

    Compares concentrated changes (entire deviation in one year) versus
    distributed changes (deviation split across two years).

    Structure: 2 base vectors × 3 rotations × 2 variants (positive/negative) = 12 pairs

    Each pair represents biennial budgets (Year 1, Year 2) stored as flattened
    6-element arrays.
    """

    def generate_pairs(
        self, user_vector: tuple, n: int = 12, vector_size: int = 3
    ) -> List[Dict[str, tuple]]:
        """
        Generate 12 comparison pairs for triangle inequality testing.

        Args:
            user_vector: User's ideal budget allocation
            n: Number of pairs to generate (ignored, always generates 12)
            vector_size: Size of each allocation vector (always 3)

        Returns:
            List of 12 dicts containing biennial budget comparison pairs

        Raises:
            UnsuitableForStrategyError: If user vector contains zero values
            ValueError: If unable to generate required pairs
        """
        # Check for zero values
        if 0 in user_vector:
            logger.info(f"User vector {user_vector} contains zero values")
            raise UnsuitableForStrategyError(
                "User vector contains zero values and is unsuitable for "
                "triangle inequality strategy"
            )

        # Validate inputs
        self._validate_vector(user_vector, vector_size)

        if n != 12:
            logger.warning(f"Strategy designed for 12 pairs but got n={n}, using 12")
            n = 12

        logger.info(f"Generating {n} triangle inequality pairs")

        all_pairs = []

        # Generate 2 base change vectors with multiple attempts
        max_base_attempts = 100
        successful_bases = 0

        for attempt in range(max_base_attempts):
            if successful_bases >= 2:
                break

            try:
                # Generate base change vector q
                q = self._generate_base_change_vector(user_vector, vector_size)

                # Decompose q into q1 and q2
                # This may raise ValueError if decomposition is degenerate
                q1, q2 = self._decompose_change_vector(q)

                # Verify decomposition
                if not np.allclose(np.array(q1) + np.array(q2), np.array(q)):
                    continue

                # Try all 3 rotations for this base vector
                base_pairs = []
                for rotation in range(3):
                    # Apply rotation
                    q_rot = self._rotate_vector(q, rotation)
                    q1_rot = self._rotate_vector(q1, rotation)
                    q2_rot = self._rotate_vector(q2, rotation)

                    # Generate positive variant: (p, p+q) vs (p+q1, p+q2)
                    pos_pair = self._generate_pair_variant(
                        user_vector,
                        q_rot,
                        q1_rot,
                        q2_rot,
                        variant="positive",
                        group_num=successful_bases + 1,
                        rotation=rotation,
                    )
                    if pos_pair:
                        base_pairs.append(pos_pair)

                    # Generate negative variant: (p, p-q) vs (p-q1, p-q2)
                    neg_pair = self._generate_pair_variant(
                        user_vector,
                        q_rot,
                        q1_rot,
                        q2_rot,
                        variant="negative",
                        group_num=successful_bases + 1,
                        rotation=rotation,
                    )
                    if neg_pair:
                        base_pairs.append(neg_pair)

                # Only accept this base if we got all 6 pairs (3 rotations × 2 variants)
                if len(base_pairs) == 6:
                    all_pairs.extend(base_pairs)
                    successful_bases += 1

            except ValueError:
                # Failed to generate valid base vector, try again
                continue

        if len(all_pairs) < 12:
            raise ValueError(f"Unable to generate 12 pairs, only got {len(all_pairs)}")

        # Take exactly 12 pairs
        final_pairs = all_pairs[:12]

        logger.info(
            f"Generated {len(final_pairs)} triangle inequality pairs "
            f"using {self.__class__.__name__}"
        )
        self._log_pairs(final_pairs)

        return final_pairs

    def _generate_base_change_vector(
        self, user_vector: tuple, vector_size: int
    ) -> np.ndarray:
        """
        Generate a base change vector q where:
        - sum(q) = 0
        - Each element is multiple of 5
        - q ≠ [0, 0, 0]
        - p ± q produces valid budgets
        - After decomposition, p ± q1 and p ± q2 also produce valid budgets

        Args:
            user_vector: User's ideal budget
            vector_size: Size of vector (3)

        Returns:
            Change vector q as numpy array
        """
        user_array = np.array(user_vector)
        max_attempts = 1000

        for _ in range(max_attempts):
            # Generate random multiples of 5 that sum to 0
            # Use conservative range to ensure valid budgets even after decomposition
            min_val = min(user_vector)
            max_val = max(user_vector)

            # After decomposition q1=[x1,0,-x1] and q2=[0,x2,-x2]
            # We need p±x1 and p±x2 to be valid for all positions
            max_change = min(min_val, 100 - max_val) // 5
            max_change = max(1, max_change // 2)

            if max_change < 1:
                max_change = 1

            # Generate first two elements
            q = []
            for _ in range(vector_size - 1):
                change = np.random.randint(-max_change, max_change + 1) * 5
                q.append(change)

            # Last element ensures sum = 0
            q.append(-sum(q))
            q = np.array(q)

            # Check if all zeros
            if np.all(q == 0):
                continue

            # Check if at least one meaningful difference
            if not any(abs(d) >= 5 for d in q):
                continue

            # Validate both addition and subtraction
            vec_plus = user_array + q
            vec_minus = user_array - q

            if not (
                np.all(vec_plus >= 0)
                and np.all(vec_plus <= 100)
                and np.all(vec_minus >= 0)
                and np.all(vec_minus <= 100)
            ):
                continue

            # Check decomposed components
            try:
                q1, q2 = self._decompose_change_vector(q)
            except ValueError:
                # Degenerate decomposition, skip this q
                continue

            # Validate p ± q1
            vec_plus_q1 = user_array + q1
            vec_minus_q1 = user_array - q1

            # Validate p ± q2
            vec_plus_q2 = user_array + q2
            vec_minus_q2 = user_array - q2

            if (
                np.all(vec_plus_q1 >= 0)
                and np.all(vec_plus_q1 <= 100)
                and np.all(vec_minus_q1 >= 0)
                and np.all(vec_minus_q1 <= 100)
                and np.all(vec_plus_q2 >= 0)
                and np.all(vec_plus_q2 <= 100)
                and np.all(vec_minus_q2 >= 0)
                and np.all(vec_minus_q2 <= 100)
            ):
                return q

        raise ValueError("Unable to generate valid base change vector")

    def _decompose_change_vector(self, q: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Decompose change vector q into q1 and q2 using the pattern from paper.

        Pattern:
            q = [x1, x2, x3]
            q1 = [x1, 0, -x1]
            q2 = [0, x2, -x2]

        This ensures q1 + q2 = q and creates split components.

        Args:
            q: Change vector to decompose

        Returns:
            Tuple of (q1, q2) as numpy arrays

        Raises:
            ValueError: If decomposition produces degenerate components (all zeros)
        """
        x1, x2, x3 = q

        q1 = np.array([x1, 0, -x1])
        q2 = np.array([0, x2, -x2])

        # Verify: q1 + q2 should equal q
        # Note: x1 + 0 = x1, 0 + x2 = x2, -x1 + (-x2) = -(x1+x2) = x3
        # because x1 + x2 + x3 = 0, so x3 = -(x1+x2)

        # Validate decomposition produces non-degenerate components
        # This is required for meaningful triangle inequality testing
        if np.all(q1 == 0) or np.all(q2 == 0):
            raise ValueError(
                f"Degenerate decomposition: q={q} produces "
                f"q1={q1} or q2={q2} as zero vector"
            )

        return q1, q2

    def _rotate_vector(self, v: np.ndarray, rotation: int) -> np.ndarray:
        """
        Apply coordinate rotation to vector.

        Args:
            v: Vector to rotate
            rotation: Number of positions to rotate (0, 1, or 2)

        Returns:
            Rotated vector
        """
        if rotation == 0:
            return v
        return np.roll(v, rotation)

    def _generate_pair_variant(
        self,
        user_vector: tuple,
        q: np.ndarray,
        q1: np.ndarray,
        q2: np.ndarray,
        variant: str,
        group_num: int,
        rotation: int,
    ) -> Dict:
        """
        Generate a single pair variant (positive or negative).

        Args:
            user_vector: User's ideal budget
            q: Change vector
            q1: First component of q
            q2: Second component of q
            variant: "positive" or "negative"
            group_num: Base vector group number (1-2)
            rotation: Rotation number (0-2)

        Returns:
            Pair dictionary with flattened biennial budgets
        """
        user_array = np.array(user_vector)
        sign = 1 if variant == "positive" else -1

        # Concentrated: (p, p ± q)
        year1_concentrated = user_array
        year2_concentrated = user_array + sign * q

        # Distributed: (p ± q1, p ± q2)
        year1_distributed = user_array + sign * q1
        year2_distributed = user_array + sign * q2

        # Validate all vectors
        all_vecs = [
            year1_concentrated,
            year2_concentrated,
            year1_distributed,
            year2_distributed,
        ]

        for vec in all_vecs:
            if not (
                np.all(vec >= 0)
                and np.all(vec <= 100)
                and abs(np.sum(vec) - 100) < 0.01
            ):
                logger.debug(f"Invalid vector in pair: {vec}")
                return None

        # Convert to integer tuples
        year1_concentrated = tuple(int(v) for v in year1_concentrated)
        year2_concentrated = tuple(int(v) for v in year2_concentrated)
        year1_distributed = tuple(int(v) for v in year1_distributed)
        year2_distributed = tuple(int(v) for v in year2_distributed)

        # Flatten to 6-element arrays
        concentrated = self._flatten_biennial_budget(
            year1_concentrated, year2_concentrated
        )
        distributed = self._flatten_biennial_budget(
            year1_distributed, year2_distributed
        )

        # Calculate differences
        # Concentrated: Year 1 no change, Year 2 has full change
        diff_concentrated = [0, 0, 0] + [int(sign * d) for d in q]

        # Distributed: Year 1 has q1 change, Year 2 has q2 change
        diff_distributed = [int(sign * d) for d in q1] + [int(sign * d) for d in q2]

        # Create pair
        sign_symbol = "+" if variant == "positive" else "-"

        pair = {
            f"Triangle Concentrated ({sign_symbol}) - G{group_num} R{rotation}": concentrated,
            f"Triangle Distributed ({sign_symbol}) - G{group_num} R{rotation}": distributed,
            "option1_differences": diff_concentrated,
            "option2_differences": diff_distributed,
            "group_number": group_num,
            "rotation_number": rotation,
            "variant": variant,
            "is_biennial": True,
        }

        return pair

    def _flatten_biennial_budget(self, year1: tuple, year2: tuple) -> list:
        """
        Flatten two 3-element year budgets into single 6-element array.

        Args:
            year1: Budget for year 1
            year2: Budget for year 2

        Returns:
            Flattened list [year1_vals..., year2_vals...]
        """
        return list(year1) + list(year2)

    def get_strategy_name(self) -> str:
        """Return unique identifier for this strategy."""
        return "triangle_inequality_test"

    def get_option_labels(self) -> Tuple[str, str]:
        """
        Return labels for the two options being compared.

        Backend uses descriptive names, frontend shows neutral labels.
        """
        return ("Concentrated Change", "Distributed Change")

    def _get_metric_name(self, metric_type: str) -> str:
        """Get descriptive name for metrics."""
        metric_names = {
            "concentrated": "Concentrated Change",
            "distributed": "Distributed Change",
            "consistency": "Triangle Inequality Consistency",
        }
        return metric_names.get(metric_type, metric_type.replace("_", " ").title())

    def get_table_columns(self) -> Dict[str, Dict]:
        """
        Get column definitions for the survey response breakdown table.

        Returns:
            Dict: Column definitions for triangle inequality analysis
        """
        return {
            "concentrated_preference": {
                "name": "Concentrated Change",
                "type": "percentage",
                "highlight": True,
            },
            "distributed_preference": {
                "name": "Distributed Change",
                "type": "percentage",
                "highlight": True,
            },
            "triangle_consistency": {
                "name": "Triangle Inequality Consistency",
                "type": "percentage",
                "highlight": True,
            },
        }

    def is_ranking_based(self) -> bool:
        """
        Identify if this strategy uses ranking questions.

        Returns:
            bool: False, as this strategy uses pairwise comparisons
        """
        return False
