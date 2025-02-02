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
    budget vector, comparison pairs, and awareness check.
    """

    user_id: str
    survey_id: int
    user_vector: List[int] = field(default_factory=list)
    user_comment: Optional[str] = ""
    awareness_answer: int = 0
    comparison_pairs: List[ComparisonPair] = field(default_factory=list)

    def validate(self) -> tuple[bool, Optional[str]]:
        """
        Validates the complete survey submission.

        Returns:
            tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        try:
            # Validate user_vector
            if not self.user_vector:
                return False, get_translation("missing_budget", "messages")

            if sum(self.user_vector) != 100:
                return False, get_translation("budget_sum_error", "messages")

            if any(v < 0 or v > 95 for v in self.user_vector):
                return False, get_translation("budget_range_error", "messages")

            # Validate awareness check (must be 2)
            if self.awareness_answer != 2:
                return False, get_translation("failed_awareness", "messages")

            # Validate comparison pairs
            if len(self.comparison_pairs) != 10:
                return False, get_translation("invalid_pairs_count", "messages")

            # Validate each comparison pair
            for idx, pair in enumerate(self.comparison_pairs):
                if not pair.is_valid():
                    return False, get_translation(
                        "invalid_pair_at_position", "messages", position=str(idx + 1)
                    )

            return True, None

        except Exception as e:
            logger.error(f"Survey validation error: {str(e)}")
            return False, get_translation("validation_error", "messages")

    @classmethod
    def from_form_data(
        cls, form_data: Dict[str, Any], user_id: str, survey_id: int
    ) -> "SurveySubmission":
        """
        Creates a SurveySubmission instance from form data.
        Handles swapped pairs by restoring original option order and adjusting user choice accordingly.

        Args:
            form_data: The raw form data from the request
            user_id: The user's identifier
            survey_id: The internal survey identifier

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

            # Process comparison pairs
            pairs = []
            for i in range(10):
                option_1 = list(map(int, form_data.get(f"option1_{i}", "").split(",")))
                option_2 = list(map(int, form_data.get(f"option2_{i}", "").split(",")))
                raw_user_choice = int(form_data.get(f"choice_{i}", 0))
                user_choice = raw_user_choice
                was_swapped = form_data.get(f"was_swapped_{i}") == "true"
                option1_strategy = form_data.get(f"option1_strategy_{i}")
                option2_strategy = form_data.get(f"option2_strategy_{i}")

                # If options were swapped during display, adjust choice and the options
                # to match original option order
                if was_swapped:
                    # Swap both options and adjust choice
                    option_1, option_2 = option_2, option_1
                    option1_strategy, option2_strategy = (
                        option2_strategy,
                        option1_strategy,
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
                    )
                )

            return cls(
                user_id=user_id,
                survey_id=survey_id,
                user_vector=user_vector,
                user_comment=form_data.get("user_comment", "").strip(),
                awareness_answer=int(form_data.get("awareness_check", 0)),
                comparison_pairs=pairs,
            )

        except (ValueError, KeyError, AttributeError) as e:
            logger.error(f"Error creating SurveySubmission from form data: {str(e)}")
            raise ValueError(f"Invalid form data: {str(e)}")
