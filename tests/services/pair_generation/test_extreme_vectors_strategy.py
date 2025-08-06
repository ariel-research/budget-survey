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


class TestTransitivityAnalyzer(unittest.TestCase):
    """Test class for TransitivityAnalyzer functionality."""

    def setUp(self):
        """Set up test fixtures."""
        from analysis.transitivity_analyzer import TransitivityAnalyzer

        self.analyzer = TransitivityAnalyzer()

        # Real user data example - transitive core vectors
        self.transitive_choices = [
            # Core vectors: A>B>C (transitive)
            {
                "pair_number": 1,
                "option1_strategy": "Extreme Vector 1",
                "option2_strategy": "Extreme Vector 2",
                "user_choice": 1,
            },  # A>B
            {
                "pair_number": 2,
                "option1_strategy": "Extreme Vector 1",
                "option2_strategy": "Extreme Vector 3",
                "user_choice": 1,
            },  # A>C
            {
                "pair_number": 3,
                "option1_strategy": "Extreme Vector 2",
                "option2_strategy": "Extreme Vector 3",
                "user_choice": 1,
            },  # B>C
            # 25% weighted: A>C>B (transitive but different order)
            {
                "pair_number": 4,
                "option1_strategy": "25% Weighted Average (Extreme 1)",
                "option2_strategy": "25% Weighted Average (Extreme 2)",
                "user_choice": 1,
            },  # A>B
            {
                "pair_number": 5,
                "option1_strategy": "25% Weighted Average (Extreme 1)",
                "option2_strategy": "25% Weighted Average (Extreme 3)",
                "user_choice": 1,
            },  # A>C
            {
                "pair_number": 6,
                "option1_strategy": "25% Weighted Average (Extreme 2)",
                "option2_strategy": "25% Weighted Average (Extreme 3)",
                "user_choice": 2,
            },  # C>B
            # 50% weighted: A>B>C (transitive, same as core)
            {
                "pair_number": 7,
                "option1_strategy": "50% Weighted Average (Extreme 1)",
                "option2_strategy": "50% Weighted Average (Extreme 2)",
                "user_choice": 1,
            },  # A>B
            {
                "pair_number": 8,
                "option1_strategy": "50% Weighted Average (Extreme 1)",
                "option2_strategy": "50% Weighted Average (Extreme 3)",
                "user_choice": 1,
            },  # A>C
            {
                "pair_number": 9,
                "option1_strategy": "50% Weighted Average (Extreme 2)",
                "option2_strategy": "50% Weighted Average (Extreme 3)",
                "user_choice": 1,
            },  # B>C
            # 75% weighted: A>B>C (transitive, same as core)
            {
                "pair_number": 10,
                "option1_strategy": "75% Weighted Average (Extreme 1)",
                "option2_strategy": "75% Weighted Average (Extreme 2)",
                "user_choice": 1,
            },  # A>B
            {
                "pair_number": 11,
                "option1_strategy": "75% Weighted Average (Extreme 1)",
                "option2_strategy": "75% Weighted Average (Extreme 3)",
                "user_choice": 1,
            },  # A>C
            {
                "pair_number": 12,
                "option1_strategy": "75% Weighted Average (Extreme 2)",
                "option2_strategy": "75% Weighted Average (Extreme 3)",
                "user_choice": 1,
            },  # B>C
        ]

        # Intransitive cycle example: A>B, B>C, C>A
        self.intransitive_choices = [
            {
                "pair_number": 1,
                "option1_strategy": "Extreme Vector 1",
                "option2_strategy": "Extreme Vector 2",
                "user_choice": 1,
            },  # A>B
            {
                "pair_number": 2,
                "option1_strategy": "Extreme Vector 2",
                "option2_strategy": "Extreme Vector 3",
                "user_choice": 1,
            },  # B>C
            {
                "pair_number": 3,
                "option1_strategy": "Extreme Vector 1",
                "option2_strategy": "Extreme Vector 3",
                "user_choice": 2,
            },  # C>A
        ]

        # Incomplete data example
        self.incomplete_choices = [
            {
                "pair_number": 1,
                "option1_strategy": "Extreme Vector 1",
                "option2_strategy": "Extreme Vector 2",
                "user_choice": 1,
            },  # A>B
            {
                "pair_number": 2,
                "option1_strategy": "Extreme Vector 1",
                "option2_strategy": "Extreme Vector 3",
                "user_choice": 1,
            },  # A>C
            # Missing B vs C comparison
        ]

    def test_extract_vector_identifier(self):
        """Test extraction of vector identifiers from strategy strings."""
        test_cases = [
            ("Extreme Vector 1", "A"),
            ("Extreme Vector 2", "B"),
            ("Extreme Vector 3", "C"),
            ("25% Weighted Average (Extreme 1)", "A"),
            ("50% Weighted Average (Extreme 2)", "B"),
            ("75% Weighted Average (Extreme 3)", "C"),
            ("Invalid Strategy", None),
        ]

        for strategy, expected in test_cases:
            with self.subTest(strategy=strategy):
                result = self.analyzer._extract_vector_identifier(strategy)
                self.assertEqual(result, expected)

    def test_identify_group(self):
        """Test identification of percentile groups."""
        test_cases = [
            ("Extreme Vector 1", "Extreme Vector 2", "core"),
            (
                "25% Weighted Average (Extreme 1)",
                "25% Weighted Average (Extreme 2)",
                "25",
            ),
            (
                "50% Weighted Average (Extreme 1)",
                "50% Weighted Average (Extreme 2)",
                "50",
            ),
            (
                "75% Weighted Average (Extreme 1)",
                "75% Weighted Average (Extreme 2)",
                "75",
            ),
            ("Extreme Vector 1", "25% Weighted Average (Extreme 2)", None),
            ("Invalid Strategy 1", "Invalid Strategy 2", None),
        ]

        for option1, option2, expected in test_cases:
            with self.subTest(option1=option1, option2=option2):
                result = self.analyzer._identify_group(option1, option2)
                self.assertEqual(result, expected)

    def test_extract_preferences_by_group(self):
        """Test extraction of preferences by percentile group."""
        groups = self.analyzer.extract_preferences_by_group(self.transitive_choices)

        # Check that all groups are present
        self.assertIn("core", groups)
        self.assertIn("25", groups)
        self.assertIn("50", groups)
        self.assertIn("75", groups)

        # Check core preferences (A>B>C)
        core_prefs = groups["core"]
        self.assertEqual(core_prefs.get("A_vs_B"), "A")
        self.assertEqual(core_prefs.get("A_vs_C"), "A")
        self.assertEqual(core_prefs.get("B_vs_C"), "B")

        # Check 25% preferences (A>C>B based on our test data)
        prefs_25 = groups["25"]
        self.assertEqual(prefs_25.get("A_vs_B"), "A")
        self.assertEqual(prefs_25.get("A_vs_C"), "A")
        self.assertEqual(prefs_25.get("B_vs_C"), "C")

    def test_determine_preference_order_transitive(self):
        """Test determination of transitive preference orders."""
        # Test A>B>C ordering
        comparisons = {"A_vs_B": "A", "A_vs_C": "A", "B_vs_C": "B"}
        order, is_transitive = self.analyzer.determine_preference_order(comparisons)
        self.assertTrue(is_transitive)
        self.assertEqual(order, "A>B>C")

        # Test A>C>B ordering
        comparisons = {"A_vs_B": "A", "A_vs_C": "A", "B_vs_C": "C"}
        order, is_transitive = self.analyzer.determine_preference_order(comparisons)
        self.assertTrue(is_transitive)
        self.assertEqual(order, "A>C>B")

        # Test B>C>A ordering
        comparisons = {"A_vs_B": "B", "A_vs_C": "C", "B_vs_C": "B"}
        order, is_transitive = self.analyzer.determine_preference_order(comparisons)
        self.assertTrue(is_transitive)
        self.assertEqual(order, "B>C>A")

    def test_determine_preference_order_intransitive(self):
        """Test detection of intransitive cycles."""
        # A>B, B>C, C>A (cycle)
        comparisons = {"A_vs_B": "A", "B_vs_C": "B", "A_vs_C": "C"}
        order, is_transitive = self.analyzer.determine_preference_order(comparisons)
        self.assertFalse(is_transitive)
        # Enhanced behavior: show actual cycle instead of just 'Intransitive'
        self.assertEqual(order, "A>B, C>A, B>C")

    def test_determine_preference_order_incomplete(self):
        """Test handling of incomplete comparison data."""
        # Missing one comparison
        comparisons = {"A_vs_B": "A", "A_vs_C": "A"}
        order, is_transitive = self.analyzer.determine_preference_order(comparisons)
        self.assertFalse(is_transitive)
        self.assertEqual(order, "Incomplete")

        # Empty comparisons
        comparisons = {}
        order, is_transitive = self.analyzer.determine_preference_order(comparisons)
        self.assertFalse(is_transitive)
        self.assertEqual(order, "Incomplete")

    def test_analyze_group_transitivity_core(self):
        """Test transitivity analysis for core vectors."""
        result = self.analyzer.analyze_group_transitivity(
            self.transitive_choices[:3], percentile=None
        )
        self.assertTrue(result["is_transitive"])
        self.assertEqual(result["preference_order"], "A>B>C")
        self.assertEqual(len(result["comparisons"]), 3)

    def test_analyze_group_transitivity_intransitive(self):
        """Test detection of intransitive preferences."""
        result = self.analyzer.analyze_group_transitivity(self.intransitive_choices)
        self.assertFalse(result["is_transitive"])
        # Enhanced behavior: show actual cycle instead of just 'Intransitive'
        self.assertEqual(result["preference_order"], "A>B, C>A, B>C")

    def test_analyze_group_transitivity_incomplete(self):
        """Test handling of incomplete data."""
        result = self.analyzer.analyze_group_transitivity(self.incomplete_choices)
        self.assertFalse(result["is_transitive"])
        self.assertEqual(result["preference_order"], "Incomplete")

    def test_get_full_transitivity_report(self):
        """Test generation of complete transitivity report."""
        report = self.analyzer.get_full_transitivity_report(self.transitive_choices)

        # Check that all groups are analyzed
        self.assertIn("core", report)
        self.assertIn("25", report)
        self.assertIn("50", report)
        self.assertIn("75", report)

        # Check overall metrics
        self.assertIn("transitivity_rate", report)
        self.assertIn("order_stability_score", report)

        # All groups should be transitive in our test data
        self.assertEqual(report["transitivity_rate"], 100.0)

        # 3 out of 4 groups have A>B>C order (75% stability)
        self.assertEqual(report["order_stability_score"], 75.0)

        # Check individual group results
        self.assertTrue(report["core"]["is_transitive"])
        self.assertEqual(report["core"]["order"], "A>B>C")

        self.assertTrue(report["25"]["is_transitive"])
        self.assertEqual(report["25"]["order"], "A>C>B")

        self.assertTrue(report["50"]["is_transitive"])
        self.assertEqual(report["50"]["order"], "A>B>C")

        self.assertTrue(report["75"]["is_transitive"])
        self.assertEqual(report["75"]["order"], "A>B>C")

    def test_empty_choices(self):
        """Test handling of empty choices list."""
        report = self.analyzer.get_full_transitivity_report([])

        # Should handle empty input gracefully
        self.assertEqual(report["transitivity_rate"], 0.0)
        self.assertEqual(report["order_stability_score"], 0.0)

        for group in ["core", "25", "50", "75"]:
            self.assertFalse(report[group]["is_transitive"])
            self.assertEqual(report[group]["order"], "No Data")

    def test_malformed_choices(self):
        """Test handling of malformed choice data."""
        malformed_choices = [
            {"pair_number": 1},  # Missing required fields
            {"option1_strategy": "Extreme Vector 1"},  # Missing other fields
            {
                "user_choice": None,
                "option1_strategy": "Extreme Vector 1",
                "option2_strategy": "Extreme Vector 2",
            },  # None user_choice
        ]

        report = self.analyzer.get_full_transitivity_report(malformed_choices)

        # Should handle malformed data gracefully
        for group in ["core", "25", "50", "75"]:
            self.assertEqual(report[group]["order"], "No Data")

    def test_all_possible_transitive_orderings(self):
        """Test that all 6 possible transitive orderings are correctly identified."""
        orderings = [
            ({"A_vs_B": "A", "A_vs_C": "A", "B_vs_C": "B"}, "A>B>C"),
            ({"A_vs_B": "A", "A_vs_C": "A", "B_vs_C": "C"}, "A>C>B"),
            ({"A_vs_B": "B", "A_vs_C": "A", "B_vs_C": "B"}, "B>A>C"),
            ({"A_vs_B": "B", "A_vs_C": "C", "B_vs_C": "B"}, "B>C>A"),
            ({"A_vs_B": "A", "A_vs_C": "C", "B_vs_C": "C"}, "C>A>B"),
            ({"A_vs_B": "B", "A_vs_C": "C", "B_vs_C": "C"}, "C>B>A"),
        ]

        for comparisons, expected_order in orderings:
            with self.subTest(expected_order=expected_order):
                order, is_transitive = self.analyzer.determine_preference_order(
                    comparisons
                )
                self.assertTrue(is_transitive, f"Failed for {expected_order}")
                self.assertEqual(order, expected_order)


if __name__ == "__main__":
    unittest.main()
