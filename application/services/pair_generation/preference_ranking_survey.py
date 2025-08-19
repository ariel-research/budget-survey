"""Implementation of the Preference Ranking Survey strategy."""

import logging
from typing import Dict, List, Tuple

import numpy as np

from application.exceptions import UnsuitableForStrategyError
from application.services.pair_generation.base import PairGenerationStrategy
from application.translations import get_translation

logger = logging.getLogger(__name__)


class PreferenceRankingSurveyStrategy(PairGenerationStrategy):
    """
    Strategy testing user preference order through forced-ranking methodology.

    This strategy generates 12 pairs organized into 4 forced-ranking questions
    to uncover stable user priorities among 3 budget subjects. Each question
    presents 3 options derived from the user's ideal vector plus a base
    difference vector and its 2 cyclic shifts.

    Algorithm:
    1. Calculate two magnitudes: X1 = max(1, round(0.2 * min(user_vector))),
       X2 = max(1, round(0.4 * min(user_vector)))
    2. Create two base difference vectors (both sum to zero):
       - Positive Vector: (+2X, -X, -X)
       - Negative Vector: (-2X, +X, +X)
    3. Generate 4 questions by combining magnitudes (X1, X2) with vectors
    4. For each question, create 3 options using base vector and 2 shifts
    5. Convert 3-option rankings to pairs: 3 pairs per question = 12 pairs

    The core hypothesis is that user's underlying preference order will be
    consistently revealed across all questions.
    """

    def generate_pairs(
        self, user_vector: tuple, n: int = 12, vector_size: int = 3
    ) -> List[Dict[str, tuple]]:
        """
        Generate 12 pairs testing preference order through forced rankings.

        Args:
            user_vector: User's ideal budget allocation.
            n: Number of pairs to generate (always 12 for this strategy).
            vector_size: Size of each allocation vector (must be 3).

        Returns:
            List of 12 dictionaries containing comparison pairs.

        Raises:
            UnsuitableForStrategyError: If user vector contains zero values.
            ValueError: If vector_size is not 3 or pair generation fails.
        """
        if vector_size != 3:
            raise ValueError(
                "PreferenceRankingSurveyStrategy only supports vector_size=3."
            )

        if 0 in user_vector:
            logger.info(f"User vector {user_vector} contains zero values, unsuitable.")
            raise UnsuitableForStrategyError(
                "User vector contains zero values and is unsuitable for "
                "this strategy."
            )

        self._validate_vector(user_vector, vector_size)

        pairs = []
        user_array = np.array(user_vector)

        # Calculate magnitudes based on minimum value
        min_value = min(user_vector)
        x1 = max(1, round(0.2 * min_value))
        x2 = max(1, round(0.4 * min_value))

        logger.info(f"Calculated magnitudes: X1={x1}, X2={x2} (min_value={min_value})")

        # Define the 4 questions: 2 magnitudes × 2 vector types
        questions = [
            (x1, "positive", "X1_positive"),
            (x1, "negative", "X1_negative"),
            (x2, "positive", "X2_positive"),
            (x2, "negative", "X2_negative"),
        ]

        for q_idx, (magnitude, vector_type, question_label) in enumerate(questions, 1):
            # Create base difference vector
            if vector_type == "positive":
                base_diff = np.array([2 * magnitude, -magnitude, -magnitude])
            else:  # negative
                base_diff = np.array([-2 * magnitude, magnitude, magnitude])

            # Generate 3 options using base vector and its cyclic shifts
            option_a = user_array + base_diff
            option_b = user_array + self._rotate_vector(base_diff, 1)
            option_c = user_array + self._rotate_vector(base_diff, 2)

            # Validate all options are within valid range
            options = [("A", option_a), ("B", option_b), ("C", option_c)]
            for opt_name, option in options:
                if not (
                    np.all(option >= 0)
                    and np.all(option <= 100)
                    and np.sum(option) == 100
                ):
                    logger.warning(
                        f"Invalid option {opt_name} in question {q_idx}: "
                        f"{option.tolist()}"
                    )
                    raise ValueError(
                        f"Generated invalid option {opt_name} for " f"question {q_idx}"
                    )

            # Convert options to tuples
            option_a_tuple = tuple(option_a.tolist())
            option_b_tuple = tuple(option_b.tolist())
            option_c_tuple = tuple(option_c.tolist())

            # Generate 3 pairs from the 3 options (A vs B, A vs C, B vs C)
            question_pairs = [
                {
                    "Option A": option_a_tuple,
                    "Option B": option_b_tuple,
                    "question_number": q_idx,
                    "question_label": question_label,
                    "magnitude": magnitude,
                    "vector_type": vector_type,
                    "pair_type": "A_vs_B",
                    "option_a_differences": base_diff.tolist(),
                    "option_b_differences": self._rotate_vector(base_diff, 1).tolist(),
                },
                {
                    "Option A": option_a_tuple,
                    "Option C": option_c_tuple,
                    "question_number": q_idx,
                    "question_label": question_label,
                    "magnitude": magnitude,
                    "vector_type": vector_type,
                    "pair_type": "A_vs_C",
                    "option_a_differences": base_diff.tolist(),
                    "option_c_differences": self._rotate_vector(base_diff, 2).tolist(),
                },
                {
                    "Option B": option_b_tuple,
                    "Option C": option_c_tuple,
                    "question_number": q_idx,
                    "question_label": question_label,
                    "magnitude": magnitude,
                    "vector_type": vector_type,
                    "pair_type": "B_vs_C",
                    "option_b_differences": self._rotate_vector(base_diff, 1).tolist(),
                    "option_c_differences": self._rotate_vector(base_diff, 2).tolist(),
                },
            ]

            pairs.extend(question_pairs)

        logger.info(
            f"Generated {len(pairs)} pairs from {len(questions)} "
            f"forced-ranking questions"
        )
        self._log_pairs(pairs)
        return pairs

    def generate_ranking_questions(
        self, user_vector: tuple, vector_size: int = 3
    ) -> List[Dict]:
        """
        Generate 4 ranking questions for frontend display.

        This method generates the same 4 questions that would be converted into
        12 pairs, but returns them in a format suitable for ranking display.

        Args:
            user_vector: User's ideal budget allocation.
            vector_size: Size of each allocation vector (must be 3).

        Returns:
            List of 4 ranking questions, each with options A, B, C to be
            ranked.

        Raises:
            ValueError: If vector_size is not 3.
            UnsuitableForStrategyError: If user_vector contains zero values.
        """
        # Use the same validation as generate_pairs
        if vector_size != 3:
            raise ValueError("Preference ranking strategy requires vector_size=3")

        self._validate_vector(user_vector, vector_size)

        user_array = np.array(user_vector)

        # Calculate magnitudes (same as in generate_pairs)
        min_value = min(user_vector)
        x1 = max(1, round(0.2 * min_value))
        x2 = max(1, round(0.4 * min_value))

        logger.info(
            f"Generating 4 ranking questions: X1={x1}, X2={x2} "
            f"(min_value={min_value})"
        )

        questions = []
        question_configs = [
            (1, x1, "positive", "X1_positive"),
            (2, x1, "negative", "X1_negative"),
            (3, x2, "positive", "X2_positive"),
            (4, x2, "negative", "X2_negative"),
        ]

        for question_num, magnitude, vector_type, question_label in question_configs:
            # Generate base difference vector
            if vector_type == "positive":
                base_diff = np.array([2 * magnitude, -magnitude, -magnitude])
            else:  # negative
                base_diff = np.array([-2 * magnitude, magnitude, magnitude])

            # Generate three options using cyclic shifts
            option_a = user_array + base_diff
            option_b = user_array + self._rotate_vector(base_diff, 1)
            option_c = user_array + self._rotate_vector(base_diff, 2)

            # Validate all options
            for opt_name, option in [
                ("A", option_a),
                ("B", option_b),
                ("C", option_c),
            ]:
                if not all(0 <= val <= 100 for val in option):
                    raise UnsuitableForStrategyError(
                        f"Option {opt_name} in question {question_num} has "
                        f"invalid values: {option}"
                    )

            # Convert to tuples
            option_a = tuple(option_a)
            option_b = tuple(option_b)
            option_c = tuple(option_c)

            question = {
                "question_number": question_num,
                "question_label": question_label,
                "magnitude": magnitude,
                "vector_type": vector_type,
                "option_a": option_a,
                "option_b": option_b,
                "option_c": option_c,
                "option_a_differences": tuple(base_diff),
                "option_b_differences": tuple(self._rotate_vector(base_diff, 1)),
                "option_c_differences": tuple(self._rotate_vector(base_diff, 2)),
            }

            questions.append(question)

            logger.debug(
                f"Question {question_num} ({question_label}): "
                f"A={option_a}, B={option_b}, C={option_c}"
            )

        return questions

    def is_ranking_based(self) -> bool:
        """
        Identify this strategy as ranking-based for special frontend handling.

        Returns:
            bool: True, indicating this strategy uses ranking questions instead
                  of pairwise comparisons for display.
        """
        return True

    def _rotate_vector(self, vector: np.ndarray, positions: int) -> np.ndarray:
        """
        Rotate a vector to the right by the specified number of positions.

        Args:
            vector: The numpy array to rotate.
            positions: Number of positions to rotate right.

        Returns:
            The rotated numpy array.
        """
        positions = positions % len(vector)
        if positions == 0:
            return vector.copy()
        return np.concatenate([vector[-positions:], vector[:-positions]])

    def get_strategy_name(self) -> str:
        """Return unique identifier for this strategy."""
        return "preference_ranking_survey"

    def get_option_labels(self) -> Tuple[str, str]:
        """Return labels for the two options being compared."""
        return (
            get_translation("option_a_label", "answers"),
            get_translation("option_b_label", "answers"),
        )

    def _get_metric_name(self, metric_type: str) -> str:
        """Get the display name for a metric type."""
        return f"Ranking {metric_type}"

    def get_table_columns(self) -> Dict[str, Dict]:
        """Get column definitions for the survey response breakdown table."""
        return {
            "option_a": {
                "name": get_translation("option_a_label", "answers"),
                "type": "percentage",
                "highlight": True,
            },
            "option_b": {
                "name": get_translation("option_b_label", "answers"),
                "type": "percentage",
                "highlight": True,
            },
        }

    def _log_pairs(self, pairs: List[Dict[str, tuple]]) -> None:
        """
        Log generated pairs with enhanced information for preference ranking.

        Args:
            pairs: List of dicts containing strategy descriptions and vectors
        """
        logger.info(f"Generated pairs using {self.__class__.__name__}:")

        current_question = None
        for i, pair in enumerate(pairs, 1):
            # Check if we're starting a new question
            if current_question != pair.get("question_number"):
                current_question = pair.get("question_number")
                logger.info(
                    f"\nQuestion {current_question} " f"({pair.get('question_label')}):"
                )

            # Extract vectors and log pair info
            pair_type = pair.get("pair_type", "unknown")
            magnitude = pair.get("magnitude", "?")
            vector_type = pair.get("vector_type", "?")

            # Find the vector keys (exclude metadata)
            vector_keys = [k for k, v in pair.items() if isinstance(v, tuple)]
            if len(vector_keys) >= 2:
                vec_a = pair[vector_keys[0]]
                vec_b = pair[vector_keys[1]]

                vec_a_fmt, sum_a = self._format_vector_for_logging(vec_a)
                vec_b_fmt, sum_b = self._format_vector_for_logging(vec_b)

                logger.info(
                    f"  Pair {i} ({pair_type}, mag={magnitude}, "
                    f"{vector_type}):\n"
                    f"    {vector_keys[0]}: {vec_a_fmt} (sum: {sum_a})\n"
                    f"    {vector_keys[1]}: {vec_b_fmt} (sum: {sum_b})"
                )
