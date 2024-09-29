from utils.generate_examples import sum_of_differences


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
