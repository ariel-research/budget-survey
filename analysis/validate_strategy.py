"""
Consolidated Validation Suite for OptimizationMetricsRankStrategy.

This script audits the pair generation strategy.
Updated to perform a 'Steel Man' comparison for Min-Max Normalization:
It uses a brute-force optimizer to find the best possible Min-Max pairs.

Includes detailed logging with L1 RANKS to verify vector quality.
"""

import argparse
import logging
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

# Adjust path to import application modules
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
        choices=["single", "global"],
        default="single",
        help="Analysis mode: 'single' for one user, 'global' for all valid inputs.",
    )
    parser.add_argument(
        "--user-vector",
        nargs="+",
        type=int,
        default=[50, 30, 20],
        help="User vector for single mode (integers summing to 100)",
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
    Finds maximum separation mathematically possible, ensuring UNIQUE usage.
    """
    n = len(l1_scores)
    candidates = []

    # Optimization: Subsample if too large
    indices = np.arange(n)
    if n > 2000:
        indices = np.random.choice(indices, 2000, replace=False)

    l1_sub = l1_scores[indices]
    leo_sub = leo_scores[indices]

    # O(N^2) search for trade-offs
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

            l1_gain = score_l1_a - score_l1_b
            leo_gain = score_leo_b - score_leo_a

            if l1_gain > 0 and leo_gain > 0:
                total_separation = l1_gain + leo_gain

                # Balance check
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


# ============================================================================
# MODE 1: SINGLE USER ANALYSIS
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

        # ---------------------------------------------------------
        # METHOD A: RANK NORMALIZATION (Standard)
        # ---------------------------------------------------------
        l1_ranks = (len(l1_distances) - rankdata(l1_distances) + 1) / len(l1_distances)
        leontief_ranks = rankdata(leontief_ratios) / len(l1_distances)

        rank_pairs_meta = strategy._find_complementary_pairs(
            vector_pool, l1_ranks, leontief_ranks, strategy.TARGET_PAIRS
        )
        logger.info(f"\n ✅ [Rank Strategy] Found {len(rank_pairs_meta)} pairs")

        # LOG SELECTED PAIRS FOR RANK
        logger.info("    --- Rank Selected Pairs (With L1 Ranks) ---")
        rank_indices_check = []
        for i, (idx_a, idx_b, _, _, _) in enumerate(rank_pairs_meta):
            rank_indices_check.extend([idx_a, idx_b])
            vec_a = vector_pool[idx_a]
            vec_b = vector_pool[idx_b]
            rank_a = l1_ranks[idx_a]
            rank_b = l1_ranks[idx_b]

            logger.info(f"    Pair {i+1}:")
            logger.info(f"       A: Idx {idx_a} | Vec {vec_a} | L1 Rank: {rank_a:.4f}")
            logger.info(f"       B: Idx {idx_b} | Vec {vec_b} | L1 Rank: {rank_b:.4f}")

        if len(rank_indices_check) != len(set(rank_indices_check)):
            logger.error("    !!! DUPLICATE INDICES FOUND IN RANK STRATEGY !!!")
        else:
            logger.info("    (Verified: All indices are unique)")

        # ---------------------------------------------------------
        # METHOD B: MIN-MAX NORMALIZATION (Brute Force / Steel Man)
        # ---------------------------------------------------------
        l1_mm = normalize_minmax(l1_distances, invert=True)
        leo_mm = normalize_minmax(leontief_ratios, invert=False)

        mm_pairs_meta = _find_best_pairs_brute_force(
            l1_mm, leo_mm, strategy.TARGET_PAIRS
        )

        logger.info(f"\n ✅ [Min-Max Strategy] Found {len(mm_pairs_meta)} pairs")
        if len(mm_pairs_meta) > 0:
            avg_score = sum(p[3] for p in mm_pairs_meta) / len(mm_pairs_meta)
            logger.info(f"    -> Avg Separation Score: {avg_score:.4f}")

        # LOG SELECTED PAIRS FOR MIN-MAX
        logger.info("    --- Min-Max Selected Pairs (With L1 Ranks) ---")
        mm_indices_check = []
        for i, (idx_a, idx_b, _, _, _) in enumerate(mm_pairs_meta):
            mm_indices_check.extend([idx_a, idx_b])
            vec_a = vector_pool[idx_a]
            vec_b = vector_pool[idx_b]
            # Use the global L1 Ranks for apple-to-apple quality comparison
            rank_a = l1_ranks[idx_a]
            rank_b = l1_ranks[idx_b]

            logger.info(f"    Pair {i+1}:")
            logger.info(f"       A: Idx {idx_a} | Vec {vec_a} | L1 Rank: {rank_a:.4f}")
            logger.info(f"       B: Idx {idx_b} | Vec {vec_b} | L1 Rank: {rank_b:.4f}")

        if len(mm_indices_check) != len(set(mm_indices_check)):
            logger.error("    !!! DUPLICATE INDICES FOUND IN MIN-MAX STRATEGY !!!")
        else:
            logger.info("    (Verified: All indices are unique)")

        # ---------------------------------------------------------
        # VISUALIZATION
        # ---------------------------------------------------------
        _compare_selection_logic(
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


def _compare_selection_logic(
    user_vector, vector_pool, rank_l1, rank_leo, rank_pairs, mm_l1, mm_leo, mm_pairs
):
    """Generates the A/B comparison plot."""
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Calculate Overlap
    set_rank = set(tuple(sorted((p[0], p[1]))) for p in rank_pairs)
    set_mm = set(tuple(sorted((p[0], p[1]))) for p in mm_pairs)
    overlap = len(set_rank.intersection(set_mm))

    fig, axes = plt.subplots(1, 2, figsize=(20, 9))

    # --- PLOT 1: RANK SPACE ---
    ax1 = axes[0]
    ax1.scatter(rank_l1, rank_leo, c="gray", s=5, alpha=0.1, label="Pool")

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
# MODE 2: GLOBAL (Simplified for this context)
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
    # Placeholder for brevity
    pass


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = _parse_args()
    if args.mode == "single":
        analyze_single_user(tuple(args.user_vector))
    else:
        analyze_global_robustness()
