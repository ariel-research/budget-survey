import json
import logging
import os
from typing import Dict, List, Tuple

import pandas as pd

from utils.generate_examples import sum_of_differences

logger = logging.getLogger(__name__)


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


def save_dataframe_to_csv(df: pd.DataFrame, csv_filename: str) -> None:
    """
    Save a pandas DataFrame to a CSV file.

    Args:
        df: A pandas DataFrame to be saved.
        csv_filename: The filename (including path) where the CSV will be saved.

    Raises:
        ValueError: If the DataFrame is empty.

    Example:
        >>> df = pd.DataFrame({'name': ['Alice', 'Bob'], 'age': [30, 25]})
        >>> save_dataframe_to_csv(df, 'output.csv')
    """
    if df.empty:
        logger.error("Input DataFrame is empty")
        raise ValueError("Input DataFrame is empty")

    try:
        ensure_directory_exists(csv_filename)
        logger.info(f"Writing DataFrame to {csv_filename}")
        df.to_csv(csv_filename, index=False)
        logger.info(f"Successfully wrote data to {csv_filename}")
    except Exception as e:
        logger.error(f"Error occurred while saving DataFrame to CSV: {e}")
        raise


def ensure_directory_exists(file_path: str) -> None:
    """
    Ensure that the directory for the given file path exists.
    If it doesn't exist, create it.

    Args:
        file_path: The full path of the file, including filename.
    """
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
        logger.info(f"Created directory: {directory}")
