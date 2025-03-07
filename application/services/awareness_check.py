"""Module for handling survey awareness check generation."""

import logging
import random
from typing import Any, Dict, List, Set, Tuple

logger = logging.getLogger(__name__)


def _get_valid_modifications(
    vector: List[int], num_of_subjects: int
) -> List[Tuple[int, int, int]]:
    """
    Find all valid index pairs for vector modification.

    Args:
        vector: The original vector
        num_of_subjects: Number of subjects

    Returns:
        List of tuples (inc_idx, dec_idx, amount) representing valid modifications

    Raises:
        ValueError: If vector length doesn't match num_of_subjects
    """
    if len(vector) != num_of_subjects:
        raise ValueError(
            f"Vector length {len(vector)} does not match number of subjects {num_of_subjects}"
        )

    valid_mods = []

    for inc_idx in range(num_of_subjects):
        for dec_idx in range(num_of_subjects):
            if inc_idx != dec_idx:
                for amount in [5, 10, 15]:  # Try different modification amounts
                    if vector[inc_idx] + amount <= 95 and vector[dec_idx] - amount >= 5:
                        valid_mods.append((inc_idx, dec_idx, amount))

    return valid_mods


def generate_awareness_questions(
    user_vector: List[int], num_of_subjects: int
) -> List[Dict[str, Any]]:
    """
    Generate two different awareness test questions.
    First question's correct answer is option 1, second question's correct answer is option 2.

    Args:
        user_vector: The user's original budget allocation vector
        num_of_subjects: The number of subjects in the budget allocation

    Returns:
        List of two different awareness questions

    Raises:
        ValueError: If unable to generate two different questions or if input validation fails
    """
    logger.debug(f"Generating two awareness questions for user vector: {user_vector}")

    # Validate inputs
    if len(user_vector) != num_of_subjects:
        raise ValueError(
            f"Vector length {len(user_vector)} does not match number of subjects {num_of_subjects}"
        )

    if sum(user_vector) != 100:
        raise ValueError(f"Vector sum must be 100, got {sum(user_vector)}")

    if any(v < 0 or v > 95 for v in user_vector):
        raise ValueError("Vector values must be between 0 and 95")

    if any(v < 5 for v in user_vector if v != 0):
        raise ValueError("Non-zero vector values must be at least 5")

    # Get all valid modifications
    valid_mods = _get_valid_modifications(user_vector, num_of_subjects)
    if not valid_mods:
        raise ValueError("No valid modifications possible for this vector")

    # Shuffle modifications to ensure randomness
    random.shuffle(valid_mods)

    used_vectors: Set[Tuple[int, ...]] = set()
    questions = []

    # Try to generate two different questions
    for inc_idx, dec_idx, amount in valid_mods:
        test_vector = user_vector.copy()
        test_vector[inc_idx] += amount
        test_vector[dec_idx] -= amount

        vector_tuple = tuple(test_vector)
        if vector_tuple not in used_vectors:
            used_vectors.add(vector_tuple)

            # First question: correct answer is option 1
            if len(questions) == 0:
                questions.append(
                    {
                        "option1": user_vector,  # Original vector is option 1
                        "option2": test_vector,
                        "correct_answer": 1,  # Correct answer is option 1
                    }
                )
            # Second question: correct answer is option 2
            else:
                questions.append(
                    {
                        "option1": test_vector,
                        "option2": user_vector,  # Original vector is option 2
                        "correct_answer": 2,  # Correct answer is option 2
                    }
                )

            if len(questions) == 2:
                logger.debug("Successfully generated two different awareness questions")
                return questions

    logger.error("Failed to generate two different awareness questions")
    raise ValueError("Could not generate two different awareness questions")


def generate_awareness_check(
    user_vector: List[int], num_of_subjects: int
) -> Dict[str, Any]:
    """
    Generate a single awareness check question.

    This function is maintained for backward compatibility.
    """
    questions = generate_awareness_questions(user_vector, num_of_subjects)
    return questions[0]
