"""Module for handling survey awareness check generation."""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def generate_awareness_check(
    user_vector: List[int], num_of_subjects: int
) -> Dict[str, Any]:
    """
    Generate an awareness check question based on the user's vector.

    Args:
        user_vector (List[int]): The user's original budget allocation vector.
        num_of_subjects (int): The number of subjects in the budget allocation.

    Returns:
        Dict[str, Any]: A dictionary containing:
            - 'option1': A modified version of the user's vector
            - 'option2': The user's original vector
            - 'correct_answer': Always 2, indicating that option2 is correct

    This function creates a fake vector by modifying two elements of the user's vector
    by ±5, maintaining the sum of 100 and ensuring all values stay within [0-95].

    Example:
        >>> generate_awareness_check([30, 40, 30], 3)
        {'option1': [35, 35, 30], 'option2': [30, 40, 30], 'correct_answer': 2}
    """
    logger.debug(f"Generating awareness check for user vector: {user_vector}")

    # Create a copy to avoid modifying the original vector
    fake_vector = user_vector.copy()

    # Find indices where values can be increased (<=90) or decreased (>=5)
    valid_increase = [i for i in range(num_of_subjects) if fake_vector[i] <= 95]
    valid_decrease = [i for i in range(num_of_subjects) if fake_vector[i] >= 5]

    logger.debug(
        f"Valid indices for increase: {valid_increase}, decrease: {valid_decrease}"
    )

    # Systematically check each possible combination of increase/decrease indices
    for inc_idx in valid_increase:
        for dec_idx in valid_decrease:
            if inc_idx != dec_idx:
                test_vector = fake_vector.copy()
                test_vector[inc_idx] += 5
                test_vector[dec_idx] -= 5

                if test_vector != user_vector:
                    logger.debug(
                        f"Generated fake vector by increasing index {inc_idx} "
                        f"and decreasing index {dec_idx}: {test_vector}"
                    )
                    return {
                        "option1": test_vector,
                        "option2": user_vector,
                        "correct_answer": 2,
                    }

    logger.error(
        f"Could not generate valid fake vector. User vector: {user_vector}, "
        f"Valid increase indices: {valid_increase}, Valid decrease indices: {valid_decrease}"
    )
    raise ValueError(
        "Could not generate valid fake vector: no valid indices for modification"
    )
