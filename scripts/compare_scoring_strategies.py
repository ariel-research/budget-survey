"""
Compares three pair-scoring strategies for the GenericRankStrategy:
  - max_min:      score = min(gain_a, gain_b)
  - weighted_cc:  score = min(gain_a, gain_b) + λ * (max(gain_a, gain_b) - min(gain_a, gain_b))
  - harmonic_mean: score = 2 * gain_a * gain_b / (gain_a + gain_b)

For each test vector, the script reports:

JACCARD SIMILARITY (top-10 overlap)
  Measures whether two strategies pick the same 10 pairs to show users.
  Calculated as: |intersection| / |union| of the two top-10 sets.
  Range: 0.0 (no shared pairs) to 1.0 (identical top-10).
  This is the most practically important metric — it directly answers
  "would a user see different questions depending on which formula we use?"

SPEARMAN ρ (full ranking correlation)
  Measures whether two strategies agree on the ordering of ALL valid pairs,
  not just the top 10. Calculated by ranking each strategy's scores and
  computing the correlation between those rank lists.
  Range: -1.0 (reversed order) to 1.0 (identical order). In practice,
  values above 0.95 mean the strategies are interchangeable.
  This catches subtle divergence that Jaccard misses when the top-10 agree
  but the ordering below the cutoff differs.

VERDICT
  A one-line interpretation based on valid pair count and minimum Spearman ρ:
  ✓ AGREEMENT  — strategies are interchangeable for this vector
  ~ PARTIAL    — top-10 is identical but full ordering differs slightly
  ✗ DIVERGENCE — formula choice would change which pairs users see
  ⚠ DEGENERATE — too few valid pairs to draw reliable conclusions
"""

import numpy as np

from application.services.algorithms.math_utils import rankdata
from application.services.algorithms.utility_models import (
    L1UtilityModel,
    L2UtilityModel,
)
from application.services.pair_generation.generic_rank_strategy import (
    SCORING_HARMONIC_MEAN,
    SCORING_MAX_MIN,
    SCORING_WEIGHTED_CC,
    GenericRankStrategy,
    _compute_all_ranked_pairs,
)


def _spearman_rho(x: list, y: list) -> float:
    """
    Compute Spearman's rank correlation using Pearson correlation of ranks.
    """
    rx = rankdata(np.array(x))
    ry = rankdata(np.array(y))
    # If either ranking is constant, all pairs are tied — formulas trivially agree
    if np.std(rx) == 0 or np.std(ry) == 0:
        return 1.0
    return float(np.corrcoef(rx, ry)[0, 1])


def run_comparison(user_vector: tuple):
    vector_size = len(user_vector)
    k = 10

    # Common parameters
    params = {
        "utility_model_a_class": L1UtilityModel,
        "utility_model_b_class": L2UtilityModel,
        "grid_step": 5,
        "min_component": 10,
        "normalization_method": "ordinal",
    }

    strategies = [
        ("max_min", SCORING_MAX_MIN, 0.0),
        ("weighted_cc", SCORING_WEIGHTED_CC, 0.1),
        ("harmonic_mean", SCORING_HARMONIC_MEAN, 0.0),
    ]

    results = {}
    full_rankings = {}

    for name, method, lam in strategies:
        strategy = GenericRankStrategy(
            **params, scoring_method=method, scoring_lambda=lam
        )

        all_pairs = _compute_all_ranked_pairs(
            user_vector=user_vector,
            vector_size=vector_size,
            grid_step=strategy.grid_step,
            current_floor=strategy.min_component,
            utility_model_a_class=params["utility_model_a_class"],
            utility_model_b_class=params["utility_model_b_class"],
            normalization_method=strategy.normalization_method,
            strategy_name=strategy.get_strategy_name(),
            scoring_method=method,
            scoring_lambda=lam,
        )

        top_k_pairs = {frozenset((p[0], p[1])) for p in all_pairs[:k]}
        results[name] = top_k_pairs

        full_rankings[name] = {frozenset((p[0], p[1])): p[2] for p in all_pairs}

    assert (
        full_rankings["max_min"].keys()
        == full_rankings["weighted_cc"].keys()
        == full_rankings["harmonic_mean"].keys()
    ), "Scoring methods produced different valid pair sets — this should never happen"

    n_valid = len(full_rankings["max_min"])
    print(f"\nUser vector: {user_vector}")
    print(
        f"  Strategy: L1 vs L2  |  Valid discriminating pairs: {n_valid}  |  Pairs needed for survey: {k}"
    )

    if n_valid < 20:
        print(
            "  ⚠  Low pair count — top-k selection may reflect arbitrary "
            "tiebreaking rather than genuine formula divergence"
        )

    print(
        f"\nTop-{k} Jaccard similarity  (1.0 = identical pairs selected, 0.0 = no overlap):"
    )

    def get_jaccard(s1, s2):
        set1 = results[s1]
        set2 = results[s2]
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        return intersection / union if union > 0 else 1.0

    print(
        f"  max_min      vs weighted_cc:   {get_jaccard('max_min', 'weighted_cc'):.3f}"
    )
    print(
        f"  max_min      vs harmonic_mean: {get_jaccard('max_min', 'harmonic_mean'):.3f}"
    )
    print(
        f"  weighted_cc  vs harmonic_mean: {get_jaccard('weighted_cc', 'harmonic_mean'):.3f}"
    )

    print(
        "\nSpearman ρ — full ranking correlation  (1.0 = identical ordering, 0.95+ = effectively equivalent):"
    )
    all_valid_pairs = list(full_rankings["max_min"].keys())

    def get_spearman(n1, n2):
        scores1 = [full_rankings[n1][p] for p in all_valid_pairs]
        scores2 = [full_rankings[n2][p] for p in all_valid_pairs]
        return _spearman_rho(scores1, scores2)

    s_m_w = get_spearman("max_min", "weighted_cc")
    s_m_h = get_spearman("max_min", "harmonic_mean")
    s_w_h = get_spearman("weighted_cc", "harmonic_mean")

    print(f"  max_min vs weighted_cc:   {s_m_w:.2f}")
    print(f"  max_min vs harmonic_mean: {s_m_h:.2f}")
    print(f"  weighted_cc vs harmonic_mean: {s_w_h:.2f}")

    spearman_values = [s_m_w, s_m_h, s_w_h]
    min_spearman = min(spearman_values)

    if n_valid < 20:
        verdict = "⚠  DEGENERATE: too few valid pairs — conclusions unreliable"
    elif min_spearman >= 0.95:
        verdict = "✓  AGREEMENT: all formulas effectively equivalent for this vector"
    elif min_spearman >= 0.80:
        verdict = (
            "~  PARTIAL: formulas agree on top pairs, minor divergence in full ranking"
        )
    else:
        verdict = "✗  DIVERGENCE: formula choice meaningfully affects pair selection"

    print(f"\nVerdict: {verdict}\n")
    print("-" * 60)


if __name__ == "__main__":
    # Test vectors are selected from real production data (unsuitable_for_strategy=0).
    # For L1 vs L2 specifically, balanced vectors (e.g. [40,30,30]) are structurally
    # unsuitable — the two models agree too strongly in that region to generate
    # enough discriminating pairs. Only vectors with a clearly dominant issue work.
    test_vectors = [
        # --- 3D vectors ---
        # Moderate concentration — most frequent suitable 3D vector
        (50, 25, 25),
        # High single-issue concentration — models most likely to diverge here
        (60, 20, 20),
        # Very high concentration — tests near-extreme simplex behavior
        (70, 15, 15),
        # --- 4D vectors ---
        # most frequent suitable 4D vector
        (25, 25, 25, 25),
        # --- 5D vectors ---
        # most frequent suitable 5D vector
        (20, 20, 20, 20, 20),
    ]
    for vec in test_vectors:
        run_comparison(vec)
