"""Test suite for concrete rank-based strategies."""

import pytest

from application.services.pair_generation.rank_strategies import (
    KLVsAntiLeontiefRankStrategy,
    KLVsL1RankStrategy,
    KLVsL2RankStrategy,
    L1VsL2RankStrategy,
    L1VsLeontiefRankStrategy,
    L2VsLeontiefRankStrategy,
    LeontiefVsAntiLeontiefRankStrategy,
    LeontiefVsKLRankStrategy,
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


@pytest.fixture
def leontief_anti_leo_strategy():
    return LeontiefVsAntiLeontiefRankStrategy()


@pytest.fixture
def leontief_kl_strategy():
    return LeontiefVsKLRankStrategy()


@pytest.fixture
def kl_anti_leo_strategy():
    return KLVsAntiLeontiefRankStrategy()


@pytest.fixture
def kl_l1_strategy():
    return KLVsL1RankStrategy()


@pytest.fixture
def kl_l2_strategy():
    return KLVsL2RankStrategy()


class TestL1VsLeontiefRankStrategy:
    """Tests for the L1 vs Leontief concrete strategy."""

    def test_strategy_metadata(self, l1_leo_strategy):
        """Verify strategy metadata matches expectations."""
        # Dynamic name generation
        assert l1_leo_strategy.get_strategy_name() == "l1_vs_leontief_rank_comparison"
        labels = l1_leo_strategy.get_option_labels()
        assert "l1 (Rank)" in labels
        assert "leontief (Rank)" in labels

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
            descriptions = [k for k in pair.keys() if k != "__metadata__"]
            assert any("l1:" in d for d in descriptions)
            assert any("leontief:" in d for d in descriptions)

    def test_custom_grid_step(self):
        """Verify strategy respects custom grid step."""
        strategy = L1VsLeontiefRankStrategy(grid_step=10)
        assert strategy.grid_step == 10

        # Pool size for step 10, size 3, min_component=10
        # Side length is 100.
        # Min component 10 removes 3*10 = 30 from total budget?
        # Let's verify calculation.
        # Simplex logic: x1 + x2 + x3 = 100, xi >= 10, step 10.
        # Let yi = (xi - 10)/10.
        # sum(10*yi + 10) = 100 => 10*sum(yi) + 30 = 100 => 10*sum(yi) = 70 => sum(yi) = 7.
        # Stars and bars: C(n + k - 1, k - 1) -> C(7 + 3 - 1, 3 - 1) = C(9, 2)
        # 9 * 8 / 2 = 36.
        pool = strategy.generate_vector_pool(size=10, vector_size=3)
        assert len(pool) == 36


class TestL1VsL2RankStrategy:
    """Tests for the L1 vs L2 concrete strategy."""

    def test_strategy_metadata(self, l1_l2_strategy):
        """Verify strategy metadata matches expectations."""
        assert l1_l2_strategy.get_strategy_name() == "l1_vs_l2_rank_comparison"
        labels = l1_l2_strategy.get_option_labels()
        assert "l1 (Rank)" in labels
        assert "l2 (Rank)" in labels

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
            assert any("l1:" in d for d in descriptions)
            assert any("l2:" in d for d in descriptions)


class TestL2VsLeontiefRankStrategy:
    """Tests for the L2 vs Leontief concrete strategy."""

    def test_strategy_metadata(self, l2_leo_strategy):
        """Verify strategy metadata matches expectations."""
        assert l2_leo_strategy.get_strategy_name() == "l2_vs_leontief_rank_comparison"
        labels = l2_leo_strategy.get_option_labels()
        assert "l2 (Rank)" in labels
        assert "leontief (Rank)" in labels

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
            assert any("l2:" in d for d in descriptions)
            assert any("leontief:" in d for d in descriptions)


class TestLeontiefVsAntiLeontiefRankStrategy:
    """Tests for the Leontief vs Anti-Leontief strategy."""

    def test_generate_pairs_integration(self, leontief_anti_leo_strategy):
        """Verify end-to-end pair generation."""
        user_vector = (50, 30, 20)
        n = 2
        pairs = leontief_anti_leo_strategy.generate_pairs(
            user_vector, n=n, vector_size=3
        )
        assert len(pairs) == n
        for pair in pairs:
            descriptions = [k for k in pair.keys() if k != "__metadata__"]
            assert any("leontief:" in d for d in descriptions)
            assert any("anti_leontief:" in d for d in descriptions)


class TestLeontiefVsKLRankStrategy:
    """Tests for the Leontief vs KL strategy."""

    def test_generate_pairs_integration(self, leontief_kl_strategy):
        """Verify end-to-end pair generation."""
        user_vector = (50, 30, 20)
        n = 2
        pairs = leontief_kl_strategy.generate_pairs(user_vector, n=n, vector_size=3)
        assert len(pairs) == n
        for pair in pairs:
            descriptions = [k for k in pair.keys() if k != "__metadata__"]
            assert any("leontief:" in d for d in descriptions)
            assert any("kl:" in d for d in descriptions)


class TestKLVsAntiLeontiefRankStrategy:
    """Tests for the KL vs Anti-Leontief strategy."""

    def test_generate_pairs_integration(self, kl_anti_leo_strategy):
        """Verify end-to-end pair generation."""
        user_vector = (50, 30, 20)
        n = 2
        pairs = kl_anti_leo_strategy.generate_pairs(user_vector, n=n, vector_size=3)
        assert len(pairs) == n
        for pair in pairs:
            descriptions = [k for k in pair.keys() if k != "__metadata__"]
            assert any("kl:" in d for d in descriptions)
            assert any("anti_leontief:" in d for d in descriptions)


class TestKLVsL1RankStrategy:
    """Tests for the KL vs L1 strategy."""

    def test_generate_pairs_integration(self, kl_l1_strategy):
        """Verify end-to-end pair generation."""
        user_vector = (50, 30, 20)
        n = 2
        pairs = kl_l1_strategy.generate_pairs(user_vector, n=n, vector_size=3)
        assert len(pairs) == n
        for pair in pairs:
            descriptions = [k for k in pair.keys() if k != "__metadata__"]
            assert any("kl:" in d for d in descriptions)
            assert any("l1:" in d for d in descriptions)


class TestKLVsL2RankStrategy:
    """Tests for the KL vs L2 strategy."""

    def test_generate_pairs_integration(self, kl_l2_strategy):
        """Verify end-to-end pair generation."""
        user_vector = (50, 30, 20)
        n = 2
        pairs = kl_l2_strategy.generate_pairs(user_vector, n=n, vector_size=3)
        assert len(pairs) == n
        for pair in pairs:
            descriptions = [k for k in pair.keys() if k != "__metadata__"]
            assert any("kl:" in d for d in descriptions)
            assert any("l2:" in d for d in descriptions)
