"""
Enhanced visualization suite for OptimizationMetricsRankStrategy.

Provides four types of analysis:
1. Basic metric space visualization (rank vs min-max normalization)
2. Pair selection analysis with quality metrics and relaxation effectiveness
3. Simplex coverage validation
4. Multi-vector comparison across different user vector types

PURPOSE: Help determine optimal values for POOL_SIZE, TARGET_PAIRS, and RELAXATION_LEVELS
by analyzing algorithm behavior and pair informativeness.
"""

import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import matplotlib.pyplot as plt
import numpy as np

from application.services.pair_generation.optimization_metrics_rank import (
    OptimizationMetricsRankStrategy,
    rankdata,
)

plt.switch_backend("Agg")  # Ensure rendering works in headless Docker envs

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "analysis_output"
DEFAULT_USER_VECTOR = (35, 35, 30)  # Must be multiples of 5 and sum to 100

logger = logging.getLogger("vector_pool_visualization")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Comprehensive visualization suite for " "OptimizationMetricsRankStrategy"
        )
    )
    parser.add_argument(
        "--user-vector",
        nargs="+",
        type=int,
        default=list(DEFAULT_USER_VECTOR),
        metavar="INT",
        help=(
            "Space-separated integers (multiples of 5) that sum to 100. "
            "Length determines the vector dimensionality. "
            "All values must be multiples of 5 "
            "(default: %(default)s)."
        ),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional numpy.random seed for reproducible vector pools.",
    )
    parser.add_argument(
        "--mode",
        choices=["basic", "pairs", "coverage", "comparison", "all"],
        default="all",
        help=(
            "Visualization mode: "
            "basic (metric spaces), "
            "pairs (pair selection), "
            "coverage (simplex sampling), "
            "comparison (multiple user vectors), "
            "all (generate everything)"
        ),
    )
    return parser.parse_args()


def _ensure_output_dir() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _vector_pool_metrics(
    strategy: OptimizationMetricsRankStrategy,
    user_vector: Tuple[int, ...],
) -> Tuple[np.ndarray, np.ndarray, Sequence[tuple]]:
    """Generate vector pool and compute metrics."""
    vector_size = len(user_vector)
    vector_pool = list(strategy.generate_vector_pool(strategy.POOL_SIZE, vector_size))

    l1_distances = np.array(
        [strategy._calculate_l1_distance(user_vector, vec) for vec in vector_pool],
        dtype=float,
    )
    leontief_ratios = np.array(
        [strategy._calculate_leontief_ratio(user_vector, vec) for vec in vector_pool],
        dtype=float,
    )
    return l1_distances, leontief_ratios, vector_pool


def _compute_rank_metrics(
    l1_distances: np.ndarray, leontief_ratios: np.ndarray
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute rank-normalized metrics and discrepancies."""
    n = len(l1_distances)
    if n == 0:
        raise ValueError("Vector pool is empty; cannot compute ranks.")

    # Match strategy's rank computation exactly
    l1_raw_ranks = rankdata(l1_distances, method="average")
    l1_norm = (n - l1_raw_ranks + 1) / n
    leontief_norm = rankdata(leontief_ratios, method="average") / n
    discrepancies = l1_norm - leontief_norm

    return l1_norm, leontief_norm, discrepancies


def _compute_minmax_metrics(
    l1_distances: np.ndarray, leontief_ratios: np.ndarray
) -> Tuple[np.ndarray, np.ndarray]:
    """Compute min-max normalized metrics."""
    # For L1: lower is better, so invert the normalization
    l1_min, l1_max = l1_distances.min(), l1_distances.max()
    if l1_max > l1_min:
        l1_minmax = (l1_max - l1_distances) / (l1_max - l1_min)
    else:
        l1_minmax = np.ones_like(l1_distances)

    # For Leontief: higher is better, standard normalization
    leo_min, leo_max = leontief_ratios.min(), leontief_ratios.max()
    if leo_max > leo_min:
        leo_minmax = (leontief_ratios - leo_min) / (leo_max - leo_min)
    else:
        leo_minmax = np.ones_like(leontief_ratios)

    return l1_minmax, leo_minmax


# ============================================================================
# MODE 1: BASIC METRIC SPACE VISUALIZATION (ENHANCED)
# ============================================================================


def _plot_absolute_values(
    l1_distances: np.ndarray,
    leontief_ratios: np.ndarray,
    user_vector: Tuple[int, ...],
) -> None:
    """Plot metrics in absolute value space with intuitive axis directions."""
    fig, ax = plt.subplots(figsize=(10, 6))

    # Negate L1 so both axes show "higher is better"
    neg_l1 = -l1_distances

    ax.scatter(
        neg_l1,
        leontief_ratios,
        s=14,
        alpha=0.6,
        c="#1f77b4",
        edgecolors="none",
    )
    ax.set_xlabel(
        "Negative L1 distance (higher = closer to ideal)", fontsize=11, labelpad=12
    )
    ax.set_ylabel(
        "Leontief ratio (higher = maintains proportions)", fontsize=11, labelpad=12
    )
    ax.set_title(
        f"Vector Pool Metrics - Absolute Scale\n"
        f"User Vector: {user_vector} (both axes: higher is better)",
        fontsize=12,
        pad=15,
    )
    ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.4)

    # Add statistics box
    stats_text = (
        f"L1 range: [{l1_distances.min():.0f}, {l1_distances.max():.0f}]\n"
        f"Leontief range: [{leontief_ratios.min():.3f}, "
        f"{leontief_ratios.max():.3f}]\n"
        f"Vectors with Leo=0: {np.sum(leontief_ratios == 0)}"
    )
    ax.text(
        0.02,
        0.98,
        stats_text,
        transform=ax.transAxes,
        fontsize=9,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
    )

    # Add Pareto frontier note
    ax.text(
        0.98,
        0.02,
        "Upper-right = better at both metrics",
        transform=ax.transAxes,
        fontsize=9,
        horizontalalignment="right",
        verticalalignment="bottom",
        style="italic",
        alpha=0.6,
    )

    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "01_absolute_metrics_scatter.png", dpi=200)
    plt.close(fig)
    logger.info("Saved: 01_absolute_metrics_scatter.png")


def _plot_normalization_comparison(
    l1_norm: np.ndarray,
    leontief_norm: np.ndarray,
    l1_minmax: np.ndarray,
    leo_minmax: np.ndarray,
    user_vector: Tuple[int, ...],
) -> None:
    """Compare rank-based vs min-max normalization."""
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    # LEFT: Rank-based
    ax1 = axes[0]
    ax1.scatter(
        l1_norm,
        leontief_norm,
        s=14,
        alpha=0.6,
        c="#ff7f0e",
        edgecolors="none",
        label="Vector pool",
    )
    ax1.plot([0, 1], [0, 1], "k--", alpha=0.3, linewidth=1.5, label="Equal rank")
    ax1.set_xlim(-0.05, 1.05)
    ax1.set_ylim(-0.05, 1.05)
    ax1.set_xlabel(
        "L1 rank (normalized, higher = closer to user vector)",
        fontsize=11,
        labelpad=12,
    )
    ax1.set_ylabel(
        "Leontief rank (normalized, higher = better proportionality)",
        fontsize=11,
        labelpad=12,
    )
    ax1.set_title("RANK-BASED Normalization", fontsize=12, pad=15)
    ax1.grid(True, linestyle="--", linewidth=0.5, alpha=0.4)
    ax1.legend(loc="upper right", fontsize=9)

    corr_rank = np.corrcoef(l1_norm, leontief_norm)[0, 1]
    if corr_rank < 0.65:
        quality_rank = "Excellent"
        color_rank = "lightgreen"
    elif corr_rank < 0.80:
        quality_rank = "Good"
        color_rank = "wheat"
    else:
        quality_rank = "Limited"
        color_rank = "lightcoral"

    ax1.text(
        0.02,
        0.98,
        f"ρ = {corr_rank:.3f}\n{quality_rank} diversity",
        transform=ax1.transAxes,
        fontsize=9,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor=color_rank, alpha=0.6),
    )

    # RIGHT: Min-max
    ax2 = axes[1]
    ax2.scatter(
        l1_minmax,
        leo_minmax,
        s=14,
        alpha=0.6,
        c="#2ca02c",
        edgecolors="none",
        label="Vector pool",
    )
    ax2.plot([0, 1], [0, 1], "k--", alpha=0.3, linewidth=1.5, label="Equal normalized")
    ax2.set_xlim(-0.05, 1.05)
    ax2.set_ylim(-0.05, 1.05)
    ax2.set_xlabel(
        "L1 min-max (normalized, higher = smaller raw distance)",
        fontsize=11,
        labelpad=12,
    )
    ax2.set_ylabel(
        "Leontief min-max (normalized, higher = stronger ratio)",
        fontsize=11,
        labelpad=12,
    )
    ax2.set_title("MIN-MAX Normalization", fontsize=12, pad=15)
    ax2.grid(True, linestyle="--", linewidth=0.5, alpha=0.4)
    ax2.legend(loc="upper right", fontsize=9)

    corr_minmax = np.corrcoef(l1_minmax, leo_minmax)[0, 1]
    if corr_minmax < 0.65:
        quality_minmax = "Excellent"
        color_minmax = "lightgreen"
    elif corr_minmax < 0.80:
        quality_minmax = "Good"
        color_minmax = "wheat"
    else:
        quality_minmax = "Limited"
        color_minmax = "lightcoral"

    ax2.text(
        0.02,
        0.98,
        f"ρ = {corr_minmax:.3f}\n{quality_minmax} diversity",
        transform=ax2.transAxes,
        fontsize=9,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor=color_minmax, alpha=0.6),
    )

    fig.suptitle(
        f"Normalization Comparison: Rank-Based vs Min-Max\n"
        f"User Vector: {user_vector}",
        fontsize=13,
        y=0.98,
    )
    fig.tight_layout(rect=[0, 0.03, 1, 0.96])
    fig.savefig(OUTPUT_DIR / "02_normalization_comparison.png", dpi=200)
    plt.close(fig)
    logger.info("Saved: 02_normalization_comparison.png")

    # Log comparison insights
    logger.info("\nNormalization Comparison:")
    logger.info(f"  Rank-based correlation: {corr_rank:.3f} ({quality_rank})")
    logger.info(f"  Min-max correlation:    {corr_minmax:.3f} ({quality_minmax})")
    logger.info(f"  Difference: {abs(corr_rank - corr_minmax):.3f}")
    if abs(corr_rank - corr_minmax) < 0.05:
        logger.info("  → Normalizations show similar patterns")
    else:
        logger.info("  → Normalizations reveal different structures!")


def visualize_basic_metrics(
    user_vector: Tuple[int, ...], seed: Optional[int] = None
) -> None:
    """Generate basic metric space visualizations."""
    if seed is not None:
        np.random.seed(seed)

    _validate_user_vector(user_vector)

    strategy = OptimizationMetricsRankStrategy()
    strategy._validate_vector(user_vector, len(user_vector))

    l1_distances, leontief_ratios, vector_pool = _vector_pool_metrics(
        strategy, user_vector
    )
    logger.info(
        "Vector pool size: %d (requested %d)",
        len(vector_pool),
        strategy.POOL_SIZE,
    )

    _ensure_output_dir()
    _plot_absolute_values(l1_distances, leontief_ratios, user_vector)

    l1_norm, leontief_norm, _ = _compute_rank_metrics(l1_distances, leontief_ratios)
    l1_minmax, leo_minmax = _compute_minmax_metrics(l1_distances, leontief_ratios)
    _plot_normalization_comparison(
        l1_norm, leontief_norm, l1_minmax, leo_minmax, user_vector
    )


# ============================================================================
# MODE 2: PAIR SELECTION ANALYSIS WITH QUALITY METRICS
# ============================================================================


def _find_pairs_with_metadata(
    strategy: OptimizationMetricsRankStrategy,
    vector_pool: List[tuple],
    l1_distances: np.ndarray,
    leontief_ratios: np.ndarray,
    l1_norm: np.ndarray,
    leontief_norm: np.ndarray,
    discrepancies: np.ndarray,
) -> Dict[int, List[Tuple[int, int, dict]]]:
    """Find pairs at each relaxation level and return full metadata."""
    # DYNAMIC INITIALIZATION: Creates buckets for 1..N levels based on strategy config
    num_levels = len(strategy.RELAXATION_LEVELS)
    pairs_by_level = {i: [] for i in range(1, num_levels + 1)}

    used_indices = set()

    for level_idx, (epsilon, balance_tol) in enumerate(strategy.RELAXATION_LEVELS, 1):
        type_a_indices = np.where(discrepancies > epsilon)[0]
        type_b_indices = np.where(discrepancies < -epsilon)[0]

        type_a_available = [i for i in type_a_indices if i not in used_indices]
        type_b_available = [i for i in type_b_indices if i not in used_indices]

        for a_idx in type_a_available:
            a_disc = discrepancies[a_idx]

            for b_idx in type_b_available:
                if b_idx in used_indices:
                    continue

                b_disc = discrepancies[b_idx]

                if abs(b_disc) > 0.001:
                    ratio = abs(a_disc) / abs(b_disc)
                else:
                    ratio = float("inf")

                if 1 / balance_tol <= ratio <= balance_tol:
                    # Compute pair quality metrics
                    l1_sep = abs(l1_distances[a_idx] - l1_distances[b_idx])
                    leo_sep = abs(leontief_ratios[a_idx] - leontief_ratios[b_idx])

                    metadata = {
                        "a_idx": a_idx,
                        "b_idx": b_idx,
                        "a_disc": a_disc,
                        "b_disc": b_disc,
                        "balance_ratio": ratio,
                        "l1_separation": l1_sep,
                        "leo_separation": leo_sep,
                    }

                    pairs_by_level[level_idx].append((a_idx, b_idx, metadata))
                    used_indices.add(a_idx)
                    used_indices.add(b_idx)
                    break

    return pairs_by_level


def _plot_pair_quality_dashboard(
    pairs_by_level: Dict[int, List[Tuple[int, int, dict]]],
    l1_norm: np.ndarray,
    leontief_norm: np.ndarray,
    user_vector: Tuple[int, ...],
    strategy: OptimizationMetricsRankStrategy,
) -> None:
    """Comprehensive pair quality analysis dashboard."""
    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(3, 3, hspace=0.35, wspace=0.3)

    # Extract all pairs and metadata
    all_pairs = []
    all_metadata = []
    level_labels = []

    # Get sorted levels present in the data
    present_levels = sorted(pairs_by_level.keys())

    for level in present_levels:
        pairs = pairs_by_level[level]
        for _, _, metadata in pairs:
            all_pairs.append((metadata["a_idx"], metadata["b_idx"]))
            all_metadata.append(metadata)
            level_labels.append(level)

    if len(all_pairs) == 0:
        logger.warning("No pairs found for quality analysis!")
        return

    # Expanded colors and names for up to 5 levels
    colors = {
        1: "#e74c3c",  # Red
        2: "#f39c12",  # Orange
        3: "#3498db",  # Blue
        4: "#9b59b6",  # Purple
        5: "#95a5a6",  # Gray (Safety Net)
        6: "#34495e",  # Extra fallback
    }
    level_names = {
        1: "Strict",
        2: "Moderate",
        3: "Loose",
        4: "Minimal",
        5: "Safety Net",
    }

    # PLOT 1: Relaxation Level Usage (TOP LEFT)
    ax1 = fig.add_subplot(gs[0, 0])
    level_counts = {lvl: 0 for lvl in present_levels}
    for level in level_labels:
        level_counts[level] += 1

    ax1.set_xlabel("Relaxation Level", fontsize=10)
    ax1.set_ylabel("Number of Pairs", fontsize=10)
    ax1.set_title(
        "Pair Distribution by Relaxation Level", fontsize=11, fontweight="bold"
    )
    ax1.set_xticks(present_levels)
    ax1.set_xticklabels(
        [f"L{i}\n{level_names.get(i, '?')}" for i in present_levels], fontsize=8
    )
    ax1.grid(True, axis="y", alpha=0.3)

    # Add percentage labels on bars
    total_pairs = sum(level_counts.values())
    for i, (level, count) in enumerate(level_counts.items()):
        if count > 0:
            pct = count / total_pairs * 100
            ax1.text(
                level,
                count,
                f"{count}\n({pct:.0f}%)",
                ha="center",
                va="bottom",
                fontsize=9,
                fontweight="bold",
            )

    # PLOT 2: Balance Ratio Distribution (TOP CENTER)
    ax2 = fig.add_subplot(gs[0, 1])
    balance_ratios = [m["balance_ratio"] for m in all_metadata]
    ax2.hist(balance_ratios, bins=15, edgecolor="black", alpha=0.7, color="#95a5a6")

    # Add reference lines for tolerance levels
    for level, (epsilon, tol) in enumerate(strategy.RELAXATION_LEVELS, 1):
        ax2.axvline(
            tol,
            color=colors.get(level, "black"),
            linestyle="--",
            linewidth=1.5,
            alpha=0.7,
            label=f"L{level} limit: {tol}",
        )

    ax2.set_xlabel("Balance Ratio (|disc_A| / |disc_B|)", fontsize=10)
    ax2.set_ylabel("Frequency", fontsize=10)
    ax2.set_title("Balance Ratio Distribution", fontsize=11, fontweight="bold")
    # Legend might be too crowded if we have 5 levels, simplify if needed
    if len(present_levels) <= 4:
        ax2.legend(fontsize=8, loc="upper right")
    ax2.grid(True, alpha=0.3)

    # PLOT 3: Metric Separation Scatter (TOP RIGHT)
    ax3 = fig.add_subplot(gs[0, 2])
    l1_seps = [m["l1_separation"] for m in all_metadata]
    leo_seps = [m["leo_separation"] for m in all_metadata]

    for level in present_levels:
        level_mask = [lbl == level for lbl in level_labels]
        if any(level_mask):
            ax3.scatter(
                [l1_seps[i] for i in range(len(l1_seps)) if level_mask[i]],
                [leo_seps[i] for i in range(len(leo_seps)) if level_mask[i]],
                s=60,
                alpha=0.7,
                c=colors.get(level, "black"),
                edgecolors="black",
                linewidth=0.5,
                label=f"Level {level}",
                zorder=10 - level,
            )

    ax3.set_xlabel("L1 Separation (absolute)", fontsize=10)
    ax3.set_ylabel("Leontief Separation (absolute)", fontsize=10)
    ax3.set_title(
        "Pair Metric Separations\n(Both should be large)",
        fontsize=11,
        fontweight="bold",
    )
    ax3.legend(fontsize=8, loc="lower right")
    ax3.grid(True, alpha=0.3)

    # PLOT 4-7: Pairs in Rank Space by Level (MIDDLE & BOTTOM ROWS)
    # The grid only has space for 4 specific level plots (indices 1,0 to 2,1).
    # We will plot the first 4 levels found.
    plot_slots = [(1, 0), (1, 1), (2, 0), (2, 1)]

    for i, level in enumerate(present_levels[:4]):
        row, col = plot_slots[i]
        ax = fig.add_subplot(gs[row, col])

        # Get strategy parameters safely
        if level <= len(strategy.RELAXATION_LEVELS):
            epsilon, balance_tol = strategy.RELAXATION_LEVELS[level - 1]
        else:
            epsilon, balance_tol = 0.0, 0.0

        # Plot all vectors in gray
        ax.scatter(l1_norm, leontief_norm, s=8, alpha=0.15, c="gray", edgecolors="none")

        # Highlight epsilon boundaries
        type_a_mask = (l1_norm - leontief_norm) > epsilon
        type_b_mask = (l1_norm - leontief_norm) < -epsilon

        ax.scatter(
            l1_norm[type_a_mask],
            leontief_norm[type_a_mask],
            s=15,
            alpha=0.3,
            c="lightblue",
            edgecolors="none",
            label=f"Type A (disc>{epsilon})",
        )
        ax.scatter(
            l1_norm[type_b_mask],
            leontief_norm[type_b_mask],
            s=15,
            alpha=0.3,
            c="lightgreen",
            edgecolors="none",
            label=f"Type B (disc<-{epsilon})",
        )

        # Draw selected pairs for this level
        level_pairs = [(m["a_idx"], m["b_idx"]) for _, _, m in pairs_by_level[level]]
        for a_idx, b_idx in level_pairs:
            ax.plot(
                [l1_norm[a_idx], l1_norm[b_idx]],
                [leontief_norm[a_idx], leontief_norm[b_idx]],
                color=colors.get(level, "black"),
                alpha=0.7,
                linewidth=2,
                zorder=3,
            )
            ax.scatter(
                [l1_norm[a_idx], l1_norm[b_idx]],
                [leontief_norm[a_idx], leontief_norm[b_idx]],
                s=70,
                c=colors.get(level, "black"),
                edgecolors="black",
                linewidths=1,
                zorder=4,
            )

        # Diagonal reference
        ax.plot([0, 1], [0, 1], "k--", alpha=0.2, linewidth=1)

        ax.set_xlim(-0.05, 1.05)
        ax.set_ylim(-0.05, 1.05)
        ax.set_xlabel("L1 rank", fontsize=9)
        ax.set_ylabel("Leontief rank", fontsize=9)
        ax.set_title(
            f"Level {level}: {level_names.get(level, 'Unknown')}\n"
            f"ε={epsilon}, tol={balance_tol} | Pairs: {len(level_pairs)}",
            fontsize=10,
            fontweight="bold",
        )
        ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.3)
        if len(level_pairs) > 0:
            ax.legend(fontsize=7, loc="upper right")

    # PLOT 8: Vector Utilization Analysis (BOTTOM RIGHT)
    ax8 = fig.add_subplot(gs[2, 2])

    pool_size = len(l1_norm)
    vectors_used = len(set([idx for pair in all_pairs for idx in pair]))
    utilization_pct = vectors_used / pool_size * 100

    categories = ["Used in\nPairs", "Unused"]
    values = [vectors_used, pool_size - vectors_used]
    colors_util = ["#2ecc71", "#95a5a6"]

    wedges, texts, autotexts = ax8.pie(
        values,
        labels=categories,
        colors=colors_util,
        autopct="%1.1f%%",
        startangle=90,
        textprops={"fontsize": 10, "fontweight": "bold"},
    )
    ax8.set_title(
        f"Vector Pool Utilization\n"
        f"{vectors_used}/{pool_size} vectors used ({utilization_pct:.1f}%)",
        fontsize=10,
        fontweight="bold",
    )

    if utilization_pct > 50:
        status = "⚠ HIGH - Consider increasing POOL_SIZE"
        color_status = "orange"
    elif utilization_pct > 30:
        status = "⚠ MODERATE - Monitor pool size"
        color_status = "yellow"
    else:
        status = "✓ GOOD - Sufficient selectivity"
        color_status = "lightgreen"

    ax8.text(
        0,
        -1.3,
        status,
        ha="center",
        fontsize=9,
        bbox=dict(boxstyle="round", facecolor=color_status, alpha=0.7),
        transform=ax8.transData,
    )

    fig.suptitle(
        f"Pair Quality Dashboard\n"
        f"User Vector: {user_vector} | Total Pairs: {len(all_pairs)}",
        fontsize=14,
        fontweight="bold",
        y=0.98,
    )

    fig.savefig(OUTPUT_DIR / "03_pair_quality_dashboard.png", dpi=200)
    plt.close(fig)
    logger.info("Saved: 03_pair_quality_dashboard.png")


def visualize_pair_selection(
    user_vector: Tuple[int, ...], seed: Optional[int] = None
) -> None:
    """Generate pair selection analysis with quality metrics."""
    if seed is not None:
        np.random.seed(seed)

    _validate_user_vector(user_vector)

    strategy = OptimizationMetricsRankStrategy()
    strategy._validate_vector(user_vector, len(user_vector))

    l1_distances, leontief_ratios, vector_pool = _vector_pool_metrics(
        strategy, user_vector
    )
    l1_norm, leontief_norm, discrepancies = _compute_rank_metrics(
        l1_distances, leontief_ratios
    )

    pairs_by_level = _find_pairs_with_metadata(
        strategy,
        list(vector_pool),
        l1_distances,
        leontief_ratios,
        l1_norm,
        leontief_norm,
        discrepancies,
    )

    total_pairs = sum(len(pairs) for pairs in pairs_by_level.values())
    pool_size = len(vector_pool)
    vectors_used = len(
        set(
            [
                idx
                for level_pairs in pairs_by_level.values()
                for idx_a, idx_b, _ in level_pairs
                for idx in [idx_a, idx_b]
            ]
        )
    )
    utilization = vectors_used / pool_size * 100

    logger.info(f"\n{'='*60}")
    logger.info("PAIR SELECTION ANALYSIS")
    logger.info(f"{'='*60}")
    logger.info(f"Total pairs found: {total_pairs}")
    logger.info(f"Vector utilization: {utilization:.1f}% ({vectors_used}/{pool_size})")

    if utilization > 50:
        logger.warning("⚠ HIGH UTILIZATION - Consider increasing POOL_SIZE")
    elif utilization > 30:
        logger.warning("⚠ MODERATE UTILIZATION - Monitor pool size")
    else:
        logger.info("✓ Good utilization - sufficient selectivity")

    logger.info("\nPairs by relaxation level:")
    for level, pairs in pairs_by_level.items():
        pct = len(pairs) / total_pairs * 100 if total_pairs > 0 else 0
        epsilon, tol = strategy.RELAXATION_LEVELS[level - 1]
        logger.info(
            f"  Level {level} (ε={epsilon}, tol={tol}): "
            f"{len(pairs)} pairs ({pct:.1f}%)"
        )

        if level >= 3 and pct > 40:
            logger.warning("    ⚠ Heavy reliance on loose constraints!")

    # Compute quality metrics
    all_metadata = [m for pairs in pairs_by_level.values() for _, _, m in pairs]
    if all_metadata:
        balance_ratios = [m["balance_ratio"] for m in all_metadata]
        l1_seps = [m["l1_separation"] for m in all_metadata]
        leo_seps = [m["leo_separation"] for m in all_metadata]

        logger.info("\nPair quality metrics:")
        logger.info(
            f"  Balance ratio - Mean: {np.mean(balance_ratios):.2f}, "
            f"Max: {np.max(balance_ratios):.2f}"
        )
        logger.info(f"  L1 separation - Mean: {np.mean(l1_seps):.1f}")
        logger.info(f"  Leontief separation - Mean: {np.mean(leo_seps):.3f}")

        high_imbalance = sum(1 for r in balance_ratios if r > 3.0)
        if high_imbalance > 0:
            logger.warning(f"  ⚠ {high_imbalance} pairs have balance ratio >3.0")

    _ensure_output_dir()
    _plot_pair_quality_dashboard(
        pairs_by_level, l1_norm, leontief_norm, user_vector, strategy
    )


# ============================================================================
# MODE 3: SIMPLEX COVERAGE VALIDATION
# ============================================================================


def _plot_simplex_coverage(
    vector_pool: Sequence[tuple], user_vector: Tuple[int, ...]
) -> None:
    """Validate uniform simplex sampling with multiple diagnostics."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    vector_array = np.array(vector_pool)
    n_components = vector_array.shape[1]

    # Plot 1: Maximum component distribution
    ax1 = axes[0, 0]
    max_components = vector_array.max(axis=1)
    ax1.hist(max_components, bins=20, edgecolor="black", alpha=0.7, color="#3498db")
    ax1.axvline(
        max_components.mean(),
        color="red",
        linestyle="--",
        linewidth=2,
        label=f"Mean: {max_components.mean():.1f}",
    )
    ax1.set_xlabel("Maximum component value", fontsize=10)
    ax1.set_ylabel("Frequency", fontsize=10)
    ax1.set_title("Max Component Distribution\n(uniform = relatively flat)")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Plot 2: Minimum component distribution
    ax2 = axes[0, 1]
    min_components = vector_array.min(axis=1)
    ax2.hist(min_components, bins=20, edgecolor="black", alpha=0.7, color="#e74c3c")
    ax2.axvline(
        min_components.mean(),
        color="red",
        linestyle="--",
        linewidth=2,
        label=f"Mean: {min_components.mean():.1f}",
    )
    ax2.set_xlabel("Minimum component value", fontsize=10)
    ax2.set_ylabel("Frequency", fontsize=10)
    ax2.set_title("Min Component Distribution")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # Plot 3: Per-component distribution
    ax3 = axes[1, 0]
    positions = np.arange(n_components)
    box_data = [vector_array[:, i] for i in range(n_components)]
    ax3.boxplot(
        box_data,
        positions=positions,
        widths=0.6,
        patch_artist=True,
        boxprops=dict(facecolor="#95a5a6", alpha=0.7),
    )
    ax3.set_xlabel("Component index", fontsize=10)
    ax3.set_ylabel("Value", fontsize=10)
    ax3.set_title("Per-Component Value Distribution")
    ax3.set_xticks(positions)
    ax3.grid(True, alpha=0.3, axis="y")

    # Plot 4: Entropy/uniformity measure
    ax4 = axes[1, 1]
    # Calculate entropy for each vector (higher = more uniform)
    entropies = []
    for vec in vector_pool:
        vec_array = np.array(vec) / 100.0  # Normalize to probabilities
        vec_array = vec_array[vec_array > 0]  # Remove zeros
        entropy = -np.sum(vec_array * np.log(vec_array + 1e-10))
        entropies.append(entropy)

    ax4.hist(entropies, bins=20, edgecolor="black", alpha=0.7, color="#f39c12")
    max_entropy = np.log(n_components)
    ax4.axvline(
        max_entropy,
        color="red",
        linestyle="--",
        linewidth=2,
        label=f"Max possible: {max_entropy:.2f}",
    )
    ax4.set_xlabel("Vector entropy", fontsize=10)
    ax4.set_ylabel("Frequency", fontsize=10)
    ax4.set_title(
        "Allocation Uniformity (Shannon Entropy)\n" "(higher = more evenly distributed)"
    )
    ax4.legend()
    ax4.grid(True, alpha=0.3)

    fig.suptitle(
        f"Simplex Coverage Analysis (Sticks Method Validation)\n"
        f"User Vector: {user_vector} | Pool Size: {len(vector_pool)}",
        fontsize=13,
        y=0.995,
    )
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "04_simplex_coverage_validation.png", dpi=200)
    plt.close(fig)
    logger.info("Saved: 04_simplex_coverage_validation.png")

    # Log statistics
    logger.info("Simplex Coverage Statistics:")
    logger.info(f"  Max component mean: {max_components.mean():.2f}")
    logger.info(f"  Min component mean: {min_components.mean():.2f}")
    logger.info(
        f"  Mean entropy: {np.mean(entropies):.3f} "
        f"(max possible: {max_entropy:.3f})"
    )
    logger.info(
        f"  Entropy/Max ratio: {np.mean(entropies)/max_entropy:.3f} "
        f"(closer to 1.0 = more uniform)"
    )


def _validate_user_vector(user_vector: Tuple[int, ...]) -> None:
    """
    Validate user vector meets strategy requirements.

    Raises:
        ValueError: If vector is invalid
    """
    # Check sum equals 100
    if sum(user_vector) != 100:
        raise ValueError(
            f"Invalid user vector {user_vector}: "
            f"Components must sum to 100 (sums to {sum(user_vector)})"
        )

    # Check at least 2 positive dimensions
    positive_dims = sum(1 for v in user_vector if v > 0)
    if positive_dims < 2:
        raise ValueError(
            f"Invalid user vector {user_vector}: "
            f"Must have at least 2 positive dimensions (has {positive_dims}). "
            f"Single-dimension vectors create degenerate trade-offs."
        )

    # Check all values are multiples of 5
    non_multiples = [v for v in user_vector if v % 5 != 0]
    if non_multiples:
        raise ValueError(
            f"Invalid user vector {user_vector}: "
            f"All components must be multiples of 5. "
            f"Found non-multiples: {non_multiples}"
        )

    # Warning for extreme allocations
    max_component = max(user_vector)
    if max_component > 90:
        logger.warning(
            f"User vector {user_vector} has extreme allocation "
            f"(max component: {max_component}%). "
            f"This may produce high metric correlation and limited trade-offs."
        )


def visualize_simplex_coverage(
    user_vector: Tuple[int, ...], seed: Optional[int] = None
) -> None:
    """Generate simplex coverage validation plots."""
    if seed is not None:
        np.random.seed(seed)

    _validate_user_vector(user_vector)

    strategy = OptimizationMetricsRankStrategy()
    strategy._validate_vector(user_vector, len(user_vector))

    _, _, vector_pool = _vector_pool_metrics(strategy, user_vector)

    _ensure_output_dir()
    _plot_simplex_coverage(vector_pool, user_vector)


# ============================================================================
# MODE 4: MULTI-VECTOR COMPARISON
# ============================================================================


def _plot_multi_vector_comparison(
    test_vectors: List[Tuple[Tuple[int, ...], str]], seed: Optional[int]
) -> None:
    """Compare metric patterns across different user vector types."""
    if seed is not None:
        np.random.seed(seed)

    n_vectors = len(test_vectors)
    fig, axes = plt.subplots(n_vectors, 2, figsize=(14, 4 * n_vectors), squeeze=False)

    strategy = OptimizationMetricsRankStrategy()
    summary_stats = []

    for idx, (user_vector, description) in enumerate(test_vectors):
        # Validate vector
        try:
            _validate_user_vector(user_vector)
        except ValueError as e:
            logger.warning(f"Skipping invalid vector {user_vector}: {e}")
            # Clear the axes for this row
            for ax in axes[idx]:
                ax.text(
                    0.5,
                    0.5,
                    f"INVALID VECTOR\n{user_vector}\n{str(e)}",
                    ha="center",
                    va="center",
                    transform=ax.transAxes,
                    fontsize=10,
                    color="red",
                )
                ax.set_xticks([])
                ax.set_yticks([])
            continue

        # Use consistent seed for each vector
        if seed is not None:
            np.random.seed(seed + idx)

        l1_distances, leontief_ratios, vector_pool = _vector_pool_metrics(
            strategy, user_vector
        )
        l1_norm, leontief_norm, discrepancies = _compute_rank_metrics(
            l1_distances, leontief_ratios
        )

        # Quick pair generation check
        pairs_by_level = _find_pairs_with_metadata(
            strategy,
            list(vector_pool),
            l1_distances,
            leontief_ratios,
            l1_norm,
            leontief_norm,
            discrepancies,
        )
        total_pairs = sum(len(pairs) for pairs in pairs_by_level.values())
        level_4_pairs = len(pairs_by_level[4])
        level_4_pct = (level_4_pairs / total_pairs * 100) if total_pairs > 0 else 0

        # Absolute space (with negative L1)
        ax_abs = axes[idx, 0]
        ax_abs.scatter(
            -l1_distances,  # Negated for intuitive direction
            leontief_ratios,
            s=12,
            alpha=0.5,
            c="#1f77b4",
            edgecolors="none",
        )
        ax_abs.set_xlabel(
            "Negative L1 distance (higher = better)",
            fontsize=10,
        )
        ax_abs.set_ylabel(
            "Leontief ratio (higher = better)",
            fontsize=10,
        )
        ax_abs.set_title(
            f"{description}\n{user_vector} - Absolute",
            fontsize=11,
        )
        ax_abs.grid(True, linestyle="--", linewidth=0.5, alpha=0.3)

        # Rank-normalized space
        ax_rank = axes[idx, 1]
        ax_rank.scatter(
            l1_norm,
            leontief_norm,
            s=12,
            alpha=0.5,
            c="#ff7f0e",
            edgecolors="none",
        )
        ax_rank.plot([0, 1], [0, 1], "k--", alpha=0.3, linewidth=1)
        ax_rank.set_xlim(-0.05, 1.05)
        ax_rank.set_ylim(-0.05, 1.05)
        ax_rank.set_xlabel("L1 rank", fontsize=10)
        ax_rank.set_ylabel("Leontief rank", fontsize=10)
        ax_rank.set_title(
            f"{description}\n{user_vector} - Rank-Normalized", fontsize=11
        )
        ax_rank.grid(True, linestyle="--", linewidth=0.5, alpha=0.3)

        # Add correlation with quality assessment
        corr = np.corrcoef(l1_norm, leontief_norm)[0, 1]
        if corr < 0.65:
            quality = "Excellent"
            color = "lightgreen"
        elif corr < 0.80:
            quality = "Good"
            color = "wheat"
        else:
            quality = "Limited"
            color = "lightcoral"

        info_text = f"ρ = {corr:.3f}\n{quality}\n{total_pairs} pairs"
        if level_4_pct > 40:
            info_text += f"\n⚠ L4: {level_4_pct:.0f}%"
            color = "orange"

        ax_rank.text(
            0.02,
            0.98,
            info_text,
            transform=ax_rank.transAxes,
            fontsize=9,
            verticalalignment="top",
            bbox=dict(boxstyle="round", facecolor=color, alpha=0.6),
        )

        summary_stats.append(
            {
                "vector": user_vector,
                "description": description,
                "correlation": corr,
                "quality": quality,
                "total_pairs": total_pairs,
                "level_4_pct": level_4_pct,
            }
        )

    fig.suptitle(
        "Multi-Vector Comparison: How User Vector Affects Strategy Performance\n"
        "(Lower correlation + more Level 1-2 pairs = better)",
        fontsize=14,
        y=0.998,
    )
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "05_multi_vector_comparison.png", dpi=200)
    plt.close(fig)
    logger.info("Saved: 05_multi_vector_comparison.png")

    # Log summary insights
    logger.info("\n" + "=" * 60)
    logger.info("MULTI-VECTOR COMPARISON SUMMARY")
    logger.info("=" * 60)
    for stat in summary_stats:
        logger.info(f"\n{stat['description']}: {stat['vector']}")
        logger.info(f"  Correlation: {stat['correlation']:.3f} ({stat['quality']})")
        logger.info(f"  Total pairs: {stat['total_pairs']}")
        logger.info(f"  Level 4 usage: {stat['level_4_pct']:.1f}%")
        if stat["correlation"] > 0.85:
            logger.warning("  ⚠ HIGH CORRELATION - Strategy may be ineffective")
        if stat["level_4_pct"] > 50:
            logger.warning("  ⚠ HEAVY RELIANCE ON LOOSE CONSTRAINTS")


def visualize_multi_vector_comparison(seed: Optional[int] = None) -> None:
    """Generate comparison across different user vector types."""
    # Only include VALID test vectors (>=2 positive dims, multiples of 5)
    test_vectors = [
        ((35, 35, 30), "Balanced 3D"),
        ((40, 30, 30), "Most Frequent OIA 3D"),
        ((70, 20, 10), "Skewed 3D"),
        ((60, 30, 10), "Moderately Skewed 3D"),
        ((40, 30, 30), "Slight Imbalance 3D"),
        ((50, 25, 25), "2:1:1 Ratio 3D"),
        ((25, 25, 25, 25), "Balanced 4D"),
        ((60, 20, 10, 10), "Skewed 4D"),
        ((45, 25, 20, 10), "Mixed Skew 4D"),
    ]

    _ensure_output_dir()
    _plot_multi_vector_comparison(test_vectors, seed)


# ============================================================================
# MAIN EXECUTION
# ============================================================================


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )
    args = _parse_args()
    user_vector = tuple(args.user_vector)

    logger.info(f"Running visualization mode: {args.mode}")
    logger.info(f"User vector: {user_vector}")
    if args.seed is not None:
        logger.info(f"Random seed: {args.seed}")

    try:
        if args.mode in {"basic", "all"}:
            logger.info("→ Generating basic metric visualizations")
            visualize_basic_metrics(user_vector, args.seed)

        if args.mode in {"pairs", "all"}:
            logger.info("→ Generating pair selection dashboard")
            visualize_pair_selection(user_vector, args.seed)

        if args.mode in {"coverage", "all"}:
            logger.info("→ Validating simplex coverage")
            visualize_simplex_coverage(user_vector, args.seed)

        if args.mode in {"comparison", "all"}:
            logger.info("→ Running multi-vector comparison")
            visualize_multi_vector_comparison(args.seed)

    except ValueError as exc:
        logger.error(f"Visualization failed: {exc}")
        raise


if __name__ == "__main__":
    main()
