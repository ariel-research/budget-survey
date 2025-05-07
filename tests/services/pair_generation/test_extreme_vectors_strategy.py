import unittest
from unittest.mock import patch

import numpy as np

from application.services.pair_generation import ExtremeVectorsStrategy


class TestExtremeVectorsStrategy(unittest.TestCase):
    def setUp(self):
        self.strategy = ExtremeVectorsStrategy()
        self.user_vector = (70, 20, 10)
        self.vector_size = 3

    def test_generate_extreme_vectors(self):
        """Test generation of extreme vectors."""
        extremes = self.strategy._generate_extreme_vectors(self.vector_size)

        # Should create 3 vectors for vector_size=3
        self.assertEqual(len(extremes), self.vector_size)

        # Each vector should have one 100 and the rest 0
        for v in extremes:
            self.assertEqual(np.sum(v), 100)
            self.assertEqual(np.max(v), 80)
            # Should have exactly one non-zero element
            self.assertEqual(np.count_nonzero(v), 3)

    def test_calculate_weighted_vector(self):
        """Test weighted average calculation."""
        user_vector = np.array(self.user_vector)
        extreme_vector = np.array([100, 0, 0])
        weight = 0.5

        result = self.strategy._calculate_weighted_vector(
            user_vector, extreme_vector, weight
        )
        expected = (85, 10, 5)  # 0.5*[100,0,0] + 0.5*[70,20,10]

        self.assertEqual(result, expected)
        self.assertEqual(sum(result), 100)  # Should sum to 100

    def test_generate_pairs(self):
        """Test pair generation."""
        pairs = self.strategy.generate_pairs(self.user_vector)

        # Check we have the right number of pairs
        self.assertGreaterEqual(len(pairs), 3)  # At least the extreme pairs

        # Check structure of each pair
        for pair in pairs:
            # Filter out metadata keys (option1_strategy, option2_strategy)
            vector_pairs = {k: v for k, v in pair.items() if not k.startswith("option")}

            # Should be a dict with 2 vector items
            self.assertEqual(len(vector_pairs), 2)

            # Values should be tuples of length 3
            for key, value in vector_pairs.items():
                self.assertIsInstance(value, tuple)
                self.assertEqual(len(value), self.vector_size)
                self.assertEqual(sum(value), 100)

    @patch(
        "application.services.pair_generation.extreme_vectors_strategy.get_translation"
    )
    def test_option_labels(self, mock_get_translation):
        """Test option labels."""
        # Set up the mock to return English values
        mock_get_translation.side_effect = lambda key, *args, **kwargs: {
            "extreme_1": "Extreme 1",
            "extreme_2": "Extreme 2",
        }.get(key, key)

        labels = self.strategy.get_option_labels()
        self.assertEqual(len(labels), 2)
        self.assertEqual(labels, ("Extreme 1", "Extreme 2"))

    def test_strategy_name(self):
        """Test strategy name."""
        self.assertEqual(self.strategy.get_strategy_name(), "extreme_vectors")


if __name__ == "__main__":
    unittest.main()
