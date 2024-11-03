import base64
import io

import matplotlib

# Use non-interactive backend to avoid GUI issues
matplotlib.use("Agg")
import logging
from typing import Dict, List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.colors import ListedColormap

logger = logging.getLogger(__name__)


def save_plot_to_base64(fig: plt.Figure) -> str:
    """
    Save a matplotlib figure to a base64 encoded string.

    This utility function is used to convert matplotlib figures into a format
    that can be easily embedded in HTML documents. Base64 encoding allows the image
    to be included directly in the HTML without requiring separate image files.

    Args:
        fig (plt.Figure): The matplotlib figure to save.

    Returns:
        str: Base64 encoded string of the figure.
    """
    # Create an in-memory bytes buffer
    img_buffer = io.BytesIO()
    # Save the figure to the buffer in PNG format
    fig.savefig(img_buffer, format="png", dpi=300, bbox_inches="tight")
    # Reset buffer position to the beginning
    img_buffer.seek(0)
    # Convert buffer contents to base64 and then to UTF-8 string
    img_str = base64.b64encode(img_buffer.getvalue()).decode("utf-8")
    # Close the figure to free up memory
    plt.close(fig)
    return img_str


def validate_dataframe(df: pd.DataFrame, required_columns: list) -> None:
    """
    Validate that DataFrame has required columns.

    Args:
        df: DataFrame to validate
        required_columns: List of required column names

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
    Generate a bar chart comparing sum and ratio optimization answer percentages across surveys.

    Args:
        summary_stats (pd.DataFrame): The summary statistics DataFrame.

    Returns:
        str: Base64 encoded string of the chart image.
    """
    required_columns = [
        "survey_id",
        "sum_optimized_percentage",
        "ratio_optimized_percentage",
    ]
    validate_dataframe(summary_stats, required_columns)

    # Create figure and axis with a specific size
    fig, ax = plt.subplots(figsize=(12, 6))

    # Set a clean, grid-based style for the plot
    sns.set_style("whitegrid")

    # Filter out the "Total" row and extract relevant data
    survey_data = summary_stats[summary_stats["survey_id"] != "Total"]
    surveys = survey_data["survey_id"]
    sum_opt = survey_data["sum_optimized_percentage"]
    ratio_opt = survey_data["ratio_optimized_percentage"]

    # Set up x-axis range and bar width
    x = range(len(surveys))
    width = 0.35

    # Create bars for sum and ratio optimization
    ax.bar(
        [i - width / 2 for i in x],
        sum_opt,
        width,
        label="Sum Optimization",
        color="#1f77b4",
        edgecolor="black",
    )
    ax.bar(
        [i + width / 2 for i in x],
        ratio_opt,
        width,
        label="Ratio Optimization",
        color="#2ca02c",
        edgecolor="black",
    )

    # Show left and bottom grid lines
    ax.yaxis.grid(True, linestyle="--", alpha=0.7)
    ax.xaxis.grid(False)

    # Set labels and title
    ax.set_xlabel("Survey ID", fontweight="bold")
    ax.set_ylabel("Percentage", fontweight="bold")
    ax.set_title(
        "Percentage of Sum vs Ratio Optimized Answers per Survey",
        fontsize=16,
        fontweight="bold",
        pad=20,
    )

    # Set x-axis ticks and labels
    ax.set_xticks(x)
    ax.set_xticklabels(surveys, ha="center")

    # Add value labels on top of each bar
    for i, v in enumerate(sum_opt):
        ax.text(i - width / 2, v, f"{v:.1f}%", ha="center", va="bottom")
    for i, v in enumerate(ratio_opt):
        ax.text(i + width / 2, v, f"{v:.1f}%", ha="center", va="bottom")

    # Add legend
    ax.legend(loc="upper right")

    # Adjust layout
    plt.tight_layout()

    return save_plot_to_base64(fig)


def visualize_user_survey_majority_choices(optimization_stats: pd.DataFrame) -> str:
    """
    Generate a color-coded matrix visualization showing each user's majority choice for each survey.

    This function creates a categorical data visualization where each cell represents a user's
    majority choice (sum, ratio, or equal) for a particular survey.

    Args:
        optimization_stats (pd.DataFrame): The optimization statistics DataFrame.

    Returns:
        str: Base64 encoded string of the heatmap image.
    """
    required_columns = ["survey_id", "user_id", "result"]
    validate_dataframe(optimization_stats, required_columns)

    # Pivot the data
    pivot_df = optimization_stats.pivot(
        index="user_id", columns="survey_id", values="result"
    )

    # Create a mapping for numeric encoding and colors
    color_map = {"sum": 0, "ratio": 1, "equal": 2, "missing": 3}
    colors = ["#4C72B0", "#55A868", "#CCB974", "lightgrey"]

    # Handle missing data and convert to numeric
    pivot_df = pivot_df.fillna("missing")
    # Maps each value in a column to its corresponding numeric value in color_map
    numeric_df = pivot_df.apply(lambda x: x.map(color_map))

    # Initialize the plot size based on the number of users
    fig, ax = plt.subplots(figsize=(10, max(6, len(pivot_df) * 0.5)))

    # Create custom colormap
    cmap = ListedColormap(colors)

    # Plot heatmap using imshow
    ax.imshow(numeric_df, cmap=cmap, aspect="auto", interpolation="nearest")

    # Remove grid lines
    ax.grid(False)

    # Add text annotations
    # 'i': row index (user_id) | 'j': column index (survey_id) | 'val': value (result)
    for (i, j), val in np.ndenumerate(pivot_df.values):
        text_color = "black" if val != "missing" else "grey"
        # Adds text (the value) to the center of each rectangle
        ax.text(j, i, val, ha="center", va="center", fontsize=10, color=text_color)

    # Customize the plot
    ax.set_title(
        "User Majority Choice (Sum/Ratio/Equal) by Survey",
        fontsize=16,
        fontweight="bold",
        pad=20,
    )
    ax.set_xlabel("Survey ID", fontsize=12, fontweight="bold")
    ax.set_ylabel("User ID", fontsize=12, fontweight="bold")
    ax.set_xticks(np.arange(pivot_df.shape[1]))  # The number of columns (surveys)
    ax.set_yticks(np.arange(pivot_df.shape[0]))  # The number of rows (users)
    ax.set_xticklabels(pivot_df.columns)
    ax.set_yticklabels(pivot_df.index)

    # Adjust plot limits
    ax.set_xlim(-0.5, len(pivot_df.columns) - 0.5)
    ax.set_ylim(len(pivot_df) - 0.5, -0.5)

    # Create a custom legend
    legend_elements = [plt.Rectangle((0, 0), 1, 1, facecolor=color) for color in colors]
    ax.legend(
        legend_elements,
        color_map.keys(),
        loc="upper center",
        bbox_to_anchor=(0.5, -0.15),
        ncol=4,
        title="Preference",
    )

    # Adjust layout
    plt.tight_layout()

    return save_plot_to_base64(fig)


def visualize_overall_majority_choice_distribution(summary_stats: pd.DataFrame) -> str:
    """
    Generate a pie chart showing the distribution of majority choices across all surveys.

    Args:
        summary_stats (pd.DataFrame): The summary statistics DataFrame.

    Returns:
        str: Base64 encoded string of the pie chart image.
    """
    required_columns = ["sum_count", "ratio_count", "equal_count"]
    validate_dataframe(summary_stats, required_columns)

    total_row = summary_stats.loc[summary_stats["survey_id"] == "Total"].iloc[0]

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.pie(
        [total_row["sum_count"], total_row["ratio_count"], total_row["equal_count"]],
        labels=["Sum", "Ratio", "Equal"],
        autopct="%1.1f%%",
        colors=["#4C72B0", "#55A868", "#CCB974"],
    )

    ax.set_title(
        "Distribution of Majority Choices Across All User-Survey Combinations",
        fontsize=16,
        fontweight="bold",
        pad=20,
    )

    return save_plot_to_base64(fig)


def visualize_total_answer_percentage_distribution(summary_stats: pd.DataFrame) -> str:
    """
    Generate a pie chart showing the overall percentage distribution of sum vs ratio optimization answers.

    Args:
        summary_stats (pd.DataFrame): The summary statistics DataFrame.

    Returns:
        str: Base64 encoded string of the pie chart image.
    """
    required_columns = ["sum_optimized_percentage", "ratio_optimized_percentage"]
    validate_dataframe(summary_stats, required_columns)

    total_row = summary_stats.loc[summary_stats["survey_id"] == "Total"].iloc[0]
    sum_percentage = total_row["sum_optimized_percentage"]
    ratio_percentage = total_row["ratio_optimized_percentage"]

    fig, ax = plt.subplots(figsize=(8, 8))

    ax.pie(
        [sum_percentage, ratio_percentage],
        labels=["Sum Optimization", "Ratio Optimization"],
        autopct="%1.1f%%",
        colors=["#4C72B0", "#55A868"],
        startangle=90,
    )

    ax.set_title(
        "Overall Distribution of Sum vs Ratio Optimized Answers",
        fontsize=16,
        fontweight="bold",
        pad=20,
    )

    return save_plot_to_base64(fig)


def visualize_user_choices(query_results: List[Dict]) -> str:
    """
    Creates a clean visualization showing user choices across surveys.
    """
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

        # Create figure without extra space
        fig = plt.figure(figsize=(18, fig_height), constrained_layout=True)

        # Create a single subplot that fills the figure
        ax = fig.add_subplot(111)
        ax.axis("off")

        # Define column labels
        column_labels = [
            "User ID",
            "Survey ID",
            "Choices (Q1-Q10)",
            "Option 1\nTotal",
            "Option 2\nTotal",
            "Option 1\nPercentage",
        ]

        # Create and style the table
        table = ax.table(
            cellText=stats_data,
            colLabels=column_labels,
            loc="center",
            cellLoc="center",
            bbox=[0, 0, 0.95, 1],
        )

        # Style improvements
        table.auto_set_font_size(False)
        table.set_fontsize(12)

        # Optimized column widths
        col_widths = [0.17, 0.11, 0.25, 0.11, 0.11, 0.11]
        for idx, width in enumerate(col_widths):
            for cell in table._cells:
                if cell[1] == idx:
                    table._cells[cell].set_width(width)

        # Increased row height scaling
        table.scale(1.0, 2.4)

        # Enhanced header styling
        for j, cell in enumerate(
            table._cells[(0, j)] for j in range(len(column_labels))
        ):
            cell.set_facecolor("#2C3E50")
            cell.set_text_props(color="white", weight="bold", fontsize=13)

        # Enhanced row styling
        for i in range(len(stats_data)):
            # Style choices column
            cell = table._cells[(i + 1, 2)]
            cell.set_text_props(family="monospace", fontsize=13)

            # Alternating row colors
            for j in range(len(column_labels)):
                cell = table._cells[(i + 1, j)]
                if i % 2 == 0:
                    cell.set_facecolor("#EDF2F7")
                else:
                    cell.set_facecolor("#FFFFFF")

        # Use figure suptitle for the main title with minimal spacing
        plt.suptitle(
            "Detailed Survey Choices Analysis",
            y=0.99,  # Move title very close to top
            fontsize=18,
            weight="bold",
        )

        # Add note at the bottom with minimal spacing
        fig.text(
            0.05,
            0.01,
            "Note: Choices show selected option (1 or 2) for each question Q1-Q10",
            fontsize=11,
            style="italic",
            color="#666666",
        )

        # Ensure tight layout and save
        plt.tight_layout(
            rect=[0, 0.02, 1, 0.98]
        )  # Adjust layout while preserving small space for title and note

        return save_plot_to_base64(fig)

    except Exception as e:
        logger.error(f"Error creating visualization: {str(e)}", exc_info=True)
        logger.exception("Full traceback:")
        return ""
