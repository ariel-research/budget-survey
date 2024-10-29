import json
import logging
import os
from typing import Dict, List, Tuple

import pandas as pd

from utils.generate_examples import sum_of_differences

logger = logging.getLogger(__name__)


def get_latest_csv_files(directory: str = "data") -> Dict[str, str]:
    """
    Get the latest CSV files from the specified directory.

    Args:
        directory (str): The directory to search for CSV files.

    Returns:
        Dict[str, str]: A dictionary of the latest CSV files.
    """
    csv_files = {
        f: os.path.getmtime(os.path.join(directory, f))
        for f in os.listdir(directory)
        if f.endswith(".csv")
    }

    return (
        {
            "responses": "all_completed_survey_responses.csv",
            "summary": "summarize_stats_by_survey.csv",
            "optimization": "survey_optimization_stats.csv",
        }
        if all(
            f in csv_files
            for f in [
                "all_completed_survey_responses.csv",
                "summarize_stats_by_survey.csv",
                "survey_optimization_stats.csv",
            ]
        )
        else {}
    )


def load_data(directory: str = "data") -> Dict[str, pd.DataFrame]:
    """
    Load data from CSV files into pandas DataFrames.

    Args:
        directory (str): The directory containing the CSV files.

    Returns:
        Dict[str, pd.DataFrame]: A dictionary of loaded DataFrames.
    """
    files = get_latest_csv_files(directory)
    return {
        key: pd.read_csv(os.path.join(directory, filename))
        for key, filename in files.items()
    }


def is_sum_optimized(
    optimal_vector: Tuple[int, ...],
    option_1: Tuple[int, ...],
    option_2: Tuple[int, ...],
    user_choice: int,
) -> bool:
    """
    Determine if the user's choice optimized for sum difference.

    Args:
    optimal_vector: The user's ideal budget allocation.
    option_1: First option presented to the user.
    option_2: Second option presented to the user.
    user_choice: The option chosen by the user (1 or 2).

    Returns:
    True if the user's choice optimized for sum difference, False otherwise (ratio optimized).
    """
    if user_choice not in [1, 2]:
        raise ValueError("user_choice must be either 1 or 2")

    sum_diff_1 = sum_of_differences(optimal_vector, option_1)
    sum_diff_2 = sum_of_differences(optimal_vector, option_2)

    optimal_choice = 1 if sum_diff_1 > sum_diff_2 else 2

    return optimal_choice == user_choice


def process_survey_responses(raw_results: List[Dict]) -> List[Dict]:
    """
    Processes raw survey response data into a structured format.

    Args:
        raw_results: A list of dictionaries containing raw survey response data.

    Returns:
        A list of dictionaries containing processed survey response data.
    """
    processed_results = []
    current_response = {}

    for row in raw_results:
        if (
            not current_response
            or current_response["survey_response_id"] != row["survey_response_id"]
        ):
            if current_response:
                processed_results.append(current_response)
            current_response = {
                "survey_response_id": row["survey_response_id"],
                "user_id": row["user_id"],
                "survey_id": row["survey_id"],
                "optimal_allocation": json.loads(row["optimal_allocation"]),
                "completed": row["completed"],
                "response_created_at": row["response_created_at"],
                "comparisons": [],
            }
        current_response["comparisons"].append(
            {
                "pair_number": row["pair_number"],
                "option_1": json.loads(row["option_1"]),
                "option_2": json.loads(row["option_2"]),
                "user_choice": row["user_choice"],
            }
        )

    if current_response:
        processed_results.append(current_response)

    logger.info(f"Processed {len(processed_results)} survey responses")
    return processed_results


def calculate_optimization_stats(row: pd.Series) -> pd.Series:
    """
    Calculate optimization statistics for a single survey response.

    Args:
        row (pd.Series): A row from the survey response DataFrame.

    Returns:
        pd.Series: Statistics including number of answers, sum and ratio optimized choices, and overall result.
    """
    sum_optimized_choices = 0
    ratio_optimized_choices = 0
    total_comparisons = len(row["comparisons"])

    for comparison in row["comparisons"]:
        if is_sum_optimized(
            row["optimal_allocation"],
            comparison["option_1"],
            comparison["option_2"],
            comparison["user_choice"],
        ):
            sum_optimized_choices += 1
        else:
            ratio_optimized_choices += 1

    result = (
        "sum"
        if sum_optimized_choices > ratio_optimized_choices
        else "ratio" if sum_optimized_choices < ratio_optimized_choices else "equal"
    )

    return pd.Series(
        {
            "num_of_answers": total_comparisons,
            "sum_optimized": sum_optimized_choices,
            "ratio_optimized": ratio_optimized_choices,
            "result": result,
        }
    )
