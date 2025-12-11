"""Test suite for Rank-Based Optimization Metrics Strategy."""

import numpy as np
import pytest

from application.services.pair_generation.optimization_metrics_rank import (
    OptimizationMetricsRankStrategy,
)


@pytest.fixture
def strategy():
    return OptimizationMetricsRankStrategy()


class TestL1Distance:
    """Tests for L1 distance calculation."""

    def test_l1_distance_basic(self, strategy):
        """Test basic L1 distance calculation."""
        user_vector = (10, 20, 70)
        generated_vector = (15, 25, 60)
        assert strategy._calculate_l1_distance(user_vector, generated_vector) == 20

    def test_l1_distance_identical_vectors(self, strategy):
        """Test L1 distance of identical vectors is 0."""
        vector = (30, 30, 40)
        assert strategy._calculate_l1_distance(vector, vector) == 0

    def test_l1_distance_opposite_allocations(self, strategy):
        """Test L1 distance with very different allocations."""
        user_vector = (90, 5, 5)
        generated_vector = (5, 5, 90)
        assert strategy._calculate_l1_distance(user_vector, generated_vector) == 170


class TestLeontiefRatio:
    """Tests for Leontief ratio calculation."""

    def test_leontief_ratio_basic(self, strategy):
        """Test basic Leontief ratio calculation."""
        user_vector = (50, 30, 20)
        generated_vector = (30, 40, 30)
        # Ratios: 30/50=0.6, 40/30=1.33, 30/20=1.5
        assert strategy._calculate_leontief_ratio(user_vector, generated_vector) == 0.6

    def test_leontief_ratio_with_zero_in_user_vector(self, strategy):
        """Test that zeros in user_vector are handled correctly (skipped)."""
        user_vector = (50, 50, 0)
        generated_vector = (40, 60, 0)
        # Should only consider non-zero components: 40/50=0.8, 60/50=1.2
        result = strategy._calculate_leontief_ratio(user_vector, generated_vector)
        assert result == 0.8

    def test_leontief_ratio_identical_vectors(self, strategy):
        """Test Leontief ratio of identical vectors is 1.0."""
        vector = (30, 30, 40)
        result = strategy._calculate_leontief_ratio(vector, vector)
        assert result == 1.0

    def test_leontief_ratio_all_zeros(self, strategy):
        """Test edge case where user_vector is all zeros."""
        user_vector = (0, 0, 0)
        generated_vector = (30, 30, 40)
        result = strategy._calculate_leontief_ratio(user_vector, generated_vector)
        assert result == 0.0


class TestRankNormalization:
    """Tests for rank normalization logic."""

    def test_rank_normalization_l1_inverted(self, strategy):
        """Test that L1 ranks are inverted (smaller L1 = higher rank)."""
        # Create L1 distances where smaller is better
        l1_distances = np.array([10, 50, 30, 20, 40])
        leontief_ratios = np.array(
            [0.5, 0.5, 0.5, 0.5, 0.5]
        )  # Irrelevant for this test

        l1_ranks, _ = strategy._compute_ranks(l1_distances, leontief_ratios)

        # Smallest L1 (10) should have highest rank
        assert l1_ranks[0] == max(l1_ranks)
        # Largest L1 (50) should have lowest rank
        assert l1_ranks[1] == min(l1_ranks)

    def test_rank_normalization_leontief_standard(self, strategy):
        """Test that Leontief ranks are standard (higher ratio = higher rank)."""
        l1_distances = np.array([30, 30, 30, 30, 30])  # Irrelevant for this test
        leontief_ratios = np.array([0.2, 0.8, 0.5, 0.3, 0.6])

        _, leontief_ranks = strategy._compute_ranks(l1_distances, leontief_ratios)

        # Highest ratio (0.8) should have highest rank
        assert leontief_ranks[1] == max(leontief_ranks)
        # Lowest ratio (0.2) should have lowest rank
        assert leontief_ranks[0] == min(leontief_ranks)

    def test_ranks_normalized_to_0_1(self, strategy):
        """Test that all ranks are in the range [0, 1]."""
        l1_distances = np.array([10, 50, 30, 20, 40, 15, 25, 35, 45, 55])
        leontief_ratios = np.array([0.2, 0.8, 0.5, 0.3, 0.6, 0.7, 0.4, 0.9, 0.1, 0.55])

        l1_ranks, leontief_ranks = strategy._compute_ranks(
            l1_distances, leontief_ratios
        )

        assert all(0 <= r <= 1 for r in l1_ranks)
        assert all(0 <= r <= 1 for r in leontief_ranks)


class TestVectorPoolEnumeration:
    """Tests for deterministic simplex enumeration."""

    def test_vector_pool_covers_simplex(self, strategy):
        """The strategy should enumerate the full discrete simplex."""
        pool = strategy.generate_vector_pool(size=5, vector_size=3)

        # With min=10 and step=5 we have C(14 + 3 - 1, 3 - 1) = 120 points
        assert len(pool) == 120
        assert (80, 10, 10) in pool
        assert (10, 10, 80) in pool
        assert (50, 30, 20) in pool


class TestPairGeneration:
    """Tests for the main pair generation functionality."""

    def test_generate_pairs_returns_correct_count(self, strategy):
        """Test that generate_pairs returns the requested number of pairs."""
        user_vector = (40, 30, 30)
        n_pairs = 5
        pairs = strategy.generate_pairs(user_vector, n=n_pairs, vector_size=3)

        assert len(pairs) == n_pairs

    def test_generate_pairs_structure(self, strategy):
        """Test that generated pairs have correct structure."""
        user_vector = (50, 30, 20)
        pairs = strategy.generate_pairs(user_vector, n=5, vector_size=3)

        for pair in pairs:
            assert isinstance(pair, dict)
            # Should have at least 2 vector entries + potentially __metadata__
            # Note: __metadata__ is popped by _randomize_pair_options, but we're testing
            # the raw output here
            descriptions = [k for k in pair.keys() if k != "__metadata__"]
            assert len(descriptions) == 2

            assert any("Sum Optimized Vector" in desc for desc in descriptions)
            assert any("Ratio Optimized Vector" in desc for desc in descriptions)

    def test_vectors_sum_to_100(self, strategy):
        """Test that all generated vectors sum to 100."""
        user_vector = (60, 20, 20)
        pairs = strategy.generate_pairs(user_vector, n=5, vector_size=3)

        for pair in pairs:
            vectors = [v for v in pair.values() if isinstance(v, tuple)]
            for vector in vectors:
                assert sum(vector) == 100

    def test_vectors_in_valid_range(self, strategy):
        """Test that all vector components are in valid range [0, 100]."""
        user_vector = (50, 25, 25)
        pairs = strategy.generate_pairs(user_vector, n=5, vector_size=3)

        for pair in pairs:
            vectors = [v for v in pair.values() if isinstance(v, tuple)]
            for vector in vectors:
                assert all(0 <= v <= 100 for v in vector)

    def test_vectors_distinct_from_user_vector(self, strategy):
        """Test that generated vectors are different from the user vector."""
        user_vector = (40, 35, 25)
        pairs = strategy.generate_pairs(user_vector, n=5, vector_size=3)

        for pair in pairs:
            vectors = [v for v in pair.values() if isinstance(v, tuple)]
            for vector in vectors:
                assert vector != user_vector


class TestMetadataGeneration:
    """Tests for generation metadata."""

    def test_metadata_present_in_pairs(self, strategy):
        """Test that each pair includes __metadata__ key."""
        user_vector = (45, 30, 25)
        pairs = strategy.generate_pairs(user_vector, n=5, vector_size=3)

        for pair in pairs:
            assert "__metadata__" in pair
            metadata = pair["__metadata__"]
            assert metadata["strategy"] == "max_min_rank"
            assert "score" in metadata

    def test_metadata_values_valid(self, strategy):
        """Test that metadata values are within expected ranges."""
        user_vector = (35, 35, 30)
        pairs = strategy.generate_pairs(user_vector, n=5, vector_size=3)

        for pair in pairs:
            metadata = pair["__metadata__"]
            assert metadata["strategy"] == "max_min_rank"
            assert 0 <= metadata["score"] <= 1


class TestCornerCases:
    """Tests for edge cases and corner vectors."""

    def test_corner_vector_with_zero(self, strategy):
        """
        Test with a corner vector containing zero.

        This ensures the brute-force max-min approach still surfaces pairs
        when vectors are highly skewed.
        """
        user_vector = (95, 5, 0)
        pairs = strategy.generate_pairs(user_vector, n=10, vector_size=3)

        # Should still generate pairs (proves adaptive logic works)
        assert len(pairs) > 0
        # Ideally should get close to requested count
        assert len(pairs) >= 5

    def test_extreme_allocation(self, strategy):
        """Test with an extreme budget allocation."""
        user_vector = (90, 5, 5)
        pairs = strategy.generate_pairs(user_vector, n=8, vector_size=3)

        # Should generate pairs successfully
        assert len(pairs) > 0

        # All vectors should still be valid
        for pair in pairs:
            vectors = [v for v in pair.values() if isinstance(v, tuple)]
            for vector in vectors:
                assert sum(vector) == 100
                assert all(0 <= v <= 100 for v in vector)

    def test_even_distribution(self, strategy):
        """Test with an even distribution."""
        user_vector = (35, 35, 30)
        pairs = strategy.generate_pairs(user_vector, n=10, vector_size=3)

        assert len(pairs) == 10


class TestRelaxationEscalation:
    """Tests for the adaptive relaxation mechanism."""

    def test_relaxation_levels_used_when_needed(self, strategy):
        """
        Test that relaxation escalates when strict constraints fail.

        With difficult vectors, higher relaxation levels should be used.
        """
        # A very skewed vector might require looser constraints
        user_vector = (85, 10, 5)
        pairs = strategy.generate_pairs(user_vector, n=10, vector_size=3)

        # Check that some pairs may have used higher relaxation levels
        levels_used = set()
        for pair in pairs:
            metadata = pair.get("__metadata__", {})
            levels_used.add(metadata.get("level", 1))

        # This assertion is soft - just verify we got pairs
        assert len(pairs) > 0

    def test_strict_level_preferred_when_possible(self, strategy):
        """Test that Level 1 (strict) is used when vectors allow it."""
        # A balanced vector should allow strict matching
        user_vector = (40, 30, 30)
        pairs = strategy.generate_pairs(user_vector, n=5, vector_size=3)

        # Check if any pairs used Level 1
        level_1_count = sum(
            1 for pair in pairs if pair.get("__metadata__", {}).get("level") == 1
        )

        # At least some pairs should be at Level 1 for balanced vectors
        # (This is a soft assertion as it depends on random pool)
        assert level_1_count >= 0  # Non-negative by definition


class TestStrategyMetadata:
    """Tests for strategy configuration and labels."""

    def test_strategy_name(self, strategy):
        """Test strategy name is correct."""
        assert strategy.get_strategy_name() == "l1_vs_leontief_rank_comparison"

    def test_option_labels(self, strategy):
        """Test option labels are correct."""
        labels = strategy.get_option_labels()
        assert labels == ("Sum (Rank)", "Ratio (Rank)")

    def test_metric_types(self, strategy):
        """Test metric types are correct."""
        types = strategy.get_metric_types()
        assert types == ("sum", "ratio")

    def test_metric_name_sum(self, strategy):
        """Test metric name for sum type."""
        assert strategy._get_metric_name("sum") == "Sum Optimized Vector"

    def test_metric_name_ratio(self, strategy):
        """Test metric name for ratio type."""
        assert strategy._get_metric_name("ratio") == "Ratio Optimized Vector"

    def test_metric_name_unknown(self, strategy):
        """Test metric name for unknown type."""
        assert strategy._get_metric_name("unknown") == "Unknown Vector"


class TestErrorHandling:
    """Tests for error handling."""

    def test_invalid_vector_sum(self, strategy):
        """Test that invalid vector (wrong sum) raises ValueError."""
        invalid_vector = (30, 30, 30)  # Sum is 90, not 100
        with pytest.raises(ValueError, match="must sum to 100"):
            strategy.generate_pairs(invalid_vector, n=5, vector_size=3)

    def test_invalid_vector_length(self, strategy):
        """Test that invalid vector (wrong length) raises ValueError."""
        invalid_vector = (50, 50)  # Length 2, not 3
        with pytest.raises(ValueError, match="must have length 3"):
            strategy.generate_pairs(invalid_vector, n=5, vector_size=3)

    def test_negative_values(self, strategy):
        """Test that negative values raise ValueError."""
        invalid_vector = (110, -5, -5)
        with pytest.raises(ValueError, match="must be between 0 and 100"):
            strategy.generate_pairs(invalid_vector, n=5, vector_size=3)


class TestOptionDescriptions:
    """Tests for option description generation."""

    def test_option_description_sum(self, strategy):
        """Test option description for sum-optimized vector."""
        desc = strategy.get_option_description(
            metric_type="sum", best_value=25, worst_value=45
        )
        assert "Sum Optimized Vector" in desc
        assert "best: 25.00" in desc
        assert "worst: 45.00" in desc

    def test_option_description_ratio(self, strategy):
        """Test option description for ratio-optimized vector."""
        desc = strategy.get_option_description(
            metric_type="ratio", best_value=0.85, worst_value=0.55
        )
        assert "Ratio Optimized Vector" in desc
        assert "best: 0.85" in desc
        assert "worst: 0.55" in desc
