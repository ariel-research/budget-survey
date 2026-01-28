import unittest

from application.exceptions import UnsuitableForStrategyError
from application.services.pair_generation.identity_asymmetry_strategy import (
    IdentityAsymmetryStrategy,
)


class TestIdentityAsymmetryStrategy(unittest.TestCase):
    def setUp(self):
        self.strategy = IdentityAsymmetryStrategy()

    def test_get_strategy_name(self):
        self.assertEqual(self.strategy.get_strategy_name(), "identity_asymmetry")

    def test_find_largest_equal_pair_simple(self):
        vector = (30, 30, 40)
        (idx_a, idx_b), value = self.strategy._find_largest_equal_pair(
            vector, min_val=10
        )
        self.assertEqual(idx_a, 0)
        self.assertEqual(idx_b, 1)
        self.assertEqual(value, 30)

    def test_find_largest_equal_pair_multiple(self):
        # [20, 20, 30, 30] -> should pick indices (2, 3) with value 30
        vector = (20, 20, 30, 30)
        (idx_a, idx_b), value = self.strategy._find_largest_equal_pair(
            vector, min_val=10
        )
        self.assertEqual(idx_a, 2)
        self.assertEqual(idx_b, 3)
        self.assertEqual(value, 30)

    def test_find_largest_equal_pair_tie_value(self):
        # [30, 30, 30] -> should pick (0, 1) with value 30 (deterministic by index)
        vector = (30, 30, 30)
        (idx_a, idx_b), value = self.strategy._find_largest_equal_pair(
            vector, min_val=10
        )
        self.assertEqual(idx_a, 0)
        self.assertEqual(idx_b, 1)
        self.assertEqual(value, 30)

    def test_unsuitable_vector_no_equal(self):
        vector = (10, 20, 70)
        with self.assertRaises(UnsuitableForStrategyError):
            self.strategy.generate_pairs(vector)

    def test_unsuitable_vector_small_equal(self):
        # Pair exists but value < 10
        vector = (5, 5, 90)
        with self.assertRaises(UnsuitableForStrategyError):
            self.strategy.generate_pairs(vector)

    def test_generate_pairs_math_integrity(self):
        user_vector = (30, 30, 40)
        # target = 30, step = 3.0
        # step 1: mag = 3
        # step 10: mag = 30
        pairs = self.strategy.generate_pairs(user_vector)
        self.assertEqual(len(pairs), 10)

        for i, pair in enumerate(pairs, 1):
            opt1 = pair["Option 1"]
            opt2 = pair["Option 2"]
            self.assertEqual(sum(opt1), 100)
            self.assertEqual(sum(opt2), 100)

            metadata = pair["__metadata__"]
            self.assertEqual(metadata["step_number"], i)

            # Verify magnitude rounding
            expected_mag = int(round(3.0 * i))
            self.assertEqual(metadata["magnitude"], expected_mag)

            # Verify vectors
            # idx_a=0, idx_b=1
            self.assertEqual(opt1[0], user_vector[0] - expected_mag)
            self.assertEqual(opt1[1], user_vector[1] + expected_mag)
            self.assertEqual(opt2[0], user_vector[0] + expected_mag)
            self.assertEqual(opt2[1], user_vector[1] - expected_mag)

    def test_metadata_structure(self):
        user_vector = (30, 30, 40)
        pairs = self.strategy.generate_pairs(user_vector)
        metadata = pairs[0]["__metadata__"]

        expected_keys = {
            "pair_type",
            "subject_a_idx",
            "subject_b_idx",
            "step_number",
            "magnitude",
            "option_1_favors_idx",
            "option_2_favors_idx",
        }
        self.assertTrue(expected_keys.issubset(metadata.keys()))
        self.assertEqual(metadata["pair_type"], "identity_test")


if __name__ == "__main__":
    unittest.main()
