"""
Tests for Dynamic Temporal Preference Test strategy.

Tests the comprehensive dynamic temporal preference testing strategy that
implements a 12-question survey with three 4-question sub-surveys.
"""

from unittest.mock import patch

import pytest

from application.exceptions import UnsuitableForStrategyError
from application.services.pair_generation.dynamic_temporal_preference_strategy import (
    DynamicTemporalPreferenceStrategy,
)


class TestDynamicTemporalPreferenceStrategy:
    """Test suite for DynamicTemporalPreferenceStrategy class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.strategy = DynamicTemporalPreferenceStrategy()
        # Standard test vector
        self.test_vector = (60, 25, 15)
        # Extreme test vector for fallback testing
        self.extreme_vector = (95, 5, 0)

    def test_strategy_name(self):
        """Test that strategy returns correct name."""
        assert self.strategy.get_strategy_name() == "temporal_preference_test"

    def test_generate_pairs_returns_exactly_12(self):
        """Test that generate_pairs returns exactly 12 pairs."""
        pairs = self.strategy.generate_pairs(self.test_vector, n=12)
        assert len(pairs) == 12

    def test_generate_pairs_ignores_n_parameter(self):
        """Test that generate_pairs ignores n parameter and always returns 12."""
        # Should always return 12 pairs regardless of n parameter
        pairs_10 = self.strategy.generate_pairs(self.test_vector, n=10)
        pairs_15 = self.strategy.generate_pairs(self.test_vector, n=15)

        assert len(pairs_10) == 12
        assert len(pairs_15) == 12

    def test_sub_survey_1_structure(self):
        """Test Sub-Survey 1 (Simple Discounting) structure."""
        pairs = self.strategy.generate_pairs(self.test_vector, n=12)

        # Check pairs 1-4 (sub-survey 1)
        for i in range(4):
            pair = pairs[i]

            # Should have exactly 2 option keys
            option_keys = [k for k in pair.keys() if not k.startswith("instruction")]
            assert len(option_keys) == 2

            # Check key patterns
            assert "Simple Discounting - Ideal Option" in pair
            assert "Simple Discounting - Random Option" in pair

            # Check structure: Each option should be a single vector (not tuple of tuples)
            ideal_option = pair["Simple Discounting - Ideal Option"]
            random_option = pair["Simple Discounting - Random Option"]

            # Should be single vectors (tuples of 3 integers)
            assert isinstance(ideal_option, tuple) and len(ideal_option) == 3
            assert isinstance(random_option, tuple) and len(random_option) == 3

            # Ideal option should be the user's vector
            assert ideal_option == self.test_vector

            # Random option should be different from user's vector
            assert random_option != self.test_vector

            # All values should be Python integers, not numpy types
            assert all(isinstance(v, int) for v in ideal_option)
            assert all(isinstance(v, int) for v in random_option)

    def test_balanced_vectors_mathematical_correctness(self):
        """Test that balanced vectors B and C satisfy (B+C)/2 = user_vector."""
        pairs = self.strategy.generate_pairs(self.test_vector, n=12)

        # Test sub-surveys 2 and 3 structure and mathematical correctness
        for i in range(4, 8):  # Sub-survey 2
            pair = pairs[i]

            # Should have instruction context with fixed vector B
            assert "instruction_context" in pair
            assert "fixed_vector" in pair["instruction_context"]
            vector_b = pair["instruction_context"]["fixed_vector"]

            # Should have ideal and balanced options
            assert "Second-Year Choice - Ideal Option" in pair
            assert "Second-Year Choice - Balanced Option" in pair

            ideal_option = pair["Second-Year Choice - Ideal Option"]
            vector_c = pair["Second-Year Choice - Balanced Option"]

            # Ideal option should be user vector
            assert ideal_option == self.test_vector

            # Test mathematical correctness: (B + C) / 2 = user_vector
            for j in range(3):
                avg = (vector_b[j] + vector_c[j]) / 2
                assert abs(avg - self.test_vector[j]) < 0.01, (
                    f"Balance condition failed for sub-survey 2: "
                    f"({vector_b[j]} + {vector_c[j]}) / 2 = {avg}, "
                    f"expected {self.test_vector[j]}"
                )

        for i in range(8, 12):  # Sub-survey 3
            pair = pairs[i]

            # Should have instruction context with fixed vector B
            assert "instruction_context" in pair
            assert "fixed_vector" in pair["instruction_context"]
            vector_b = pair["instruction_context"]["fixed_vector"]

            # Should have ideal and balanced options
            assert "First-Year Choice - Ideal Option" in pair
            assert "First-Year Choice - Balanced Option" in pair

            ideal_option = pair["First-Year Choice - Ideal Option"]
            vector_c = pair["First-Year Choice - Balanced Option"]

            # Ideal option should be user vector
            assert ideal_option == self.test_vector

            # Test mathematical correctness: (B + C) / 2 = user_vector
            for j in range(3):
                avg = (vector_b[j] + vector_c[j]) / 2
                assert abs(avg - self.test_vector[j]) < 0.01, (
                    f"Balance condition failed for sub-survey 3: "
                    f"({vector_b[j]} + {vector_c[j]}) / 2 = {avg}, "
                    f"expected {self.test_vector[j]}"
                )

    def test_fallback_mechanism_for_extreme_vectors(self):
        """Test that extreme vectors either succeed or fail gracefully."""
        # Extreme vectors like (95, 5, 0) are mathematically constrained
        # Should either succeed completely or raise UnsuitableForStrategyError
        try:
            pairs = self.strategy.generate_pairs(self.extreme_vector, n=12)
            # If it succeeds, it must generate exactly 12 pairs
            assert len(pairs) == 12
        except UnsuitableForStrategyError:
            # This is acceptable for extreme vectors
            pass

    @patch("numpy.random.randint")
    def test_error_handling_when_generation_fails(self, mock_randint):
        """Test UnsuitableForStrategyError is raised when generation fails."""
        # Mock random generation to create scenarios that prevent valid pairs
        import numpy as np

        def mock_randint_func(*args, size=None, **kwargs):
            # Return zeros array with appropriate size
            if size is not None:
                return np.zeros(size, dtype=int)
            else:
                return np.array([0])

        mock_randint.side_effect = mock_randint_func

        with pytest.raises(
            UnsuitableForStrategyError, match="unique balanced vector pairs"
        ):
            self.strategy.generate_pairs(self.test_vector, n=12)

    def test_get_option_labels(self):
        """Test that get_option_labels returns expected labels."""
        labels = self.strategy.get_option_labels()
        assert labels == ("Option A", "Option B")

    def test_get_table_columns(self):
        """Test that get_table_columns returns correct column definitions."""
        columns = self.strategy.get_table_columns()

        expected_keys = {"sub1_ideal_y1", "sub2_ideal_y2", "sub3_ideal_y1"}
        assert set(columns.keys()) == expected_keys

        # Check column properties
        for key, col in columns.items():
            assert "name" in col
            assert "type" in col
            assert "highlight" in col
            assert col["type"] == "percentage"
            assert col["highlight"] is True

    def test_is_ranking_based(self):
        """Test that strategy correctly identifies as not ranking-based."""
        assert self.strategy.is_ranking_based() is False
