"""
Compares three pair-scoring strategies for the GenericRankStrategy:
  - max_min:       score = min(gain_a, gain_b)
  - weighted_cc:   score = min(gain_a, gain_b) + λ * (max(gain_a, gain_b) - min(gain_a, gain_b))
  - harmonic_mean: score = 2 * gain_a * gain_b / (gain_a + gain_b)

For each (user vector × model pair), the script checks whether the three
formulas select the same top-k survey pairs. When they don't, the script
classifies the disagreement:

  • Genuine divergence — the formulas have structurally different opinions
    about which pairs are most informative. Example: MaxMin picks a balanced
    pair (gain_a=0.06, gain_b=0.06), while HarmonicMean picks a lopsided one
    (gain_a=0.09, gain_b=0.05). Choosing a formula changes the survey.

  • Tiebreaking artifact — all formulas agree the same broad cluster of pairs
    is best, but hundreds of pairs share nearly identical scores. The exact
    10 picked depend on arbitrary tiebreaking, not genuine formula disagreement.
    Diagnosed by: low Jaccard (different top-10) but high Spearman (same full ordering).

Output sections:
  1. Per-vector results — compact for agreement, detailed for divergence
  2. Summary table — one row per (vector × model pair), scannable at a glance
  3. Automatic recommendations — classified divergence cases with suggested actions

Key metrics:
  • Valid pairs — pairs where the two utility models disagree about which budget
    vector is better. Only these are useful in a survey; if both models agreed,
    the user's choice reveals nothing about their utility function.
  • Jaccard similarity — do two formulas pick the same 10 pairs to show users?
    1.0 = identical selection, 0.0 = no overlap. Directly answers: "would a user
    see different survey questions depending on the formula?"
  • Spearman ρ — do two formulas agree on the ordering of ALL valid pairs, not
    just the top 10? Values above 0.95 mean the formulas are interchangeable.
    Distinguishes genuine divergence (low Spearman) from tiebreaking artifacts
    (high Spearman despite low Jaccard).

Results are saved to: scripts/scoring_results.txt
"""

import numpy as np

from application.services.algorithms.math_utils import (
    get_cached_simplex_pool,
    rankdata,
)
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
    _compute_pair_scores,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

K = 10  # Number of pairs selected for surveys (matches production)
SPEARMAN_THRESHOLD = 0.95
JACCARD_THRESHOLD = 0.8

SCORING_METHODS = [
    ("max_min", SCORING_MAX_MIN, 0.0),
    ("weighted_cc", SCORING_WEIGHTED_CC, 0.1),
    ("harmonic_mean", SCORING_HARMONIC_MEAN, 0.0),
]

METHOD_NAMES = [name for name, _, _ in SCORING_METHODS]

ROW_FMT = "  {vec:<22} {valid:>8} {jacc:>10} {spear:>10}   {verdict}"

# ---------------------------------------------------------------------------
# Core computation — shared across all three formulas
# ---------------------------------------------------------------------------


def _compute_valid_pairs(
    user_vector: tuple,
    grid_step: int,
    min_component: int,
    utility_model_a_class,
    utility_model_b_class,
):
    """
    Find all valid discriminating pairs and compute their scores under all
    three formulas in a single pass.

    A pair (i, j) is "valid" when the two utility models disagree about which
    vector is better — model A prefers one, model B prefers the other.

    Returns:
        pool: list of budget vectors (tuples)
        pairs: list of dicts, each with keys:
            idx_a, idx_b, gain_a, gain_b, max_min, weighted_cc, harmonic_mean
    """
    model_a = utility_model_a_class()
    model_b = utility_model_b_class()

    pool = list(
        get_cached_simplex_pool(
            num_variables=len(user_vector),
            side_length=100,
            step=grid_step,
            min_value=min_component,
        )
    )
    n_pool = len(pool)
    if n_pool < 2:
        return pool, []

    # Compute utility scores and normalized ranks (ordinal)
    scores_a = np.array([model_a.calculate(user_vector, v) for v in pool])
    scores_b = np.array([model_b.calculate(user_vector, v) for v in pool])

    raw_ranks_a = rankdata(scores_a)
    raw_ranks_b = rankdata(scores_b)
    ranks_a = (raw_ranks_a - 1) / (n_pool - 1)
    ranks_b = (raw_ranks_b - 1) / (n_pool - 1)

    ranks_a_f32 = ranks_a.astype(np.float32)
    ranks_b_f32 = ranks_b.astype(np.float32)

    # Collect valid pairs with gains
    all_idx_a, all_idx_b = [], []
    all_gain_a, all_gain_b = [], []

    for i in range(n_pool - 1):
        ga = ranks_a_f32[i] - ranks_a_f32[i + 1 :]
        gb = ranks_b_f32[i + 1 :] - ranks_b_f32[i]

        # Case 1: i better on model A, candidate better on model B
        mask1 = (ga > 0) & (gb > 0)
        if np.any(mask1):
            idx = np.where(mask1)[0]
            all_idx_a.append(np.full(len(idx), i, dtype=np.int32))
            all_idx_b.append(idx + i + 1)
            all_gain_a.append(ga[idx])
            all_gain_b.append(gb[idx])

        # Case 2: candidate better on model A, i better on model B
        mask2 = (ga < 0) & (gb < 0)
        if np.any(mask2):
            idx = np.where(mask2)[0]
            all_idx_a.append(idx + i + 1)
            all_idx_b.append(np.full(len(idx), i, dtype=np.int32))
            all_gain_a.append(-ga[idx])
            all_gain_b.append(-gb[idx])

    if not all_gain_a:
        return pool, []

    final_idx_a = np.concatenate(all_idx_a)
    final_idx_b = np.concatenate(all_idx_b)
    final_gain_a = np.concatenate(all_gain_a)
    final_gain_b = np.concatenate(all_gain_b)

    # Score under all three formulas
    scores = {}
    for name, method, lam in SCORING_METHODS:
        scores[name] = _compute_pair_scores(final_gain_a, final_gain_b, method, lam)

    pairs = []
    for k in range(len(final_idx_a)):
        pairs.append(
            {
                "idx_a": int(final_idx_a[k]),
                "idx_b": int(final_idx_b[k]),
                "gain_a": float(final_gain_a[k]),
                "gain_b": float(final_gain_b[k]),
                "max_min": float(scores["max_min"][k]),
                "weighted_cc": float(scores["weighted_cc"][k]),
                "harmonic_mean": float(scores["harmonic_mean"][k]),
            }
        )

    return pool, pairs


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def _spearman_rho(x: list, y: list) -> float:
    """Spearman rank correlation. Returns 1.0 for trivial (constant) rankings."""
    rx = rankdata(np.array(x))
    ry = rankdata(np.array(y))
    if np.std(rx) == 0 or np.std(ry) == 0:
        return 1.0
    return float(np.corrcoef(rx, ry)[0, 1])


def _jaccard(set_a: set, set_b: set) -> float:
    if not set_a and not set_b:
        return 1.0
    return len(set_a & set_b) / len(set_a | set_b)


# ---------------------------------------------------------------------------
# Single comparison
# ---------------------------------------------------------------------------


def run_comparison(user_vector, model_a_class, model_b_class, label, min_component):
    """
    Run the three-way scoring comparison for one (vector × model pair).
    Returns a result dict for the summary table.
    """
    pool, pairs = _compute_valid_pairs(
        user_vector,
        grid_step=5,
        min_component=min_component,
        utility_model_a_class=model_a_class,
        utility_model_b_class=model_b_class,
    )
    n_valid = len(pairs)

    # --- Early exit: degenerate ---
    if n_valid < 20:
        verdict = "⚠ DEGENERATE"
        print(f"  {str(user_vector):<22}  pairs: {n_valid:<8}  → {verdict}")
        if n_valid == 0:
            print(
                f"  {'':22}  Models agree completely — no discriminating pairs exist.\n"
            )
        else:
            print(f"  {'':22}  Too few valid pairs for reliable comparison.\n")
        return {
            "vector": user_vector,
            "label": label,
            "n_valid": n_valid,
            "min_jaccard": None,
            "min_spearman": None,
            "verdict": verdict,
        }

    # --- Top-k sets and full scores per formula ---
    top_k = {}
    for name in METHOD_NAMES:
        sorted_pairs = sorted(pairs, key=lambda p: p[name], reverse=True)
        top_k[name] = sorted_pairs[:K]

    top_k_sets = {
        name: {frozenset((p["idx_a"], p["idx_b"])) for p in top_k[name]}
        for name in METHOD_NAMES
    }

    # Jaccard
    j_m_w = _jaccard(top_k_sets["max_min"], top_k_sets["weighted_cc"])
    j_m_h = _jaccard(top_k_sets["max_min"], top_k_sets["harmonic_mean"])
    j_w_h = _jaccard(top_k_sets["weighted_cc"], top_k_sets["harmonic_mean"])
    min_jaccard = min(j_m_w, j_m_h, j_w_h)

    # Spearman
    scores_by_method = {name: [p[name] for p in pairs] for name in METHOD_NAMES}

    s_m_w = _spearman_rho(scores_by_method["max_min"], scores_by_method["weighted_cc"])
    s_m_h = _spearman_rho(
        scores_by_method["max_min"], scores_by_method["harmonic_mean"]
    )
    s_w_h = _spearman_rho(
        scores_by_method["weighted_cc"], scores_by_method["harmonic_mean"]
    )
    min_spearman = min(s_m_w, s_m_h, s_w_h)

    # --- Verdict ---
    if min_jaccard >= JACCARD_THRESHOLD and min_spearman >= SPEARMAN_THRESHOLD:
        verdict = "✓ AGREEMENT"
    elif min_jaccard >= JACCARD_THRESHOLD:
        verdict = "~ PARTIAL"
    elif min_spearman >= SPEARMAN_THRESHOLD:
        verdict = "△ TIEBREAK"  # Low Jaccard but high Spearman = tiebreaking artifact
    else:
        verdict = "✗ DIVERGENCE"

    # --- Compact output line ---
    print(
        ROW_FMT.format(
            vec=str(user_vector),
            valid=str(n_valid),
            jacc=f"{min_jaccard:.2f}",
            spear=f"{min_spearman:.2f}",
            verdict=verdict,
        )
    )

    # --- Detail block for divergence / tiebreak cases ---
    if min_jaccard < JACCARD_THRESHOLD:
        # Determine if tiebreaking: check if MaxMin top-k scores are all identical
        mm_top_scores = [p["max_min"] for p in top_k["max_min"]]
        mm_score_spread = max(mm_top_scores) - min(mm_top_scores)
        is_flat_top = mm_score_spread < 0.001

        if is_flat_top and min_spearman >= SPEARMAN_THRESHOLD:
            print(
                f"  {'':22}  MaxMin top-{K} scores all ≈{mm_top_scores[0]:.3f} "
                f"(flat cluster → arbitrary tiebreaking)"
            )
        else:
            # Show cross-score matrix for top-K pairs per formula.
            row_fmt = "      {rank:>4}  {va:>18} vs {vb:>18}  {mm:>7} {wcc:>7} {hm:>7}  {ga:>7} {gb:>7}"

            print(f"\n      Cross-score matrix — each formula's top-{K} pairs:\n")
            print(
                row_fmt.format(
                    rank="",
                    va="Vector A",
                    vb="Vector B",
                    mm="MM",
                    wcc="WCC",
                    hm="HM",
                    ga="gain_a",
                    gb="gain_b",
                )
            )
            print(f"      {'-' * 105}")

            for name in METHOD_NAMES:
                print(f"      {name}'s top-{K}:")
                for rank, p in enumerate(top_k[name], 1):
                    print(
                        row_fmt.format(
                            rank=f"#{rank}",
                            va=str(pool[p["idx_a"]]),
                            vb=str(pool[p["idx_b"]]),
                            mm=f"{p['max_min']:.3f}",
                            wcc=f"{p['weighted_cc']:.3f}",
                            hm=f"{p['harmonic_mean']:.3f}",
                            ga=f"{p['gain_a']:.3f}",
                            gb=f"{p['gain_b']:.3f}",
                        )
                    )
                print()

    print()

    return {
        "vector": user_vector,
        "label": label,
        "n_valid": n_valid,
        "min_jaccard": min_jaccard,
        "min_spearman": min_spearman,
        "verdict": verdict,
    }


# ---------------------------------------------------------------------------
# Summary and recommendations
# ---------------------------------------------------------------------------


def print_summary(all_results):
    """Print the summary table and automatic recommendations."""

    print(f"\n{'=' * 100}")
    print("  SUMMARY TABLE")
    print(f"{'=' * 100}\n")
    print(
        f"  {'Model Pair':<22} {'Vector':<22} {'Valid':>7} "
        f"{'Jaccard':>9} {'Spearman':>10}  {'Verdict'}"
    )
    print(f"  {'-' * 95}")

    for r in all_results:
        j_str = f"{r['min_jaccard']:.2f}" if r["min_jaccard"] is not None else "  —"
        s_str = f"{r['min_spearman']:.2f}" if r["min_spearman"] is not None else "  —"
        print(
            f"  {r['label']:<22} {str(r['vector']):<22} {r['n_valid']:>7} "
            f"{j_str:>9} {s_str:>10}  {r['verdict']}"
        )

    # --- Classify results ---
    genuine = []
    tiebreak = []
    degenerate = []
    agreement = []

    for r in all_results:
        v = r["verdict"]
        if v == "⚠ DEGENERATE":
            degenerate.append(r)
        elif v == "✗ DIVERGENCE":
            genuine.append(r)
        elif v == "△ TIEBREAK":
            tiebreak.append(r)
        else:
            agreement.append(r)

    # --- Recommendations ---
    print(f"\n{'=' * 100}")
    print("  RECOMMENDATIONS")
    print(f"{'=' * 100}")

    if genuine:
        print(
            f"\n  ✗ GENUINE DIVERGENCE ({len(genuine)} cases) — formula choice affects survey pairs:"
        )
        for r in genuine:
            print(
                f"    • {r['label']}, {r['vector']}: "
                f"Spearman {r['min_spearman']:.2f}, {r['n_valid']} valid pairs"
            )
        print(
            "    → WeightedCC (λ=0.1) recommended: stays close to MaxMin while adding"
        )
        print(
            "      principled tiebreaking. HarmonicMean promotes lopsided pairs in these cases."
        )

    if tiebreak:
        print(
            f"\n  △ TIEBREAKING ARTIFACTS ({len(tiebreak)} cases) — low Jaccard from flat score clusters:"
        )
        for r in tiebreak:
            print(
                f"    • {r['label']}, {r['vector']}: "
                f"Spearman {r['min_spearman']:.2f}, {r['n_valid']} valid pairs"
            )
        print("    → Any formula works. WeightedCC provides deterministic tiebreaking.")

    if degenerate:
        print(
            f"\n  ⚠ DEGENERATE ({len(degenerate)} cases) — too few or no valid pairs:"
        )
        for r in degenerate:
            print(f"    • {r['label']}, {r['vector']}: " f"{r['n_valid']} valid pairs")
        print("    → Flag as unsuitable_for_strategy in production.")

    if agreement:
        print(
            f"\n  ✓ AGREEMENT ({len(agreement)} cases) — all formulas equivalent, no action needed."
        )

    n_total = len(all_results)
    n_safe = len(agreement) + len(tiebreak)
    print(
        f"\n  Overall: {n_safe}/{n_total} cases are formula-independent. "
        f"{len(genuine)} require attention."
    )
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    import io
    import os
    import sys

    # Tee stdout: print to terminal AND capture for file output
    output_buffer = io.StringIO()

    class Tee:
        def __init__(self, *streams):
            self.streams = streams

        def write(self, data):
            for s in self.streams:
                s.write(data)

        def flush(self):
            for s in self.streams:
                s.flush()

    sys.stdout = Tee(sys.__stdout__, output_buffer)

    test_vectors = [
        (50, 25, 25),
        (60, 20, 20),
        (70, 15, 15),
        (50, 30, 20),
        (25, 25, 25, 25),
        (40, 30, 20, 10),
        (20, 20, 20, 20, 20),
    ]

    model_pairs = [
        (L1UtilityModel, L2UtilityModel, "L1 vs L2", 0),
        (L1UtilityModel, LeontiefUtilityModel, "L1 vs Leontief", 10),
        (L2UtilityModel, LeontiefUtilityModel, "L2 vs Leontief", 10),
        (KLUtilityModel, L1UtilityModel, "KL vs L1", 10),
        (KLUtilityModel, L2UtilityModel, "KL vs L2", 10),
        (LeontiefUtilityModel, KLUtilityModel, "Leontief vs KL", 10),
    ]

    all_results = []

    for model_a, model_b, label, min_comp in model_pairs:
        print(f"\n{'=' * 100}")
        print(f"  {label}  (min_component={min_comp})")
        print(f"{'=' * 100}")
        print(
            ROW_FMT.format(
                vec="Vector",
                valid="Valid",
                jacc="Jaccard",
                spear="Spearman",
                verdict="Verdict",
            )
        )
        print(f"  {'-' * 85}")

        for vec in test_vectors:
            result = run_comparison(vec, model_a, model_b, label, min_comp)
            all_results.append(result)

    print_summary(all_results)

    output_path = os.path.join(os.path.dirname(__file__), "scoring_results.txt")
    with open(output_path, "w") as f:
        f.write(output_buffer.getvalue())
    print(f"Results saved to: {output_path}")
