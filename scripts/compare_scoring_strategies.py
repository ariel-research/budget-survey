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

        # We need all valid pairs to compute Spearman rho
        # We can call the cached function directly to get all pairs
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

        # Store top-k pairs (only the vector indices as unique identifier for the pair)
        # frozenset is safe here because _compute_all_ranked_pairs always assigns idx_a
        # as the vector better on model A, so the same logical pair always maps to the
        # same frozenset across all scoring strategies.
        top_k_pairs = {frozenset((p[0], p[1])) for p in all_pairs[:k]}
        results[name] = top_k_pairs

        # For Spearman, we need a consistent set of pairs across all strategies.
        # But different strategies might have different "valid" pairs?
        # Actually, the set of valid pairs (gains_a > 0 and gains_b > 0) is the same
        # for all scoring methods because it's determined before the scoring function.
        # Let's create a map of (idx_a, idx_b) -> score
        full_rankings[name] = {(frozenset((p[0], p[1]))): p[2] for p in all_pairs}

    # Verify that all scoring methods produced the same valid pair sets
    assert (
        full_rankings["max_min"].keys()
        == full_rankings["weighted_cc"].keys()
        == full_rankings["harmonic_mean"].keys()
    ), "Scoring methods produced different valid pair sets — this should never happen"

    # Print results
    print(f"\nUser vector: {user_vector}")

    n_valid = len(full_rankings["max_min"])
    print(f"Valid discriminating pairs found: {n_valid}")
    if n_valid < 20:
        print(
            "  ⚠  Low pair count — top-10 selection may reflect arbitrary "
            "tiebreaking rather than genuine formula divergence"
        )

    # 1. Jaccard Similarity List
    print("\nTop-10 Jaccard similarity:")

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

    # 2. Spearman Correlation
    print("\nSpearman ρ (full ranking):")
    # To compute spearman, we need the scores of all pairs that are valid in ANY strategy.
    # Since the validity criteria (gains_a > 0 and gains_b > 0) is the same,
    # the set of pairs should be identical.
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

    # 3. Verdict
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
    print("-" * 60)  # separator between vectors


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
