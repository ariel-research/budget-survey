"""
Consolidated Validation Suite for OptimizationMetricsRankStrategy.

Modes:
1. Single User Analysis:
   Validates pair quality for a specific input vector.
   Generates 'validation_dashboard.png'.

2. Global Robustness Analysis:
   Simulates algorithm performance across ALL possible valid user vectors (228 total).
   Reports which vectors require lower-quality relaxation levels.
   Generates 'global_level_distribution.png'.

Usage:
   python analysis/validate_strategy.py --mode single --user-vector 50 30 20
   python analysis/validate_strategy.py --mode global
"""

import argparse
import logging
import sys
from collections import Counter, defaultdict
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
# MODE 1: SINGLE USER ANALYSIS
# ============================================================================


def analyze_single_user(user_vector: tuple) -> None:
    """Generate pairs for one user and visualize the specific results."""
    strategy = OptimizationMetricsRankStrategy()
    vector_size = len(user_vector)

    logger.info(f" Analyzing User Vector: {user_vector}")
    logger.info(
        f" Pool Size: {strategy.POOL_SIZE} | Target Pairs: {strategy.TARGET_PAIRS}"
    )

    try:
        # 1. Manual Metric Calculation (for visualization context)
        vector_pool = list(
            strategy.generate_vector_pool(strategy.POOL_SIZE, vector_size)
        )

        l1_distances = np.array(
            [strategy._calculate_l1_distance(user_vector, v) for v in vector_pool]
        )
        leontief_ratios = np.array(
            [strategy._calculate_leontief_ratio(user_vector, v) for v in vector_pool]
        )

        # Calculate Ranks
        l1_norm = (len(l1_distances) - rankdata(l1_distances) + 1) / len(l1_distances)
        leontief_norm = rankdata(leontief_ratios) / len(l1_distances)

        # 2. Run Strategy Logic
        pairs_meta = strategy._find_complementary_pairs(
            vector_pool, l1_norm, leontief_norm, strategy.TARGET_PAIRS
        )

        logger.info(f" ✅ Found {len(pairs_meta)} pairs")
        _plot_single_dashboard(
            user_vector, pairs_meta, l1_norm, leontief_norm, strategy
        )

    except Exception as e:
        logger.error(f" Strategy Failed: {e}")
        import traceback

        traceback.print_exc()


def _plot_single_dashboard(user_vector, pairs_meta, l1_norm, leontief_norm, strategy):
    """Visualizes the specific pairs selected for this user."""
    OUTPUT_DIR.mkdir(exist_ok=True)

    fig = plt.figure(figsize=(14, 7))
    gs = fig.add_gridspec(1, 2)

    # --- LEFT PLOT: Level Distribution ---
    ax1 = fig.add_subplot(gs[0, 0])

    level_counts = {i: 0 for i in range(1, len(strategy.RELAXATION_LEVELS) + 1)}
    for _, _, level, _, _ in pairs_meta:
        level_counts[level] += 1

    colors = ["#e74c3c", "#e67e22", "#f1c40f", "#3498db", "#95a5a6"]

    ax1.bar(
        level_counts.keys(),
        level_counts.values(),
        color=colors[: len(level_counts)],
        edgecolor="black",
        alpha=0.8,
    )

    ax1.set_xlabel("Relaxation Level")
    ax1.set_ylabel("Pairs Selected")
    ax1.set_title(f"Quality Distribution (Total: {len(pairs_meta)})")
    ax1.set_xticks(list(level_counts.keys()))
    ax1.grid(axis="y", alpha=0.3)

    for i, (lvl, count) in enumerate(level_counts.items()):
        if count > 0:
            epsilon = strategy.RELAXATION_LEVELS[lvl - 1][0]
            ax1.text(lvl, count, f"{count}\n(ε={epsilon})", ha="center", va="bottom")

    # --- RIGHT PLOT: Rank Space ---
    ax2 = fig.add_subplot(gs[0, 1])

    # Background: Unused pool
    ax2.scatter(l1_norm, leontief_norm, c="gray", s=5, alpha=0.1, label="Unused Pool")

    # Foreground: Selected Pairs
    legend_added = set()
    for idx_a, idx_b, level, _, _ in pairs_meta:
        color = colors[level - 1] if level <= len(colors) else "black"

        ax2.plot(
            [l1_norm[idx_a], l1_norm[idx_b]],
            [leontief_norm[idx_a], leontief_norm[idx_b]],
            c=color,
            alpha=0.6,
            linewidth=1.5,
        )

        label = f"Level {level}" if level not in legend_added else None
        ax2.scatter(
            [l1_norm[idx_a], l1_norm[idx_b]],
            [leontief_norm[idx_a], leontief_norm[idx_b]],
            c=color,
            s=40,
            edgecolors="white",
            zorder=5,
            label=label,
        )
        if label:
            legend_added.add(level)

    # Diagonal and Annotations
    ax2.plot([0, 1], [0, 1], "k--", alpha=0.2, label="Equal Rank")

    # NEW: Updated Axis Labels
    ax2.set_xlabel("L1 Rank (Higher = Closer Distance)")
    ax2.set_ylabel("Leontief Rank (Higher = Better Ratio)")

    # NEW: Ideal Marker
    ax2.text(1.02, 1.02, "Ideal", color="green", fontsize=9, ha="center")

    # NEW: Quadrant Descriptions
    ax2.text(
        0.05,
        0.95,
        "Ratio Optimized\n(Leontief)",
        transform=ax2.transAxes,
        va="top",
        ha="left",
        fontsize=10,
        fontweight="bold",
        color="#333333",
        bbox=dict(facecolor="white", alpha=0.7, edgecolor="none"),
    )

    ax2.text(
        0.95,
        0.05,
        "Distance Optimized\n(L1)",
        transform=ax2.transAxes,
        va="bottom",
        ha="right",
        fontsize=10,
        fontweight="bold",
        color="#333333",
        bbox=dict(facecolor="white", alpha=0.7, edgecolor="none"),
    )

    ax2.set_title(f"Selected Pairs in Rank Space\nUser: {user_vector}")
    ax2.legend(loc="lower left", fontsize="small")
    ax2.set_xlim(0, 1.05)
    ax2.set_ylim(0, 1.05)

    plt.tight_layout()
    save_path = OUTPUT_DIR / "validation_dashboard.png"
    plt.savefig(save_path, dpi=150)
    logger.info(f" ✅ Dashboard saved to: {save_path}")
    plt.close()


# ============================================================================
# MODE 2: GLOBAL ROBUSTNESS ANALYSIS
# ============================================================================


def generate_all_valid_user_vectors() -> list[tuple]:
    """Generates 228 valid user vectors (sum=100, step=5, >=2 positive dims)."""
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
    """Runs simulation across all valid user vectors and tracks difficulty."""
    strategy = OptimizationMetricsRankStrategy()
    strategy.POOL_SIZE = 5151

    all_vectors = generate_all_valid_user_vectors()
    logger.info(f" Generated {len(all_vectors)} valid user vectors to test.")
    logger.info(" Starting Monte Carlo simulation...")

    pool_list = list(strategy.generate_vector_pool(5151, 3))

    total_pairs_generated = 0
    level_distribution = Counter()
    vectors_by_difficulty = defaultdict(list)

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

        max_level_used = 0
        for _, _, level, _, _ in pairs:
            level_distribution[level] += 1
            total_pairs_generated += 1
            if level > max_level_used:
                max_level_used = level

        # Categorize vector by the worst level it forced us to use
        if max_level_used > 0:
            vectors_by_difficulty[max_level_used].append(user_vec)

    print("\n Simulation complete.")
    _plot_global_stats(level_distribution, total_pairs_generated, len(all_vectors))
    _print_difficulty_report(vectors_by_difficulty)


def _print_difficulty_report(vectors_by_difficulty):
    """Prints list of vectors that required lower quality levels."""
    logger.info("\n" + "=" * 60)
    logger.info("VECTOR DIFFICULTY BREAKDOWN")
    logger.info("=" * 60)

    # Levels 3, 4, 5 are the ones we care about inspecting
    for level in range(5, 2, -1):
        vectors = vectors_by_difficulty.get(level, [])
        if vectors:
            logger.info(f"\n[Level {level} Required] ({len(vectors)} vectors):")
            # Limit output if there are too many, but usually there aren't for L5
            display_vecs = vectors[:15]
            vec_str = ", ".join(str(v) for v in display_vecs)
            if len(vectors) > 15:
                vec_str += f", ... (+{len(vectors)-15} more)"
            logger.info(f"  {vec_str}")

    l1_count = len(vectors_by_difficulty.get(1, []))
    l2_count = len(vectors_by_difficulty.get(2, []))
    logger.info(
        f"\nSummary: {l1_count} vectors perfect (L1), {l2_count} vectors good (L2)."
    )


def _plot_global_stats(distribution: Counter, total_pairs: int, total_vectors: int):
    OUTPUT_DIR.mkdir(exist_ok=True)

    levels = sorted(distribution.keys())
    counts = [distribution[lbl] for lbl in levels]
    percentages = [c / total_pairs * 100 for c in counts]

    colors = ["#e74c3c", "#e67e22", "#f1c40f", "#3498db", "#95a5a6"]
    labels = ["Strict", "Moderate", "Loose", "Minimal", "Safety Net"]

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(levels, percentages, color=colors[: len(levels)], edgecolor="black")

    ax.set_title(
        f"Global Robustness Analysis\nBased on {total_vectors} vectors ({total_pairs} pairs total)"
    )
    ax.set_xlabel("Relaxation Level")
    ax.set_ylabel("Frequency of Use (%)")
    ax.set_xticks(levels)
    ax.set_xticklabels([f"Level {lbl}\n{labels[lbl-1]}" for lbl in levels])
    ax.set_ylim(0, max(percentages) + 10)
    ax.grid(axis="y", alpha=0.3)

    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            height,
            f"{height:.1f}%",
            ha="center",
            va="bottom",
            fontweight="bold",
        )

    save_path = OUTPUT_DIR / "global_level_distribution.png"
    plt.savefig(save_path, dpi=150)
    logger.info(f" Chart saved to {save_path}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = _parse_args()

    if args.mode == "single":
        analyze_single_user(tuple(args.user_vector))
    else:
        analyze_global_robustness()
