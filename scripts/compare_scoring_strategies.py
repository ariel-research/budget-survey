"""
Compares three pair-scoring strategies for the GenericRankStrategy:
  - max_min:       score = min(gain_a, gain_b)
  - weighted_cc:   score = min(gain_a, gain_b) + λ * (max(gain_a, gain_b) - min(gain_a, gain_b))
  - harmonic_mean: score = 2 * gain_a * gain_b / (gain_a + gain_b)

For each test vector, the script reports:

VALID DISCRIMINATING PAIRS
  A pair of budget vectors (A, B) is valid for discrimination if the two utility
  models being compared disagree about which vector is better — model A prefers
  vector A, and model B prefers vector B. Only these pairs are useful in a survey:
  if both models agreed, the user's choice would reveal nothing about their
  underlying utility function. The count reported here is the total number of such
  pairs found in the full simplex grid for this user vector.

JACCARD SIMILARITY (top-k overlap)
  Measures whether two strategies pick the same k pairs to show users.
  Calculated as: |intersection| / |union| of the two top-k sets.
  Range: 0.0 (no shared pairs) to 1.0 (identical top-k).
  This is the most practically important metric — it directly answers:
  "would a user see different questions depending on which formula we use?"

SPEARMAN ρ (full ranking correlation)
  Measures whether two strategies agree on the ordering of ALL valid pairs,
  not just the top k. Calculated by ranking each strategy's scores and
  computing the correlation between those rank lists.
  Range: -1.0 (reversed order) to 1.0 (identical order). In practice,
  values above 0.95 mean the strategies are interchangeable.
  This catches subtle divergence that Jaccard misses when the top-k agree
  but the ordering below the cutoff differs.

VERDICT
  A one-line interpretation. Jaccard takes priority since it reflects what
  users actually experience. Spearman distinguishes AGREEMENT from PARTIAL
  when Jaccard is already acceptable.
  ✓ AGREEMENT  — top-k identical AND full ordering equivalent (Spearman ≥ 0.95)
  ~ PARTIAL    — top-k identical but full ordering differs slightly
  ✗ DIVERGENCE — formula choice would change which pairs users see
  ⚠ DEGENERATE — too few valid pairs to draw reliable conclusions
  Note: DIVERGENCE with Spearman ≥ 0.97 and very high pair counts (>50k)
  likely indicates a tiebreaking artifact rather than genuine disagreement.

NOTE ON HIGH PAIR COUNTS
  When the valid pair count exceeds ~50,000, Jaccard divergence often reflects
  arbitrary tiebreaking at the top of a very dense score distribution, not
  genuine formula disagreement. In these cases, all formulas agree the same
  broad cluster of pairs is best — but minor score differences determine the
  exact top-10 cutoff. The Spearman ρ is the more reliable signal in this regime.
"""

import numpy as np

from application.services.algorithms.math_utils import rankdata
from application.services.algorithms.utility_models import (
    KLUtilityModel,
    L1UtilityModel,
    L2UtilityModel,
    LeontiefUtilityModel,
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

    Spearman ρ measures whether two lists agree on the *relative ordering*
    of items, regardless of the absolute score values. It works by converting
    both score lists into rank lists and then computing their Pearson correlation.

    Returns 1.0 if either ranking is constant (all pairs tied — trivial agreement).
    """
    rx = rankdata(np.array(x))
    ry = rankdata(np.array(y))
    # If either ranking is constant, all pairs are tied — formulas trivially agree
    if np.std(rx) == 0 or np.std(ry) == 0:
        return 1.0
    return float(np.corrcoef(rx, ry)[0, 1])


def run_comparison(
    user_vector: tuple,
    utility_model_a_class,
    utility_model_b_class,
    model_pair_label: str,
    min_component: int = 0,
):
    """
    Run the three-way scoring strategy comparison for a single user vector and model pair.
    Prints valid pair count, Jaccard similarity, Spearman ρ, and a verdict to stdout.
    """
    vector_size = len(user_vector)
    k = 10

    params = {
        "utility_model_a_class": utility_model_a_class,
        "utility_model_b_class": utility_model_b_class,
        "grid_step": 5,
        "min_component": min_component,
        "normalization_method": "ordinal",
    }

    strategies = [
        ("max_min", SCORING_MAX_MIN, 0.0),
        ("weighted_cc", SCORING_WEIGHTED_CC, 0.1),
        (
            "harmonic_mean",
            SCORING_HARMONIC_MEAN,
            0.0,
        ),  # lambda ignored for harmonic mean
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

        # frozenset is used instead of a plain tuple so that pair (i, j) and pair (j, i)
        # map to the same key regardless of which index comes first.
        # _compute_all_ranked_pairs always returns idx_a as the winner on model A,
        # so in practice the order is consistent — but frozenset makes this robust
        # to any future change in that internal ordering guarantee.
        results[name] = {frozenset((p[0], p[1])) for p in all_pairs[:k]}
        full_rankings[name] = {frozenset((p[0], p[1])): p[2] for p in all_pairs}

    # Sanity check: all strategies must evaluate the same set of valid pairs.
    # The validity criterion (model A prefers A, model B prefers B) is determined
    # before scoring, so it must be identical across all three formulas.
    assert (
        full_rankings["max_min"].keys()
        == full_rankings["weighted_cc"].keys()
        == full_rankings["harmonic_mean"].keys()
    ), "Scoring methods produced different valid pair sets — this should never happen"

    n_valid = len(full_rankings["max_min"])

    # --- Output ---

    print(f"\nUser vector: {user_vector}")
    print(
        f"  Strategy: {model_pair_label}  |  "
        f"Valid discriminating pairs: {n_valid} (pairs where the two models prefer opposite vectors)  |  "
        f"Pairs needed for survey: {k}"
    )

    if n_valid < 20:
        print(
            "  ⚠  Low pair count — top-k selection may reflect arbitrary "
            "tiebreaking rather than genuine formula divergence"
        )

    # --- Jaccard Similarity ---

    def get_jaccard(s1, s2):
        set1 = results[s1]
        set2 = results[s2]
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        return intersection / union if union > 0 else 1.0

    j_m_w = get_jaccard("max_min", "weighted_cc")
    j_m_h = get_jaccard("max_min", "harmonic_mean")
    j_w_h = get_jaccard("weighted_cc", "harmonic_mean")

    print(
        f"\nTop-{k} Jaccard similarity  (1.0 = identical pairs selected, 0.0 = no overlap):"
    )
    print(f"  max_min      vs weighted_cc:   {j_m_w:.3f}")
    print(f"  max_min      vs harmonic_mean: {j_m_h:.3f}")
    print(f"  weighted_cc  vs harmonic_mean: {j_w_h:.3f}")

    # --- Spearman ρ ---

    all_valid_pairs = list(full_rankings["max_min"].keys())

    def get_spearman(n1, n2):
        scores1 = [full_rankings[n1][p] for p in all_valid_pairs]
        scores2 = [full_rankings[n2][p] for p in all_valid_pairs]
        return _spearman_rho(scores1, scores2)

    s_m_w = get_spearman("max_min", "weighted_cc")
    s_m_h = get_spearman("max_min", "harmonic_mean")
    s_w_h = get_spearman("weighted_cc", "harmonic_mean")

    print(
        "\nSpearman ρ — full ranking correlation  (1.0 = identical ordering, 0.95+ = effectively equivalent):"
    )
    print(f"  max_min      vs weighted_cc:   {s_m_w:.2f}")
    print(f"  max_min      vs harmonic_mean: {s_m_h:.2f}")
    print(f"  weighted_cc  vs harmonic_mean: {s_w_h:.2f}")

    # --- Verdict ---
    # Jaccard is evaluated first because it reflects what users actually experience
    # (do they see the same pairs?). Spearman is a secondary signal that catches
    # full-ranking divergence even when the top-k happen to be identical.

    min_jaccard = min(j_m_w, j_m_h, j_w_h)
    min_spearman = min(s_m_w, s_m_h, s_w_h)

    # --- Detail Display for Divergence ---

    if min_jaccard < 0.8 and n_valid >= 20:
        print(
            f"\n  Low Jaccard detected — top-{min(5, k)} pairs per formula (score reflects gain balance):"
        )
        print(
            "  max_min score = min(gain_a, gain_b), so low score = lopsided pair, high score = balanced pair\n"
        )

        for name in ["max_min", "weighted_cc", "harmonic_mean"]:
            sorted_by_score = sorted(
                full_rankings[name].items(), key=lambda x: x[1], reverse=True
            )[: min(5, k)]
            scores_str = ",  ".join(f"{score:.3f}" for _, score in sorted_by_score)
            # Also show the max_min score for the same pairs (reveals lopsidedness)
            maxmin_scores_str = ",  ".join(
                f"{full_rankings['max_min'].get(pair, 0.0):.3f}"
                for pair, _ in sorted_by_score
            )
            print(f"  {name:<16} scores:         {scores_str}")
            print(f"  {'':16} maxmin scores:  {maxmin_scores_str}")
            print()

    if n_valid < 20:
        verdict = "⚠  DEGENERATE: too few valid pairs — conclusions unreliable"
    elif min_jaccard < 0.8:
        verdict = "✗  DIVERGENCE: formula choice would change which pairs users see"
    elif min_spearman >= 0.95:
        verdict = "✓  AGREEMENT: all formulas effectively equivalent for this vector"
    else:
        verdict = "~  PARTIAL: same pairs selected, minor divergence in full ranking"

    print(f"\nVerdict: {verdict}\n")
    print("-" * 60)


if __name__ == "__main__":
    # Test vectors confirmed suitable from production data (unsuitable_for_strategy=0).
    # Balanced 3D vectors (e.g. [40,30,30]) are excluded — the compared utility models
    # agree too strongly in that region to generate enough discriminating pairs.
    test_vectors = [
        # --- 3D vectors ---
        # Symmetric concentration: most frequent suitable 3D vector in production
        (50, 25, 25),
        # Higher symmetric concentration
        (60, 20, 20),
        # Near-extreme symmetric concentration
        (70, 15, 15),
        # Asymmetric 3D — tests whether formula behavior differs
        # when issues have genuinely different weights (not just one dominant + two equal).
        # Note: suitability not verified against production data — may produce low pair counts
        # for some model pairs.
        (50, 30, 20),
        # --- 4D vectors ---
        # Symmetric — most frequent suitable 4D vector in production
        (25, 25, 25, 25),
        # Asymmetric — tests whether 4D agreement holds beyond the symmetric case
        (40, 30, 20, 10),
        # --- 5D vectors ---
        # Uniform 5D — included for completeness, but results are dominated
        # by tiebreaking artifacts at this scale (millions of valid pairs)
        (20, 20, 20, 20, 20),
    ]

    # (model_a_class, model_b_class, label, min_component)
    model_pairs = [
        (L1UtilityModel, L2UtilityModel, "L1 vs L2", 0),
        (L1UtilityModel, LeontiefUtilityModel, "L1 vs Leontief", 10),
        (L2UtilityModel, LeontiefUtilityModel, "L2 vs Leontief", 10),
        (KLUtilityModel, L1UtilityModel, "KL vs L1", 10),
        (KLUtilityModel, L2UtilityModel, "KL vs L2", 10),
        (LeontiefUtilityModel, KLUtilityModel, "Leontief vs KL", 10),
    ]

    for model_a, model_b, label, min_comp in model_pairs:
        print(f"\n{'='*60}")
        print(f"  SCORING STRATEGY COMPARISON: {label}")
        print(f"{'='*60}")
        for vec in test_vectors:
            run_comparison(vec, model_a, model_b, label, min_comp)
