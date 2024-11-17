import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

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
                return False, "Missing budget allocation"

            if sum(self.user_vector) != 100:
                return False, "Budget allocation must sum to 100"

            if any(v < 0 or v > 95 for v in self.user_vector):
                return False, "Budget values must be between 0 and 95"

            # Validate awareness check (must be 2 based on survey.js)
            if self.awareness_answer != 2:
                return False, "Failed awareness check"

            # Validate comparison pairs
            if len(self.comparison_pairs) != 10:
                return False, "Incorrect number of comparison pairs"

            # Validate each comparison pair
            for idx, pair in enumerate(self.comparison_pairs):
                if not pair.is_valid():
                    return False, f"Invalid comparison pair at position {idx + 1}"

            return True, None

        except Exception as e:
            logger.error(f"Survey validation error: {str(e)}")
            return False, "Internal validation error"

    @classmethod
    def from_form_data(
        cls, form_data: Dict[str, Any], user_id: str, survey_id: int
    ) -> "SurveySubmission":
        """
        Creates a SurveySubmission instance from form data.

        Args:
            form_data: The raw form data from the request
            user_id: The user's identifier
            survey_id: The survey identifier

        Returns:
            SurveySubmission: A new instance with processed form data

        Raises:
            ValueError: If form data is malformed or missing required fields
        """
        try:
            # Process user vector
            user_vector = list(map(int, form_data.get("user_vector", "").split(",")))

            # Process comparison pairs
            pairs = []
            for i in range(10):  # Matches TOTAL_RADIO_GROUPS-1 from survey.js
                option_1 = list(map(int, form_data.get(f"option1_{i}", "").split(",")))
                option_2 = list(map(int, form_data.get(f"option2_{i}", "").split(",")))
                user_choice = int(form_data.get(f"choice_{i}", 0))

                pairs.append(
                    ComparisonPair(
                        option_1=option_1, option_2=option_2, user_choice=user_choice
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
