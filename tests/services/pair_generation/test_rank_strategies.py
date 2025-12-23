"""Test suite for concrete rank-based strategies."""

import pytest

from application.services.pair_generation.rank_strategies import (
    L1VsL2RankStrategy,
    L1VsLeontiefRankStrategy,
    L2VsLeontiefRankStrategy,
)


@pytest.fixture
def l1_leo_strategy():
    return L1VsLeontiefRankStrategy()


@pytest.fixture
def l1_l2_strategy():
    return L1VsL2RankStrategy()


@pytest.fixture
def l2_leo_strategy():
    return L2VsLeontiefRankStrategy()


class TestL1VsLeontiefRankStrategy:
    """Tests for the L1 vs Leontief concrete strategy."""

    def test_strategy_metadata(self, l1_leo_strategy):
        """Verify strategy metadata matches expectations."""
        # Dynamic name generation
        assert l1_leo_strategy.get_strategy_name() == "l1_vs_leontief_rank_comparison"
        labels = l1_leo_strategy.get_option_labels()
        assert "L1 (Rank)" in labels
        assert "Leontief (Rank)" in labels

    def test_table_columns(self, l1_leo_strategy):
        """Verify table columns match expectations for analysis."""
        columns = l1_leo_strategy.get_table_columns()
        assert "l1" in columns
        assert "leontief" in columns
        assert columns["l1"]["type"] == "percentage"

    def test_generate_pairs_integration(self, l1_leo_strategy):
        """Verify end-to-end pair generation with this strategy."""
        user_vector = (50, 30, 20)
        n = 3
        pairs = l1_leo_strategy.generate_pairs(user_vector, n=n, vector_size=3)

        assert len(pairs) == n
        for pair in pairs:
            # Check metadata
            assert "__metadata__" in pair
            assert pair["__metadata__"]["strategy"] == "max_min_rank"

            # Check descriptions match translated names
            descriptions = [k for k in pair.keys() if k != "__metadata__"]
            assert any("L1 Optimized Vector" in d for d in descriptions)
            assert any("Leontief Optimized Vector" in d for d in descriptions)

    def test_custom_grid_step(self):
        """Verify strategy respects custom grid step."""
        strategy = L1VsLeontiefRankStrategy(grid_step=10)
        assert strategy.grid_step == 10

        # Pool size for step 10, size 3 should be smaller than step 5
        # C(n+k-1, k-1) for n=10, k=3 is C(12, 2) = 66
        pool = strategy.generate_vector_pool(size=10, vector_size=3)
        assert len(pool) == 66


class TestL1VsL2RankStrategy:
    """Tests for the L1 vs L2 concrete strategy."""

    def test_strategy_metadata(self, l1_l2_strategy):
        """Verify strategy metadata matches expectations."""
        assert l1_l2_strategy.get_strategy_name() == "l1_vs_l2_rank_comparison"
        labels = l1_l2_strategy.get_option_labels()
        assert "L1 (Rank)" in labels
        assert "L2 (Rank)" in labels

    def test_table_columns(self, l1_l2_strategy):
        """Verify table columns match expectations."""
        columns = l1_l2_strategy.get_table_columns()
        assert "l1" in columns
        assert "l2" in columns

    def test_generate_pairs_integration(self, l1_l2_strategy):
        """Verify end-to-end pair generation."""
        user_vector = (50, 30, 20)
        n = 2
        pairs = l1_l2_strategy.generate_pairs(user_vector, n=n, vector_size=3)
        assert len(pairs) == n
        for pair in pairs:
            descriptions = [k for k in pair.keys() if k != "__metadata__"]
            assert any("L1 Optimized Vector" in d for d in descriptions)
            assert any("L2 Optimized Vector" in d for d in descriptions)


class TestL2VsLeontiefRankStrategy:
    """Tests for the L2 vs Leontief concrete strategy."""

    def test_strategy_metadata(self, l2_leo_strategy):
        """Verify strategy metadata matches expectations."""
        assert l2_leo_strategy.get_strategy_name() == "l2_vs_leontief_rank_comparison"
        labels = l2_leo_strategy.get_option_labels()
        assert "L2 (Rank)" in labels
        assert "Leontief (Rank)" in labels

    def test_table_columns(self, l2_leo_strategy):
        """Verify table columns match expectations."""
        columns = l2_leo_strategy.get_table_columns()
        assert "l2" in columns
        assert "leontief" in columns

    def test_generate_pairs_integration(self, l2_leo_strategy):
        """Verify end-to-end pair generation."""
        user_vector = (50, 30, 20)
        n = 2
        pairs = l2_leo_strategy.generate_pairs(user_vector, n=n, vector_size=3)
        assert len(pairs) == n
        for pair in pairs:
            descriptions = [k for k in pair.keys() if k != "__metadata__"]
            assert any("L2 Optimized Vector" in d for d in descriptions)
            assert any("Leontief Optimized Vector" in d for d in descriptions)
