import base64
from io import BytesIO

import matplotlib.pyplot as plt
import pandas as pd


def generate_visualization(summary_stats: pd.DataFrame) -> bytes:
    """
    Generate a visualization of sum vs ratio optimization.

    Args:
        summary_stats (pd.DataFrame): The summary statistics DataFrame.

    Returns:
        bytes: PNG image data of the visualization.
    """
    plt.figure(figsize=(12, 6))
    surveys = summary_stats[summary_stats["survey_id"] != "Total"]["survey_id"]
    sum_opt = summary_stats[summary_stats["survey_id"] != "Total"][
        "sum_optimized_percentage"
    ]
    ratio_opt = summary_stats[summary_stats["survey_id"] != "Total"][
        "ratio_optimized_percentage"
    ]

    x = range(len(surveys))
    plt.bar(
        [i - 0.2 for i in x],
        sum_opt,
        width=0.4,
        label="Sum Optimization",
        color="#4C72B0",
    )
    plt.bar(
        [i + 0.2 for i in x],
        ratio_opt,
        width=0.4,
        label="Ratio Optimization",
        color="#55A868",
    )

    plt.xlabel("Survey ID", fontsize=12)
    plt.ylabel("Percentage", fontsize=12)
    plt.title("Sum vs Ratio Optimization by Survey", fontsize=16)
    plt.xticks(x, surveys, fontsize=10)
    plt.yticks(fontsize=10)
    plt.legend(fontsize=10)
    plt.grid(axis="y", linestyle="--", alpha=0.7)

    img = BytesIO()
    plt.savefig(img, format="png", dpi=300, bbox_inches="tight")
    img.seek(0)
    return img.getvalue()


def encode_image_base64(image_data: bytes) -> str:
    """
    Encode image data as base64 string.

    Args:
        image_data (bytes): Raw image data.

    Returns:
        str: Base64 encoded image string.
    """
    return base64.b64encode(image_data).decode("utf-8")
