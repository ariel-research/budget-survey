import json
import logging

from utils.generate_examples import sum_of_differences

logger = logging.getLogger(__name__)


def is_sum_optimized(
    optimal_vector: tuple, option_1: tuple, option_2: tuple, user_choice: int
) -> bool:
    """
    Determine if the user's choice optimized for sum difference.

    Args:
    optimal_vector (tuple): The user's ideal budget allocation.
    option_1 (tuple): First option presented to the user.
    option_2 (tuple): Second option presented to the user.
    user_choice (int): The option chosen by the user (1 or 2).

    Returns:
    bool: True if the user's choice optimized for sum difference, False otherwise.

    Examples:
    >>> is_sum_optimized((50, 30, 20), (40, 35, 25), (45, 30, 25), 2)
    False
    >>> is_sum_optimized((50, 30, 20), (40, 35, 25), (45, 30, 25), 1)
    True
    """
    if user_choice not in [1, 2]:
        raise ValueError("user_choice must be either 1 or 2")

    sum_diff_1 = sum_of_differences(optimal_vector, option_1)
    sum_diff_2 = sum_of_differences(optimal_vector, option_2)

    optimal_choice = 1 if sum_diff_1 > sum_diff_2 else 2

    return optimal_choice == user_choice


def process_survey_responses(raw_results):
    """
    Processes raw survey response data into a structured format.

    Args:
        raw_results (list): A list of dictionaries containing raw survey response data.

    Returns:
        list: A list of dictionaries containing processed survey response data.
    """
    processed_results = []
    current_response = None

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
