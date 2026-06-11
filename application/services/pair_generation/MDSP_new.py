"""Implementation of the updated original MDSP strategy with weights and multiples of 5."""

import logging
import random
from typing import Dict, List, Set, Tuple

import numpy as np

from application.services.pair_generation.base import PairGenerationStrategy
from application.translations import get_translation

logger = logging.getLogger(__name__)


class MultiDimensionalSinglePeakedStrategy(PairGenerationStrategy):
    """
        Multi-Dimensional Single-Peaked (MDSP) Pair Generation Strategy.

        This algorithm generates pairs of budget allocation vectors (Far vs. Near)
        to test user preferences under MDSP utility functions. It ensures that the
        'Near' vector is strictly closer to the user's ideal peak than the 'Far' vector
        on a localized dimension pair, reducing cognitive load by keeping all other
        dimensions completely frozen.

        Algorithm Steps:
        1. Generate a valid random budget vector (Far), rounded to multiples of 5.
        2. Compare 'Far' to the 'User Ideal' to find 'over-budget' and 'under-budget' dimensions.
        3. Randomly select exactly one over-budget dimension (i) and one under-budget dimension (j).
        4. Calculate the maximum valid budget transfer (Max Delta) from i to j without
           overshooting the User's Ideal in either dimension.
        5. Multiply Max Delta by a predefined weight (e.g., 0.1 to 0.9) to get the exact Target Delta.
        6. Transfer the Target Delta from i to j to create a continuous 'Near' vector.
        7. Round the 'Near' vector to multiples of 5 and balance it to strictly sum to 100.
        8. Filter out collisions (e.g., if Near == Far) to ensure unique data points.

        Example:
            User Ideal : (40, 30, 30)
            Random Far : (70, 25, 5)
            Weight     : 0.7

            Step A: Identify dimensions & Max Delta
                - Dim 1 (Over) : 70 vs 40 -> Max we can take is 30
                - Dim 3 (Under): 5 vs 30  -> Max we can give is 25
                - Max Delta = min(30, 25) = 25
                - Dim 2 is completely frozen at 25.

            Step B: Apply Weight
                - Target Delta = 25 * 0.7 = 17.5

            Step C: Continuous Transfer
                - Exact Near = (70 - 17.5, 25, 5 + 17.5) = (52.5, 25, 22.5)

            Step D: Round to 5 & Balance
                - Rounding: 52.5 -> 50, 25 -> 25, 22.5 -> 20 (Sum: 95)
                - Balancing: We need 5 more to reach 100. Both Dim 1 and Dim 3 lost 2.5
                  due to rounding down. The algorithm optimally returns the 5 to Dim 1.
                - Final Near = (55, 25, 20)

            Actual Displayed Delta: round(17.5) = 18.
        """
    MAX_ATTEMPTS = 10000
    WEIGHTS = [0.1, 0.2, 0.3, 0.4, 0.5, 0.5, 0.6, 0.7, 0.8, 0.9]

    def _round_to_5_and_balance(self, vector: np.ndarray) -> np.ndarray:
        """Round vector elements to nearest 5 while maintaining sum of 100."""
        rounded = np.round(vector / 5) * 5
        diff = int(100 - np.sum(rounded))

        if diff != 0:
            errors = vector - rounded
            while diff > 0:
                idx = np.argmax(errors)
                rounded[idx] += 5
                errors[idx] -= 5
                diff -= 5
            while diff < 0:
                idx = np.argmin(errors)
                rounded[idx] -= 5
                errors[idx] += 5
                diff += 5

        return rounded.astype(int)

    def create_random_vector_unrestricted(self, size: int = 3) -> tuple:
        """Generate a random vector summing to 100."""
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
        Generate MDSP pairs transferring budget between two dimensions,
        scaled by a specific weight sequence and rounded to 5.
        """
        self._validate_vector(user_vector, vector_size)
        user_vector_array = np.array(user_vector)

        pairs: List[Dict[str, tuple]] = []
        seen_vectors: Set[tuple] = {user_vector}
        used_near_vectors: Set[tuple] = set()

        attempts = 0
        max_attempts = self.MAX_ATTEMPTS

        while len(pairs) < n and attempts < max_attempts:
            attempts += 1
            try:
                q_far_raw = self.create_random_vector_unrestricted(vector_size)
                q_far = tuple(self._round_to_5_and_balance(np.array(q_far_raw)))

                if q_far in seen_vectors:
                    continue

                over_budget_dims = [d for d in range(vector_size) if q_far[d] > user_vector[d]]
                under_budget_dims = [d for d in range(vector_size) if q_far[d] < user_vector[d]]

                if not over_budget_dims or not under_budget_dims:
                    continue

                i = random.choice(over_budget_dims)
                j = random.choice(under_budget_dims)
                max_delta = min(q_far[i] - user_vector[i], user_vector[j] - q_far[j])

                if max_delta < 1:
                    continue

                x_weight = self.WEIGHTS[len(pairs)]
                target_delta = max_delta * x_weight

                exact_near = np.array(q_far, dtype=float)
                exact_near[i] -= target_delta
                exact_near[j] += target_delta

                q_near = tuple(self._round_to_5_and_balance(exact_near))

                actual_delta = int(round(target_delta))

                if q_near == q_far or q_near in used_near_vectors or q_near in seen_vectors:
                    continue

                pair_entry = {
                    self.get_option_description(role="far"): q_far,
                    self.get_option_description(role="near", weight=x_weight, delta=actual_delta): q_near,
                }
                pairs.append(pair_entry)

                seen_vectors.add(q_far)
                used_near_vectors.add(q_near)
                seen_vectors.add(q_near)

            except ValueError:
                pass

        if len(pairs) < n:
            raise ValueError(
                f"Could not generate {n} unique MDSP pairs after {max_attempts} attempts."
            )

        random.shuffle(pairs)
        return pairs

    def get_strategy_name(self) -> str:
        return "multi_dimensional_single_peaked_test"

    def get_option_labels(self) -> Tuple[str, str]:
        return (
            "Far",
            "Near",
        )

    def get_option_description(self, **kwargs) -> str:
        """Return label with Weight and Delta for Near vector."""
        role = kwargs.get("role")
        if role == "far":
            return "Far"

        weight = kwargs.get("weight")
        delta = kwargs.get("delta")
        return f"Near (Weight: {weight}, Delta: {delta})"

    def _get_metric_name(self, metric_type: str) -> str:
        if metric_type == "delta":
            return "Near Vector"
        return "Far Vector"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    strategy = MultiDimensionalSinglePeakedStrategy()
    user_peak = (40, 30, 30)

    print("Starting Original MDSP Strategy Test (with new logic)...\n")
    print(f"User Peak (Ideal): {user_peak}")
    print("-" * 50)

    try:
        generated_pairs = strategy.generate_pairs(user_vector=user_peak, n=10, vector_size=3)

        print("\nResults:")
        for i, pair in enumerate(generated_pairs, 1):
            print(f"--- Pair {i} ---")
            for option_name, vector in pair.items():
                clean_vector = tuple(int(x) for x in vector)
                print(f"{option_name}: {clean_vector}")

    except Exception as e:
        print(f"Error generating pairs: {e}")