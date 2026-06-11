"""Implementation of the multi-dimensional single-peaked (MDSP) strategy."""

import logging
import random
from typing import Dict, List, Set, Tuple

import numpy as np

from application.services.pair_generation.base import PairGenerationStrategy
from application.translations import get_translation

logger = logging.getLogger(__name__)


class MultiDimensionalSinglePeakedStrategy(PairGenerationStrategy):
    """Generate pairs that test multi-dimensional single-peaked preferences."""

    MAX_ATTEMPTS = 10000
    def create_random_vector_unrestricted(self, size: int = 3) -> tuple:
        """
        Generate a random vector summing to 100 without divisibility limits.

        Used by MDSP to broaden the candidate space for extreme user vectors.
        """
        max_attempts = 100

        for _ in range(max_attempts):
            vector = np.random.rand(size)
            vector = np.floor(vector / vector.sum() * 100).astype(int)
            vector[-1] = 100 - vector[:-1].sum()

            if np.all(vector >= 0) and np.all(vector <= 100):
                np.random.shuffle(vector)
                return tuple(int(v) for v in vector)

        raise ValueError("Could not generate valid random vector")

    def generate_pairs(
            self, user_vector: tuple, n: int = 10, vector_size: int = 3
    ) -> List[Dict[str, tuple]]:
        """
        Generate MDSP test pairs using a constructive mathematical approach.

        Instead of rejection sampling, this constructs a 'near' vector directly
        from a random 'far' vector by transferring budget strictly toward the user's peak.

        Args:
            user_vector: The user's ideal budget allocation (peak).
            n: Number of pairs to generate (default: 10).
            vector_size: Number of dimensions in the allocation vectors.

        Returns:
            List of dicts mapping option descriptions to allocation vectors.

        Raises:
            ValueError: If unable to generate the required number of pairs.
        """
        self._validate_vector(user_vector, vector_size)

        pairs: List[Dict[str, tuple]] = []
        seen_pairs: Set[Tuple[tuple, tuple]] = set()

        attempts = 0
        max_attempts = self.MAX_ATTEMPTS
        peak = user_vector

        while len(pairs) < n and attempts < max_attempts:
            attempts += 1

            # 1. Sample a random 'far' allocation
            q_far = self.create_random_vector_unrestricted(vector_size)

            # Avoid using the peak itself as the starting point
            if q_far == peak:
                continue

            # 2. Identify over-budget and under-budget dimensions relative to the peak
            over_budget_dims = [d for d in range(vector_size) if q_far[d] > peak[d]]
            under_budget_dims = [d for d in range(vector_size) if q_far[d] < peak[d]]

            if not over_budget_dims or not under_budget_dims:
                continue

            # 3. Choose one dimension to decrease and one to increase
            i = random.choice(over_budget_dims)
            j = random.choice(under_budget_dims)

            # 4. Calculate maximum valid integer transfer to avoid crossing the peak
            max_delta = min(q_far[i] - peak[i], peak[j] - q_far[j])

            # Ensure we can make a strictly positive integer improvement
            if max_delta < 1:
                continue

            # 5. Sample a random transfer amount (Integer)
            delta = random.randint(1, max_delta)

            # 6. Construct the 'near' allocation
            q_near_list = list(q_far)
            q_near_list[i] -= delta
            q_near_list[j] += delta
            q_near = tuple(q_near_list)

            candidate_pair = (q_far, q_near)

            # 7. Check for uniqueness
            if candidate_pair in seen_pairs:
                continue

            seen_pairs.add(candidate_pair)

            pair_entry = {
                self.get_option_description(role="far"): q_far,
                self.get_option_description(role="near"): q_near,
            }
            pairs.append(pair_entry)

        if len(pairs) < n:
            raise ValueError(
                f"Could not generate {n} unique MDSP pairs after "
                f"{max_attempts} attempts."
            )

        random.shuffle(pairs)

        # Logging success rate - it should be very close to 100% now!
        success_rate = 100 * len(pairs) / attempts if attempts > 0 else 0
        logger.info(
            "Generated %d MDSP pairs in %d attempts using %s (success rate: %.2f%%)",
            len(pairs),
            attempts,
            self.__class__.__name__,
            success_rate,
        )
        self._log_pairs(pairs)
        return pairs

    def get_strategy_name(self) -> str:
        """Return the strategy identifier."""
        return "multi_dimensional_single_peaked_test"

    def get_option_labels(self) -> Tuple[str, str]:
        return (
            get_translation("far_vector", "answers"),
            get_translation("near_vector", "answers"),
        )

    def get_option_description(self, **kwargs) -> str:
        role = kwargs.get("role")
        if role == "far":
            return "Further Vector"
        return "Nearer Vector"

    def _get_metric_name(self, metric_type: str) -> str:
        """Provide metric display name required by the base class."""
        return "Vector"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    strategy = MultiDimensionalSinglePeakedStrategy()

    user_peak = (20, 30, 50)

    print(f"\n--- Testing MDSP Strategy ---")
    print(f"User Peak (Ideal): {user_peak}")
    print("-" * 50)

    try:
        generated_pairs = strategy.generate_pairs(user_vector=user_peak, n=5, vector_size=3)

        print("\n--- Results ---")
        for i, pair in enumerate(generated_pairs, 1):
            far_vec = pair["Further Vector"]
            near_vec = pair["Nearer Vector"]

            diff = tuple(n - f for f, n in zip(far_vec, near_vec))

            print(f"Pair {i}:")
            print(f"  Far Vector  (q_far) : {far_vec}  | Sum: {sum(far_vec)}")
            print(f"  Near Vector (q_near): {near_vec}  | Sum: {sum(near_vec)}")
            print(f"  Difference          : {diff}   (+\\-)")
            print("-" * 50)

    except Exception as e:
        print(f"Error generating pairs: {e}")