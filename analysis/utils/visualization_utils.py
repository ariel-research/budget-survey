import base64
import io
import logging
from typing import Any, Dict, List, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import ListedColormap

logger = logging.getLogger(__name__)


def get_chart_style() -> Dict[str, Dict[str, Any]]:
    """
    Return consistent style configuration for all charts.

    Returns:
        Dict[str, Dict[str, any]]: Dictionary containing style configurations for colors, fonts, and layout
    """
    return {
        "colors": {
            "primary": "#2563eb",  # Blue
            "secondary": "#16a34a",  # Green
            "tertiary": "#ca8a04",  # Yellow
            "background": "#ffffff",
            "grid": "#e5e7eb",
            "text": "#1f2937",
        },
        "fonts": {
            "title_size": 16,
            "label_size": 12,
            "tick_size": 10,
            "annotation_size": 9,
        },
        "layout": {"figure_dpi": 300, "title_pad": 20, "legend_space": 0.2},
    }


def apply_chart_style(fig: plt.Figure, ax: plt.Axes) -> None:
    """
    Apply consistent styling to charts.

    Args:
        fig (plt.Figure): Matplotlib figure object
        ax (plt.Axes): Matplotlib axes object
    """
    style = get_chart_style()

    # Set background colors
    fig.patch.set_facecolor(style["colors"]["background"])
    ax.set_facecolor(style["colors"]["background"])

    # Customize grid
    ax.grid(True, linestyle="--", alpha=0.3, color=style["colors"]["grid"])
    ax.set_axisbelow(True)

    # Style spines
    for spine in ax.spines.values():
        spine.set_color(style["colors"]["grid"])
        spine.set_linewidth(0.5)

    # Adjust fonts
    ax.title.set_fontsize(style["fonts"]["title_size"])
    ax.title.set_color(style["colors"]["text"])
    ax.xaxis.label.set_fontsize(style["fonts"]["label_size"])
    ax.yaxis.label.set_fontsize(style["fonts"]["label_size"])
    ax.tick_params(labelsize=style["fonts"]["tick_size"])


def save_plot_to_base64(fig: plt.Figure) -> str:
    """
    Save a matplotlib figure to a base64 encoded string.

    Args:
        fig (plt.Figure): The matplotlib figure to save.

    Returns:
        str: Base64 encoded string of the figure.
    """
    img_buffer = io.BytesIO()
    try:
        fig.savefig(img_buffer, format="png", dpi=300, bbox_inches="tight")
        img_buffer.seek(0)
        return base64.b64encode(img_buffer.getvalue()).decode("utf-8")
    finally:
        img_buffer.close()


def validate_dataframe(df: pd.DataFrame, required_columns: List[str]) -> None:
    """
    Validate that DataFrame has required columns.

    Args:
        df (pd.DataFrame): DataFrame to validate
        required_columns (List[str]): List of required column names

    Raises:
        ValueError: If DataFrame is empty or missing required columns
    """
    if df.empty:
        raise ValueError("Input DataFrame is empty")
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"DataFrame missing required columns: {missing_columns}")


def visualize_per_survey_answer_percentages(summary_stats: pd.DataFrame) -> str:
    """
    Generate a bar chart comparing sum and ratio optimization percentages across surveys.

    Args:
        summary_stats (pd.DataFrame): The summary statistics DataFrame.

    Returns:
        str: Base64 encoded string of the chart image.
    """
    logger.info("Generating per-survey answer percentages visualization")
    required_columns = [
        "survey_id",
        "sum_optimized_percentage",
        "ratio_optimized_percentage",
    ]
    validate_dataframe(summary_stats, required_columns)

    style = get_chart_style()
    fig, ax = plt.subplots(figsize=(12, 6))

    # Filter out the "Total" row and extract data
    survey_data = summary_stats[summary_stats["survey_id"] != "Total"]
    surveys = survey_data["survey_id"]
    sum_opt = survey_data["sum_optimized_percentage"]
    ratio_opt = survey_data["ratio_optimized_percentage"]

    x = range(len(surveys))
    width = 0.35

    # Create bars with enhanced styling
    bars1 = ax.bar(
        [i - width / 2 for i in x],
        sum_opt,
        width,
        label="Sum Optimization",
        color=style["colors"]["primary"],
        edgecolor=style["colors"]["text"],
        alpha=0.8,
    )
    bars2 = ax.bar(
        [i + width / 2 for i in x],
        ratio_opt,
        width,
        label="Ratio Optimization",
        color=style["colors"]["secondary"],
        edgecolor=style["colors"]["text"],
        alpha=0.8,
    )

    # Add value labels
    def add_value_labels(bars):
        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f"{height:.1f}%",
                ha="center",
                va="bottom",
                fontsize=style["fonts"]["annotation_size"],
            )

    add_value_labels(bars1)
    add_value_labels(bars2)

    # Customize the plot
    ax.set_xlabel("Survey ID", fontweight="bold")
    ax.set_ylabel("Percentage", fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(surveys)

    # Enhance legend
    ax.legend(loc="upper right", framealpha=0.9, edgecolor=style["colors"]["grid"])

    # Apply consistent styling
    apply_chart_style(fig, ax)

    return save_plot_to_base64(fig)


def visualize_user_survey_majority_choices(optimization_stats: pd.DataFrame) -> str:
    """
    Generate a color-coded matrix visualization showing each user's majority choice for each survey.

    Args:
        optimization_stats (pd.DataFrame): The optimization statistics DataFrame.

    Returns:
        str: Base64 encoded string of the heatmap image.
    """
    logger.info("Generating user survey majority choices visualization")
    required_columns = ["survey_id", "user_id", "result"]
    validate_dataframe(optimization_stats, required_columns)

    style = get_chart_style()

    # Pivot the data
    pivot_df = optimization_stats.pivot(
        index="user_id", columns="survey_id", values="result"
    )

    # Create mapping for colors using style colors
    color_map = {"sum": 0, "ratio": 1, "equal": 2, "missing": 3}
    colors = [
        style["colors"]["primary"],
        style["colors"]["secondary"],
        style["colors"]["tertiary"],
        style["colors"]["grid"],
    ]

    # Handle missing data
    pivot_df = pivot_df.fillna("missing")
    numeric_df = pivot_df.apply(lambda x: x.map(color_map))

    fig, ax = plt.subplots(figsize=(10, max(6, len(pivot_df) * 0.5)))
    cmap = ListedColormap(colors)

    # Create heatmap
    ax.imshow(numeric_df, cmap=cmap, aspect="auto", interpolation="nearest")

    # Add text annotations
    for i in range(len(pivot_df.index)):
        for j in range(len(pivot_df.columns)):
            val = pivot_df.iloc[i, j]
            text_color = "white" if val in ["sum", "ratio"] else "black"
            ax.text(
                j,
                i,
                val,
                ha="center",
                va="center",
                color=text_color,
                fontsize=style["fonts"]["annotation_size"],
            )

    # Customize the plot
    ax.set_xlabel("Survey ID", fontweight="bold")
    ax.set_ylabel("User ID", fontweight="bold")

    # Set and style ticks
    ax.set_xticks(np.arange(len(pivot_df.columns)))
    ax.set_yticks(np.arange(len(pivot_df.index)))
    ax.set_xticklabels(pivot_df.columns)
    ax.set_yticklabels(pivot_df.index)

    # Add legend
    legend_elements = [plt.Rectangle((0, 0), 1, 1, facecolor=color) for color in colors]
    ax.legend(
        legend_elements,
        color_map.keys(),
        loc="upper center",
        bbox_to_anchor=(0.5, -0.15),
        ncol=4,
        title="Preference Type",
    )

    # Apply consistent styling
    apply_chart_style(fig, ax)

    return save_plot_to_base64(fig)


def visualize_overall_majority_choice_distribution(summary_stats: pd.DataFrame) -> str:
    """
    Generate a pie chart showing the distribution of majority choices across all surveys.

    Args:
        summary_stats (pd.DataFrame): The summary statistics DataFrame.

    Returns:
        str: Base64 encoded string of the pie chart image.
    """
    logger.info("Generating overall majority choice distribution visualization")
    required_columns = ["sum_count", "ratio_count", "equal_count"]
    validate_dataframe(summary_stats, required_columns)

    style = get_chart_style()
    fig, ax = plt.subplots(figsize=(8, 8))

    # Get data from total row
    total_row = summary_stats.loc[summary_stats["survey_id"] == "Total"].iloc[0]
    values = [
        total_row["sum_count"],
        total_row["ratio_count"],
        total_row["equal_count"],
    ]
    labels = ["Sum", "Ratio", "Equal"]

    # Create pie chart with enhanced styling
    wedges, texts, autotexts = ax.pie(
        values,
        labels=labels,
        autopct="%1.1f%%",
        colors=[
            style["colors"]["primary"],
            style["colors"]["secondary"],
            style["colors"]["tertiary"],
        ],
        wedgeprops={"edgecolor": "white", "linewidth": 2},
    )

    # Style text elements
    plt.setp(autotexts, size=style["fonts"]["annotation_size"], weight="bold")
    plt.setp(texts, size=style["fonts"]["label_size"])

    # Apply consistent styling
    apply_chart_style(fig, ax)

    return save_plot_to_base64(fig)


def visualize_total_answer_percentage_distribution(summary_stats: pd.DataFrame) -> str:
    """
    Generate a pie chart showing the overall percentage distribution of sum vs ratio optimization answers.

    Args:
        summary_stats (pd.DataFrame): The summary statistics DataFrame.

    Returns:
        str: Base64 encoded string of the pie chart image.
    """
    logger.info("Generating total answer percentage distribution visualization")
    required_columns = ["sum_optimized_percentage", "ratio_optimized_percentage"]
    validate_dataframe(summary_stats, required_columns)

    style = get_chart_style()
    fig, ax = plt.subplots(figsize=(8, 8))

    # Get data from total row
    total_row = summary_stats.loc[summary_stats["survey_id"] == "Total"].iloc[0]
    values = [
        total_row["sum_optimized_percentage"],
        total_row["ratio_optimized_percentage"],
    ]
    labels = ["Sum Optimization", "Ratio Optimization"]

    # Create pie chart with enhanced styling
    wedges, texts, autotexts = ax.pie(
        values,
        labels=labels,
        autopct="%1.1f%%",
        colors=[style["colors"]["primary"], style["colors"]["secondary"]],
        wedgeprops={"edgecolor": "white", "linewidth": 2},
        startangle=90,
    )

    # Style text elements
    plt.setp(autotexts, size=style["fonts"]["annotation_size"], weight="bold")
    plt.setp(texts, size=style["fonts"]["label_size"])

    # Apply consistent styling
    apply_chart_style(fig, ax)

    return save_plot_to_base64(fig)


def visualize_user_choices(query_results: List[Dict]) -> str:
    """
    Create a detailed visualization of user choices across surveys.

    Args:
        query_results (List[Dict]): List of dictionaries containing user survey choices.

    Returns:
        str: Base64 encoded string of the visualization.
    """
    logger.info("Generating user choices visualization")

    try:
        if not query_results:
            logger.warning("No data available for visualization")
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.text(
                0.5,
                0.5,
                "No survey data available",
                ha="center",
                va="center",
                fontsize=14,
            )
            ax.axis("off")
            return save_plot_to_base64(fig)

        style = get_chart_style()

        # Process data
        user_survey_map = {}
        for row in query_results:
            key = (str(row["user_id"]), str(row["survey_id"]))
            if key not in user_survey_map:
                user_survey_map[key] = {
                    "choices": [0] * 10,
                    "total_opt1": 0,
                    "total_opt2": 0,
                }

            pair_idx = row["pair_number"] - 1
            choice = row["user_choice"]
            user_survey_map[key]["choices"][pair_idx] = choice
            if choice == 1:
                user_survey_map[key]["total_opt1"] += 1
            else:
                user_survey_map[key]["total_opt2"] += 1

        # Prepare data for table
        stats_data = []
        for (user_id, survey_id), data in user_survey_map.items():
            choices_str = " ".join([str(c) for c in data["choices"]])
            total_choices = data["total_opt1"] + data["total_opt2"]
            opt1_percentage = (
                (data["total_opt1"] / total_choices * 100) if total_choices > 0 else 0
            )

            stats_data.append(
                [
                    str(user_id),
                    str(survey_id),
                    choices_str,
                    str(data["total_opt1"]),
                    str(data["total_opt2"]),
                    f"{opt1_percentage:.1f}%",
                ]
            )

        # Create figure with optimized size
        rows = len(stats_data)
        fig_height = max(12, min(24, rows * 0.9))
        fig = plt.figure(figsize=(18, fig_height), constrained_layout=True)
        ax = fig.add_subplot(111)
        ax.axis("off")

        # Create and style the table
        column_labels = [
            "User ID",
            "Survey ID",
            "Choices (Q1-Q10)",
            "Option 1\nTotal",
            "Option 2\nTotal",
            "Option 1\nPercentage",
        ]

        table = ax.table(
            cellText=stats_data,
            colLabels=column_labels,
            loc="center",
            cellLoc="center",
            bbox=[0, 0, 0.95, 1],
        )

        # Style improvements
        table.auto_set_font_size(False)
        table.set_fontsize(10)

        # Optimized column widths based on content
        col_widths = [0.17, 0.11, 0.25, 0.11, 0.11, 0.11]
        for idx, width in enumerate(col_widths):
            for cell in table._cells:
                if cell[1] == idx:
                    table._cells[cell].set_width(width)

        # Enhanced row height scaling
        table.scale(1.0, 2.4)

        # Enhanced header styling
        style = get_chart_style()
        for j, cell in enumerate(
            table._cells[(0, j)] for j in range(len(column_labels))
        ):
            cell.set_facecolor(style["colors"]["primary"])
            cell.set_text_props(color="white", weight="bold", fontsize=11)

        # Enhanced row styling
        for i in range(len(stats_data)):
            # Style choices column
            cell = table._cells[(i + 1, 2)]
            cell.set_text_props(family="monospace", fontsize=10)

            # Alternating row colors
            for j in range(len(column_labels)):
                cell = table._cells[(i + 1, j)]
                if i % 2 == 0:
                    cell.set_facecolor("#f8f9fa")  # Light background for even rows
                else:
                    cell.set_facecolor("#ffffff")  # White background for odd rows

        # Add note at the bottom
        fig.text(
            0.05,
            0.01,
            "Note: Choices show selected option (1 or 2) for each question Q1-Q10",
            fontsize=style["fonts"]["annotation_size"],
            style="italic",
            color=style["colors"]["text"],
        )

        # Ensure tight layout
        plt.tight_layout(rect=[0, 0.02, 1, 0.98])

        return save_plot_to_base64(fig)

    except Exception as e:
        logger.error(f"Error creating visualization: {str(e)}", exc_info=True)
        logger.exception("Full traceback:")
        return ""


def create_choice_distribution_chart(
    distribution: Dict[str, int], labels: Tuple[str, str]
) -> str:
    """Create bar chart showing distribution of choices."""
    style = get_chart_style()
    fig, ax = plt.subplots(figsize=(10, 6))

    # Create bars
    x = range(len(labels))
    heights = [distribution["option_1"], distribution["option_2"]]

    bars = ax.bar(
        x, heights, color=[style["colors"]["primary"], style["colors"]["secondary"]]
    )

    # Customize chart
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Number of Choices")

    # Add value labels
    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            height,
            f"{height}",
            ha="center",
            va="bottom",
        )

    apply_chart_style(fig, ax)

    return save_plot_to_base64(fig)
