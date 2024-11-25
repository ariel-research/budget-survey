"""
Handles generation of budget allocation vectors and pairs for survey comparisons.

This module provides functionality for:
- Generating random budget allocation vectors
- Calculating optimization metrics between vectors
- Creating pairs of vectors for survey comparisons
- Generating awareness check questions
"""

import logging
import random
from typing import Any, Dict, List, Set, Tuple

import numpy as np

logger = logging.getLogger(__name__)


def create_random_vector(size: int = 3) -> tuple:
    """
    Generate a random vector of integers that sums to 100, with each element
    being a multiple of 5.

    Args:
        size: Number of elements in the vector. Default is 3.

    Returns:
        tuple: A tuple containing `size` integers that sum to 100

    Example:
    >>> vector = create_random_vector(3)
    >>> int(sum(vector)) == 100  # Convert np.int to int
    True
    >>> all(int(v) % 5 == 0 for v in vector)  # Convert np.int to int
    True
    >>> len(vector)
    3
    """
    vector = np.random.rand(size)
    vector = np.floor(vector / vector.sum() * 20).astype(int)
    # Adjust the last element to ensure the sum is exactly 20
    vector[-1] = 20 - vector[:-1].sum()
    np.random.shuffle(vector)
    # Multiply each value in the vector by 5
    vector = vector * 5
    return tuple(vector)


def sum_of_differences(user_vector: tuple, comparison_vector: tuple) -> int:
    """
    Calculate total absolute differences between two vectors.

    Args:
        user_vector: Reference vector
        comparison_vector: Vector to compare against

    Returns:
        int: Sum of absolute differences

    Example:
        >>> sum_of_differences((10, 20, 30), (15, 25, 35))
        15
    """
    return int(np.sum(np.abs(np.array(user_vector) - np.array(comparison_vector))))


def minimal_ratio(user_vector: tuple, comparison_vector: tuple) -> float:
    """
    Calculate the minimal ratio between corresponding elements.

    Args:
        user_vector: Reference vector
        comparison_vector: Vector to compare against

    Returns:
        float: Minimum ratio between corresponding elements

    Example:
        >>> minimal_ratio((50, 30, 20), (30, 40, 30))
        0.6
    """
    ratios = np.array(comparison_vector) / np.array(user_vector)
    return float(np.min(ratios[np.isfinite(ratios)]))  # Handle division by zero


def calculate_optimization_metrics(
    user_vector: tuple, v1: tuple, v2: tuple
) -> Tuple[float, float, float, float]:
    """
    Calculate optimization metrics for a pair of vectors against the user vector.

    Args:
        user_vector: Reference vector
        v1, v2: Vectors to compare

    Returns:
        Tuple of (sum_diff_1, sum_diff_2, ratio_1, ratio_2)
    """
    s1 = sum_of_differences(user_vector, v1)
    s2 = sum_of_differences(user_vector, v2)
    r1 = minimal_ratio(user_vector, v1)
    r2 = minimal_ratio(user_vector, v2)
    return s1, s2, r1, r2


def is_valid_pair(metrics: Tuple[float, float, float, float]) -> bool:
    """
    Check if pair has complementary optimization properties. A valid pair is one where
    neither vector dominates the other in both metrics (sum and ratio).

    A pair is considered to have complementary properties when:
    1. First vector has better sum (lower sum_diff) but worse ratio (lower ratio), OR
    2. Second vector has better sum but worse ratio

    This ensures that users must make a trade-off between optimizing for sum of
    differences or minimal ratio.

    Args:
        metrics: Tuple of (sum_diff_1, sum_diff_2, ratio_1, ratio_2)
                where sum_diff_* represents the sum of differences from ideal vector
                and ratio_* represents the minimal ratio to ideal vector

    Returns:
        bool: True if pair has valid optimization trade-off

    Example:
        # Case 1: v1 better in sum, worse in ratio (valid pair)
        >>> is_valid_pair((30, 40, 0.6, 0.8))  # s1 < s2, r1 < r2
        True

        # Case 2: v2 better in sum, worse in ratio (valid pair)
        >>> is_valid_pair((50, 30, 0.8, 0.5))  # s1 > s2, r1 > r2
        True

        # Case 3: v1 better in both metrics (invalid pair)
        >>> is_valid_pair((30, 40, 0.8, 0.6))  # s1 < s2, r1 > r2
        False

        # Case 4: v2 better in both metrics (invalid pair)
        >>> is_valid_pair((50, 30, 0.5, 0.8))  # s1 > s2, r1 < r2
        False
    """
    s1, s2, r1, r2 = metrics
    return (s1 < s2 and r1 < r2) or (s2 < s1 and r2 < r1)


def generate_vector_pool(size: int, vector_size: int) -> Set[tuple]:
    """
    Generate a pool of unique random vectors.

    Args:
        size: Number of vectors to generate
        vector_size: Size of each vector

    Returns:
        Set of unique vectors
    """
    vector_pool = set()
    attempts = 0
    max_attempts = size * 10

    while len(vector_pool) < size and attempts < max_attempts:
        vector = create_random_vector(vector_size)
        vector_pool.add(vector)
        attempts += 1

    logger.debug(
        f"Generated vector pool of size {len(vector_pool)} "
        f"(requested: {size}, attempts: {attempts})"
    )
    return vector_pool


def generate_survey_pairs(
    user_vector: tuple, n: int = 10, vector_size: int = 3
) -> List[Tuple[tuple, tuple]]:
    """
    Generate pairs of budget allocation vectors for survey comparisons.

    Each pair contains two vectors where one is better in terms of sum_of_differences
    while the other is better in terms of minimal_ratio.

    Args:
        user_vector: The user's ideal budget allocation
        n: Number of pairs to generate (default: 10)
        vector_size: Size of each vector (default: 3)

    Returns:
        List of n pairs, where each pair contains two vectors with
        complementary optimization properties

    Raises:
        ValueError: If unable to generate enough valid pairs
    """
    POOL_MULTIPLIER = 4  # Size of vector pool relative to needed pairs
    MAX_ATTEMPTS = 3  # Maximum recursion depth

    def _generate_pairs(attempt: int = 0) -> List[Tuple[tuple, tuple]]:
        """Helper function with recursion tracking."""
        if attempt >= MAX_ATTEMPTS:
            logger.error(
                f"Failed to generate {n} valid pairs after {MAX_ATTEMPTS} attempts"
            )
            raise ValueError(
                f"Failed to generate {n} valid pairs after {MAX_ATTEMPTS} attempts"
            )

        # Generate vector pool
        pool_size = n * POOL_MULTIPLIER * (attempt + 1)
        logger.info(
            f"Attempting to generate pairs (attempt {attempt + 1}/{MAX_ATTEMPTS}, "
            f"pool size: {pool_size})"
        )
        vector_pool = generate_vector_pool(pool_size, vector_size)

        # Find valid pairs
        valid_pairs = []
        vectors = list(vector_pool)

        for i in range(len(vectors)):
            for j in range(i + 1, len(vectors)):
                v1, v2 = vectors[i], vectors[j]
                metrics = calculate_optimization_metrics(user_vector, v1, v2)

                if is_valid_pair(metrics):
                    valid_pairs.append((v1, v2))

        logger.debug(f"Found {len(valid_pairs)} valid pairs")

        if len(valid_pairs) < n:
            logger.warning(
                f"Insufficient valid pairs (found: {len(valid_pairs)}, "
                f"needed: {n}). Retrying with larger pool."
            )
            return _generate_pairs(attempt + 1)

        selected_pairs = random.sample(valid_pairs, n)
        logger.info(f"Successfully generated {n} diverse pairs")
        return selected_pairs

    try:
        return _generate_pairs()
    except ValueError as e:
        logger.error(f"Pair generation failed: {str(e)}")
        raise


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


if __name__ == "__main__":
    import doctest

    doctest.testmod()
