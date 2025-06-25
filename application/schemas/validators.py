import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from application.translations import get_translation

logger = logging.getLogger(__name__)


@dataclass
class ComparisonPair:
    """
    Represents a single comparison pair in the survey.
    Validates individual pair data structure and choices.
    """

    option_1: List[int]
    option_2: List[int]
    user_choice: int
    raw_user_choice: int = None
    option1_strategy: str = None
    option2_strategy: str = None
    option1_differences: List[int] = None
    option2_differences: List[int] = None

    def is_valid(self) -> bool:
        """
        Validates the comparison pair data.

        Returns:
            bool: True if the pair is valid, False otherwise
        """
        try:
            # Validate options structure
            if not isinstance(self.option_1, list) or not isinstance(
                self.option_2, list
            ):
                return False

            # Validate choice range (must be 1 or 2)
            if self.user_choice not in [1, 2]:
                return False

            # Validate that each option sums to 100
            if sum(self.option_1) != 100 or sum(self.option_2) != 100:
                return False

            return True
        except Exception as e:
            logger.error(f"ComparisonPair validation error: {str(e)}")
            return False


@dataclass
class SurveySubmission:
    """
    Represents a complete survey submission.
    Handles validation of the entire survey response including
    budget vector, comparison pairs, and awareness checks.
    """

    user_id: str
    survey_id: int
    user_vector: List[int] = field(default_factory=list)
    user_comment: Optional[str] = ""
    awareness_answers: List[int] = field(default_factory=list)
    comparison_pairs: List[ComparisonPair] = field(default_factory=list)
    expected_pairs: int = 10  # Default for backward compatibility

    def validate(self) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Validates the complete survey submission.

        Checks in order:
        1. Awareness checks (first check answer must be 1, second check answer must be 2)
        2. User vector validation (must have values and sum to 100)
        3. Value range validation
        4. Comparison pairs validation

        Returns:
            tuple[bool, Optional[str], Optional[str]]: A tuple containing:
                - is_valid: Whether the submission is valid
                - error_message: Error message if invalid, None if valid
                - submission_status: 'attention_failed', 'complete', or None if other error
        """
        try:
            # Validate awareness checks
            if (
                len(self.awareness_answers) != 2
                or self.awareness_answers[0] != 1  # First check must be 1
                or self.awareness_answers[1] != 2
            ):  # Second check must be 2
                logger.info(
                    f"User {self.user_id} failed awareness checks with answers: {self.awareness_answers}"
                )
                return (
                    False,
                    get_translation("failed_awareness", "messages"),
                    "attention_failed",
                )

            # Validate user_vector exists
            if not self.user_vector:
                return (False, get_translation("missing_budget", "messages"), None)

            # Validate sum is 100
            if sum(self.user_vector) != 100:
                return (False, get_translation("budget_sum_error", "messages"), None)

            # Validate value ranges
            if any(v < 0 or v > 95 for v in self.user_vector):
                return (False, get_translation("budget_range_error", "messages"), None)

            # Validate comparison pairs count
            if len(self.comparison_pairs) != self.expected_pairs:
                return (False, get_translation("invalid_pairs_count", "messages"), None)

            # Validate each comparison pair
            for idx, pair in enumerate(self.comparison_pairs):
                if not pair.is_valid():
                    return (
                        False,
                        get_translation(
                            "invalid_pair_at_position",
                            "messages",
                            position=str(idx + 1),
                        ),
                        None,
                    )

            return True, None, "complete"

        except Exception as e:
            logger.error(f"Survey validation error: {str(e)}")
            return (False, get_translation("validation_error", "messages"), None)

    @classmethod
    def from_form_data(
        cls,
        form_data: Dict[str, Any],
        user_id: str,
        survey_id: int,
        total_questions: int = None,
    ) -> "SurveySubmission":
        """
        Creates a SurveySubmission instance from form data.
        Handles swapped pairs by restoring original option order and adjusting user choice accordingly.

        Args:
            form_data: The raw form data from the request
            user_id: The user's identifier
            survey_id: The internal survey identifier
            total_questions: Total number of questions including awareness checks (default: inferred from form data)

        Returns:
            SurveySubmission: A new instance with processed form data, where:
                - Pairs are stored in their original semantic order (e.g., sum-optimized first)
                - User choices are adjusted to match this original order

        Raises:
            ValueError: If form data is malformed or missing required fields
        """
        try:
            # Process user vector
            user_vector = list(map(int, form_data.get("user_vector", "").split(",")))

            # Process awareness answers
            awareness_answers = [
                int(form_data.get(f"awareness_check_{i}", 0)) for i in range(2)
            ]

            # Determine the total questions dynamically if not provided
            if total_questions is None:
                # Find the highest question index in the form data
                max_question_idx = -1
                for key in form_data:
                    if key.startswith("choice_"):
                        try:
                            idx = int(key.split("_")[1])
                            max_question_idx = max(max_question_idx, idx)
                        except (ValueError, IndexError):
                            continue

                total_questions = max_question_idx + 1
                logger.debug(f"Inferred total questions: {total_questions}")

            # Count awareness questions to calculate expected pairs
            awareness_count = sum(
                1
                for i in range(total_questions)
                if form_data.get(f"is_awareness_{i}") == "true"
            )
            expected_pairs = total_questions - awareness_count

            # Process comparison pairs (skip awareness questions)
            pairs = []
            for i in range(total_questions):
                if form_data.get(f"is_awareness_{i}") == "true":
                    continue

                option_1 = list(map(int, form_data.get(f"option1_{i}", "").split(",")))
                option_2 = list(map(int, form_data.get(f"option2_{i}", "").split(",")))
                raw_user_choice = int(form_data.get(f"choice_{i}", 0))
                user_choice = raw_user_choice
                was_swapped = form_data.get(f"was_swapped_{i}") == "true"
                option1_strategy = form_data.get(f"option1_strategy_{i}")
                option2_strategy = form_data.get(f"option2_strategy_{i}")

                # Extract differences if available
                option1_diffs_str = form_data.get(f"option1_differences_{i}", "")
                option2_diffs_str = form_data.get(f"option2_differences_{i}", "")

                # Parse differences, handling both int and float strings
                def parse_diffs(diffs_str):
                    return list(map(lambda x: int(float(x)), diffs_str.split(",")))

                option1_differences = (
                    parse_diffs(option1_diffs_str) if option1_diffs_str else None
                )
                option2_differences = (
                    parse_diffs(option2_diffs_str) if option2_diffs_str else None
                )

                if was_swapped:
                    option_1, option_2 = option_2, option_1
                    option1_strategy, option2_strategy = (
                        option2_strategy,
                        option1_strategy,
                    )
                    option1_differences, option2_differences = (
                        option2_differences,
                        option1_differences,
                    )
                    user_choice = 3 - raw_user_choice

                pairs.append(
                    ComparisonPair(
                        option_1=option_1,
                        option_2=option_2,
                        user_choice=user_choice,
                        raw_user_choice=raw_user_choice,
                        option1_strategy=option1_strategy,
                        option2_strategy=option2_strategy,
                        option1_differences=option1_differences,
                        option2_differences=option2_differences,
                    )
                )

            return cls(
                user_id=user_id,
                survey_id=survey_id,
                user_vector=user_vector,
                user_comment=form_data.get("user_comment", "").strip(),
                awareness_answers=awareness_answers,
                comparison_pairs=pairs,
                expected_pairs=expected_pairs,
            )

        except (ValueError, KeyError, AttributeError) as e:
            logger.error(f"Error creating SurveySubmission from form data: {str(e)}")
            raise ValueError(f"Invalid form data: {str(e)}")
