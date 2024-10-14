import base64
import io

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.colors import ListedColormap


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


def visualize_per_survey_answer_percentages(summary_stats: pd.DataFrame) -> str:
    """
    Generate a bar chart comparing sum and ratio optimization answer percentages across surveys.

    Args:
        summary_stats (pd.DataFrame): The summary statistics DataFrame.

    Returns:
        str: Base64 encoded string of the chart image.
    """
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
