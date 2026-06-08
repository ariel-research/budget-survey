"""
Consolidated Validation Suite for OptimizationMetricsRankStrategy.

This script audits the pair generation strategy.

Modes:
1. 'single':      Checks Normalization Impact (Rank vs Min-Max).
                  Uses a 'Steel Man' Brute Force optimizer for Min-Max to find 
                  the best possible pairs ignoring standard thresholds.
                  
2. 'logic_check': Checks Selection Logic Impact (Sum-Score vs Min-Score).
                  Operates on Rank Data to isolate the scoring logic variable.

3. 'global':      Checks Robustness across all 228 valid user vectors.
"""

import argparse
import logging
import sys
from collections import Counter
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np

sys.path.append(str(Path(__file__).resolve().parent.parent))

from application.services.pair_generation.optimization_metrics_rank import (
    OptimizationMetricsRankStrategy,
    rankdata,
)

plt.switch_backend("Agg")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "analysis_output"
logger = logging.getLogger("validation")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Strategy Validation Suite")
    parser.add_argument(
        "--mode",
        choices=["single", "global", "logic_check"],
        default="single",
        help="Analysis mode: 'single' (Norm check), 'logic_check' (Sum vs Min), 'global' (Robustness).",
    )
    parser.add_argument(
        "--user-vector",
        nargs="+",
        type=int,
        default=[50, 30, 20],
        help="User vector for single/logic mode (integers summing to 100)",
    )
    return parser.parse_args()


# ============================================================================
# HELPER: Normalization & Optimization Logic
# ============================================================================


def normalize_minmax(data: np.ndarray, invert: bool = False) -> np.ndarray:
    """Normalizes array to [0, 1]."""
    d_min = np.min(data)
    d_max = np.max(data)
    if d_max == d_min:
        return np.zeros_like(data) if not invert else np.ones_like(data)
    norm = (data - d_min) / (d_max - d_min)
    if invert:
        return 1.0 - norm
    return norm


def _find_best_pairs_brute_force(
    l1_scores: np.ndarray, leo_scores: np.ndarray, target_count: int = 10
) -> list:
    """
    BRUTE FORCE OPTIMIZER for Min-Max Comparison.
    Finds maximum separation mathematically possible (Sum of Gains), ensuring UNIQUE usage.
    """
    n = len(l1_scores)
    candidates = []

    # Optimization: Subsample if too large to avoid O(N^2) hangs
    indices = np.arange(n)
    if n > 2500:
        indices = np.random.choice(indices, 2500, replace=False)

    l1_sub = l1_scores[indices]
    leo_sub = leo_scores[indices]

    for i in range(len(indices)):
        idx_a = indices[i]
        score_l1_a = l1_sub[i]
        score_leo_a = leo_sub[i]

        for j in range(len(indices)):
            if i == j:
                continue

            idx_b = indices[j]
            score_l1_b = l1_sub[j]
            score_leo_b = leo_sub[j]

            # Gain: How much better is A at L1? How much better is B at Leo?
            l1_gain = score_l1_a - score_l1_b
            leo_gain = score_leo_b - score_leo_a

            if l1_gain > 0 and leo_gain > 0:
                total_separation = l1_gain + leo_gain

                # Balance check to avoid extreme outliers (e.g. 0.0001 gain vs 0.9 gain)
                ratio = l1_gain / leo_gain if leo_gain > 0 else 999
                if ratio < 1:
                    ratio = 1 / ratio

                candidates.append(
                    {
                        "indices": (idx_a, idx_b),
                        "score": total_separation,
                        "balance": ratio,
                    }
                )

    # Sort by Score (Biggest separation first)
    candidates.sort(key=lambda x: x["score"], reverse=True)

    results = []
    used_indices = set()

    for cand in candidates:
        if len(results) >= target_count:
            break
        a, b = cand["indices"]

        # STRICT UNIQUENESS CHECK
        if a not in used_indices and b not in used_indices:
            results.append((a, b, 0, cand["score"], cand["balance"]))
            used_indices.add(a)
            used_indices.add(b)

    return results


def _find_pairs_max_min(l1_ranks, leo_ranks, target_count=10):
    """
    STRATEGY B:
    Selects pairs based on Max(Min(Gain_L1, Gain_Leo)).
    NO Ratio filtering involved (Pure max-min).
    """
    n = len(l1_ranks)
    candidates = []

    indices = np.arange(n)
    if n > 2500:
        indices = np.random.choice(indices, 2500, replace=False)

    l1_sub = l1_ranks[indices]
    leo_sub = leo_ranks[indices]

    for i in range(len(indices)):
        idx_a = indices[i]
        for j in range(len(indices)):
            if i == j:
                continue
            idx_b = indices[j]

            # Gains
            gain_l1 = l1_sub[i] - l1_sub[j]
            gain_leo = leo_sub[j] - leo_sub[i]

            if gain_l1 > 0 and gain_leo > 0:
                # Alternative LOGIC: Score is the MINIMUM of the two
                min_score = min(gain_l1, gain_leo)
                candidates.append(
                    {
                        "indices": (idx_a, idx_b),
                        "score": min_score,
                        "gains": (gain_l1, gain_leo),
                    }
                )

    # Sort by Min Score
    candidates.sort(key=lambda x: x["score"], reverse=True)

    results = []
    used = set()
    for c in candidates:
        if len(results) >= target_count:
            break
        a, b = c["indices"]
        if a not in used and b not in used:
            results.append(c)
            used.add(a)
            used.add(b)

    return results


def _compute_average_sum(pairs: list[dict]) -> Optional[float]:
    """Compute the average Sum score (gain_l1 + gain_leo) for the provided pairs."""
    if not pairs:
        return None
    total_sum = sum(
        (gain_l1 + gain_leo) for gain_l1, gain_leo in (p["gains"] for p in pairs)
    )
    return total_sum / len(pairs)


# ============================================================================
# MODE 1: SINGLE USER ANALYSIS (Norm Check)
# ============================================================================


def analyze_single_user(user_vector: tuple) -> None:
    """Generate pairs for one user and compare Normalization methods."""
    strategy = OptimizationMetricsRankStrategy()
    vector_size = len(user_vector)

    logger.info(f" Analyzing User Vector: {user_vector}")

    try:
        # 1. Generate ONE common pool
        vector_pool = list(
            strategy.generate_vector_pool(strategy.POOL_SIZE, vector_size)
        )

        # 2. Calculate Raw Metrics
        l1_distances = np.array(
            [strategy._calculate_l1_distance(user_vector, v) for v in vector_pool]
        )
        leontief_ratios = np.array(
            [strategy._calculate_leontief_ratio(user_vector, v) for v in vector_pool]
        )

        # --- METHOD A: RANK NORMALIZATION (Standard) ---
        l1_ranks = (len(l1_distances) - rankdata(l1_distances) + 1) / len(l1_distances)
        leontief_ranks = rankdata(leontief_ratios) / len(l1_distances)

        rank_pairs_meta = strategy._find_complementary_pairs(
            vector_pool, l1_ranks, leontief_ranks, strategy.TARGET_PAIRS
        )
        logger.info(f"\n ✅ [Rank Strategy] Found {len(rank_pairs_meta)} pairs")

        # Log details for Rank pairs
        logger.info("    --- Rank Selected Pairs ---")
        for i, (idx_a, idx_b, _, _, _) in enumerate(rank_pairs_meta):
            logger.info(
                f"    Pair {i+1}: L1 Rank {l1_ranks[idx_a]:.3f} vs {l1_ranks[idx_b]:.3f}"
            )

        # --- METHOD B: MIN-MAX NORMALIZATION (Brute Force) ---
        l1_mm = normalize_minmax(l1_distances, invert=True)
        leo_mm = normalize_minmax(leontief_ratios, invert=False)

        mm_pairs_meta = _find_best_pairs_brute_force(
            l1_mm, leo_mm, strategy.TARGET_PAIRS
        )
        logger.info(f"\n ✅ [Min-Max Strategy] Found {len(mm_pairs_meta)} pairs")

        # Visualization
        _compare_normalization_plots(
            user_vector,
            vector_pool,
            l1_ranks,
            leontief_ranks,
            rank_pairs_meta,
            l1_mm,
            leo_mm,
            mm_pairs_meta,
        )

    except Exception as e:
        logger.error(f" Strategy Failed: {e}")
        import traceback

        traceback.print_exc()


def _compare_normalization_plots(
    user_vector, vector_pool, rank_l1, rank_leo, rank_pairs, mm_l1, mm_leo, mm_pairs
):
    """Generates the Rank vs Min-Max plot."""
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Calculate Overlap
    set_rank = set(tuple(sorted((p[0], p[1]))) for p in rank_pairs)
    set_mm = set(tuple(sorted((p[0], p[1]))) for p in mm_pairs)
    overlap = len(set_rank.intersection(set_mm))

    fig, axes = plt.subplots(1, 2, figsize=(20, 9))

    # --- PLOT 1: RANK SPACE ---
    ax1 = axes[0]
    ax1.scatter(rank_l1, rank_leo, c="gray", s=5, alpha=0.1, label="Pool")

    # Rank Selections (Red)
    for idx_a, idx_b, _, _, _ in rank_pairs:
        ax1.plot(
            [rank_l1[idx_a], rank_l1[idx_b]],
            [rank_leo[idx_a], rank_leo[idx_b]],
            c="#e74c3c",
            alpha=0.9,
            linewidth=2,
            label="Rank Selected",
        )
        ax1.scatter(
            [rank_l1[idx_a], rank_l1[idx_b]],
            [rank_leo[idx_a], rank_leo[idx_b]],
            c="#e74c3c",
            s=40,
            zorder=5,
        )

    # Min-Max Selections projected (Blue Dashed)
    mm_label_added = False
    for idx_a, idx_b, _, _, _ in mm_pairs:
        if tuple(sorted((idx_a, idx_b))) in set_rank.intersection(set_mm):
            continue
        label = "Min-Max Selected" if not mm_label_added else ""
        ax1.plot(
            [rank_l1[idx_a], rank_l1[idx_b]],
            [rank_leo[idx_a], rank_leo[idx_b]],
            c="#3498db",
            alpha=0.7,
            linewidth=1.5,
            linestyle="--",
            label=label,
        )
        mm_label_added = True

    handles, labels = ax1.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax1.legend(by_label.values(), by_label.keys(), loc="lower right")
    ax1.set_title("Strategy A: Rank Normalization\n(Algorithm Space)")
    ax1.set_xlabel("L1 Rank")
    ax1.set_ylabel("Leontief Rank")

    # --- PLOT 2: MIN-MAX SPACE ---
    ax2 = axes[1]
    ax2.scatter(mm_l1, mm_leo, c="gray", s=5, alpha=0.1, label="Pool")

    # Min-Max Selections (Blue)
    for idx_a, idx_b, _, _, _ in mm_pairs:
        ax2.plot(
            [mm_l1[idx_a], mm_l1[idx_b]],
            [mm_leo[idx_a], mm_leo[idx_b]],
            c="#3498db",
            alpha=0.9,
            linewidth=2,
            label="Min-Max Selected",
        )
        ax2.scatter(
            [mm_l1[idx_a], mm_l1[idx_b]],
            [mm_leo[idx_a], mm_leo[idx_b]],
            c="#3498db",
            s=40,
            zorder=5,
        )

    # Rank Selections projected (Red Dashed)
    rank_label_added = False
    for idx_a, idx_b, _, _, _ in rank_pairs:
        if tuple(sorted((idx_a, idx_b))) in set_rank.intersection(set_mm):
            continue
        label = "Rank Selected" if not rank_label_added else ""
        ax2.plot(
            [mm_l1[idx_a], mm_l1[idx_b]],
            [mm_leo[idx_a], mm_leo[idx_b]],
            c="#e74c3c",
            alpha=0.5,
            linewidth=1.5,
            linestyle="--",
            label=label,
        )
        rank_label_added = True

    handles, labels = ax2.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax2.legend(by_label.values(), by_label.keys(), loc="lower right")

    ax2.set_title("Strategy B: Min-Max Normalization\n(Brute Force Optimization)")
    ax2.set_xlabel("L1 Min-Max Score")
    ax2.set_ylabel("Leontief Min-Max Score")

    fig.suptitle(
        f"Normalization Impact: {user_vector} | Overlap: {overlap}/10", fontsize=16
    )
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "selection_logic_comparison.png", dpi=150)
    logger.info(" ✅ Comparison plot saved.")


# ============================================================================
# MODE 2: LOGIC CHECK (Sum vs Min on Rank Data)
# ============================================================================


def analyze_logic_comparison(user_vector: tuple) -> None:
    """Compares 'Sum Score' vs 'Min Score' strategies on Rank Data."""
    strategy = OptimizationMetricsRankStrategy()
    logger.info(f" Analyzing Logic (Sum vs Min) for: {user_vector}")

    # 1. Setup Data
    pool = list(strategy.generate_vector_pool(strategy.POOL_SIZE, 3))
    l1_raw = np.array([strategy._calculate_l1_distance(user_vector, v) for v in pool])
    leo_raw = np.array(
        [strategy._calculate_leontief_ratio(user_vector, v) for v in pool]
    )

    l1_ranks = (len(l1_raw) - rankdata(l1_raw) + 1) / len(l1_raw)
    leo_ranks = rankdata(leo_raw) / len(l1_raw)

    # 2. Strategy A: CURRENT (Sum + Ratio Filter)
    # Using the class method to ensure exact reproduction of production logic
    pairs_sum_meta = strategy._find_complementary_pairs(pool, l1_ranks, leo_ranks, 10)
    pairs_sum = []
    for p in pairs_sum_meta:
        idx_a, idx_b = p[0], p[1]
        gain_l1 = l1_ranks[idx_a] - l1_ranks[idx_b]
        gain_leo = leo_ranks[idx_b] - leo_ranks[idx_a]
        pairs_sum.append(
            {
                "indices": (idx_a, idx_b),
                "score": gain_l1 + gain_leo,
                "gains": (gain_l1, gain_leo),
            }
        )

    # 3. Strategy B: Alternative (Max Min, No Filter)
    pairs_min = _find_pairs_max_min(l1_ranks, leo_ranks, 10)

    # 4. Analysis
    set_sum = set(tuple(sorted(p["indices"])) for p in pairs_sum)
    set_min = set(tuple(sorted(p["indices"])) for p in pairs_min)
    overlap = len(set_sum.intersection(set_min))

    sum_exclusive_pairs = [
        p for p in pairs_sum if tuple(sorted(p["indices"])) not in set_min
    ]
    min_exclusive_pairs = [
        p for p in pairs_min if tuple(sorted(p["indices"])) not in set_sum
    ]
    overlap_pairs = [p for p in pairs_sum if tuple(sorted(p["indices"])) in set_min]

    logger.info(f" 📊 Logic Overlap: {overlap}/10 pairs")

    # 5. Plot
    OUTPUT_DIR.mkdir(exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.scatter(l1_ranks, leo_ranks, c="gray", s=1, alpha=0.1)

    # Plot Sum Strategy (Red)
    for p in pairs_sum:
        a, b = p["indices"]
        ax.plot(
            [l1_ranks[a], l1_ranks[b]],
            [leo_ranks[a], leo_ranks[b]],
            c="red",
            alpha=0.6,
            linewidth=2,
            label="Current (Sum)",
        )
        ax.scatter(
            [l1_ranks[a], l1_ranks[b]], [leo_ranks[a], leo_ranks[b]], c="red", s=30
        )

    # Plot Min Strategy (Blue)
    min_added = False
    for p in pairs_min:
        a, b = p["indices"]
        if tuple(sorted((a, b))) not in set_sum:
            label = "Tested approach (Min)" if not min_added else ""
            ax.plot(
                [l1_ranks[a], l1_ranks[b]],
                [leo_ranks[a], leo_ranks[b]],
                c="blue",
                alpha=0.6,
                linewidth=2,
                linestyle="--",
                label=label,
            )
            ax.scatter(
                [l1_ranks[a], l1_ranks[b]], [leo_ranks[a], leo_ranks[b]], c="blue", s=30
            )
            min_added = True

    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys())

    ax.set_title(f"Logic Check: Sum vs Min | Overlap: {overlap}/10")
    ax.set_xlabel("L1 Rank")
    ax.set_ylabel("Leo Rank")
    ax.plot([0, 1], [0, 1], "k--", alpha=0.1)

    save_path = OUTPUT_DIR / "logic_comparison.png"
    plt.savefig(save_path, dpi=150)
    logger.info(f" ✅ Logic comparison plot saved to: {save_path}")

    # Log details
    if sum_exclusive_pairs or min_exclusive_pairs:
        logger.info("\n--- EXCLUSIVE TO SUM (Current) ---")
        for p in sum_exclusive_pairs:
            idx_a, idx_b = p["indices"]
            g1, g2 = p["gains"]
            vec_a = pool[idx_a]
            vec_b = pool[idx_b]
            logger.info(
                f"{vec_a} vs {vec_b}: L1={g1:.2f}, Leo={g2:.2f} | Sum={g1+g2:.2f} | Min={min(g1,g2):.2f}"
            )

        logger.info("\n--- EXCLUSIVE TO MIN (Tested Approach) ---")
        for p in min_exclusive_pairs:
            idx_a, idx_b = p["indices"]
            g1, g2 = p["gains"]
            vec_a = pool[idx_a]
            vec_b = pool[idx_b]
            logger.info(
                f"{vec_a} vs {vec_b}: L1={g1:.2f}, Leo={g2:.2f} | Sum={g1+g2:.2f} | Min={min(g1,g2):.2f}"
            )

    logger.info("\n--- AVERAGE SUM BY GROUP ---")
    group_definitions = [
        ("Current Strategy (Sum total)", pairs_sum),
        ("Tested Strategy (Min total)", pairs_min),
        ("Overlap (Both strategies)", overlap_pairs),
        ("Exclusive Current", sum_exclusive_pairs),
        ("Exclusive Tested", min_exclusive_pairs),
    ]

    for label, group_pairs in group_definitions:
        avg_sum = _compute_average_sum(group_pairs)
        if avg_sum is None:
            logger.info(f"{label}: n/a")
        else:
            logger.info(f"{label}: {avg_sum:.2f}")


# ============================================================================
# MODE 3: GLOBAL (Robustness)
# ============================================================================


def generate_all_valid_user_vectors() -> list[tuple]:
    valid_vectors = []
    step = 5
    for x in range(0, 105, step):
        for y in range(0, 105 - x, step):
            z = 100 - x - y
            vector = (x, y, z)
            if sum(1 for v in vector if v > 0) >= 2:
                valid_vectors.append(vector)
    return valid_vectors


def analyze_global_robustness():
    """Runs simulation across all valid user vectors."""
    strategy = OptimizationMetricsRankStrategy()
    strategy.POOL_SIZE = 5151

    all_vectors = generate_all_valid_user_vectors()
    logger.info(f" Generated {len(all_vectors)} valid user vectors.")
    pool_list = list(strategy.generate_vector_pool(strategy.POOL_SIZE, 3))

    total_pairs_generated = 0
    level_distribution = Counter()

    for i, user_vec in enumerate(all_vectors):
        if i % 20 == 0:
            print(f" Processing vector {i}/{len(all_vectors)}...", end="\r")

        l1_dists = np.array(
            [strategy._calculate_l1_distance(user_vec, v) for v in pool_list]
        )
        leo_ratios = np.array(
            [strategy._calculate_leontief_ratio(user_vec, v) for v in pool_list]
        )

        n = len(pool_list)
        l1_ranks = (n - rankdata(l1_dists) + 1) / n
        leo_ranks = rankdata(leo_ratios) / n

        pairs = strategy._find_complementary_pairs(
            pool_list, l1_ranks, leo_ranks, strategy.TARGET_PAIRS
        )

        for _, _, level, _, _ in pairs:
            level_distribution[level] += 1
            total_pairs_generated += 1

    print("\n Simulation complete.")
    _plot_global_stats(level_distribution, total_pairs_generated, len(all_vectors))


def _plot_global_stats(distribution: Counter, total_pairs: int, total_vectors: int):
    OUTPUT_DIR.mkdir(exist_ok=True)
    levels = sorted(distribution.keys())
    counts = [distribution[lev] for lev in levels]
    percentages = [c / total_pairs * 100 for c in counts]

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(levels, percentages, color="#e74c3c", edgecolor="black")
    ax.set_title(f"Global Robustness Analysis ({total_vectors} vectors)")
    ax.set_ylabel("Frequency (%)")
    ax.set_xlabel("Level")
    for bar in bars:
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{bar.get_height():.1f}%",
            ha="center",
            va="bottom",
        )

    plt.savefig(OUTPUT_DIR / "global_level_distribution.png", dpi=150)
    logger.info("Saved global distribution plot.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = _parse_args()

    if args.mode == "single":
        analyze_single_user(tuple(args.user_vector))
    elif args.mode == "logic_check":
        analyze_logic_comparison(tuple(args.user_vector))
    else:
        analyze_global_robustness()
