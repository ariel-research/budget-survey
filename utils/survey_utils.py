import random
from typing import Any, Dict, List


def is_valid_vector(vector: List[int]) -> bool:
    """
    Check if the given vector is valid according to the survey rules.

    Parameters:
    vector (List[int]): A list of integers representing the budget allocation.

    Returns:
    bool: True if the vector is valid (sums to 100 and all elements are multiples of 5),
          False otherwise.

    Example:
    >>> is_valid_vector([30, 40, 30])
    True
    >>> is_valid_vector([33, 33, 34])
    False
    """
    return sum(vector) == 100 and all(v % 5 == 0 for v in vector)


def generate_awareness_check(
    user_vector: List[int], num_of_subjects: int
) -> Dict[str, Any]:
    """
    Generate an awareness check question based on the user's vector.

    Parameters:
    user_vector (List[int]): The user's original budget allocation vector.
    num_of_subjects (int): The number of subjects in the budget allocation.

    Returns:
    Dict[str, Any]: A dictionary containing:
        - 'option1': A randomly generated fake vector
        - 'option2': The user's original vector
        - 'correct_answer': Always 2, indicating that option2 is correct

    This function creates a fake vector different from the user's vector to use
    as a distractor in the awareness check question.

    Example:
    >>> generate_awareness_check([30, 40, 30], 3)
    {'option1': [35, 45, 20], 'option2': [30, 40, 30], 'correct_answer': 2}
    """
    while True:
        fake_vector = [random.choice(range(0, 101, 5)) for _ in range(num_of_subjects)]
        if sum(fake_vector) == 100 and fake_vector != user_vector:
            break

    return {"option1": fake_vector, "option2": user_vector, "correct_answer": 2}
