import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from application.schemas.validators import SurveySubmission
from database.queries import (
    check_user_participation,
    create_comparison_pair,
    create_survey_response,
    create_user,
    get_subjects,
    get_survey_name,
    mark_survey_as_completed,
    user_exists,
)
from utils.generate_examples import generate_user_example
from utils.survey_utils import generate_awareness_check, is_valid_vector

logger = logging.getLogger(__name__)


class SurveyService:
    @staticmethod
    def check_survey_exists(survey_id: int) -> Tuple[bool, Optional[str]]:
        """
        Verify survey exists and has subjects.

        Returns:
            Tuple of (exists: bool, error_message: Optional[str])
        """
        survey_name = get_survey_name(survey_id)
        if not survey_name:
            return False, "Survey not found"

        subjects = get_subjects(survey_id)
        if not subjects:
            return False, "Survey has no subjects"

        return True, None

    @staticmethod
    def check_user_eligibility(
        user_id: str, survey_id: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if user is eligible to take the survey.

        Returns:
            Tuple of (eligible: bool, redirect_url: Optional[str])
        """
        if check_user_participation(user_id, survey_id):
            logger.info(f"User {user_id} has already completed survey {survey_id}")
            return False, "thank_you"
        return True, None

    @staticmethod
    def validate_vector(vector: List[int], num_subjects: int) -> bool:
        """Validate user's budget allocation vector."""
        return len(vector) == num_subjects and is_valid_vector(vector)

    @staticmethod
    def generate_survey_pairs(
        user_vector: List[int], num_subjects: int
    ) -> Tuple[List[Dict], Dict]:
        """
        Generate survey comparison pairs and awareness check.

        Args:
            user_vector: User's ideal budget allocation
            num_subjects: Number of budget subjects

        Returns:
            Tuple of (comparison_pairs, awareness_check)
        """
        comparison_pairs = list(
            generate_user_example(tuple(user_vector), n=10, vector_size=num_subjects)
        )
        awareness_check = generate_awareness_check(user_vector, num_subjects)

        return comparison_pairs, awareness_check

    @staticmethod
    def process_survey_submission(submission: SurveySubmission) -> None:
        """
        Process and store a complete survey submission.
        Creates user if needed, stores responses, and marks survey as complete.

        Args:
            submission: Validated survey submission data

        Raises:
            Exception: If database operations fail
        """
        try:
            # Ensure user exists
            if not user_exists(submission.user_id):
                create_user(submission.user_id)
                logger.info(f"Created new user: {submission.user_id}")

            # Create survey response
            survey_response_id = create_survey_response(
                submission.user_id,
                submission.survey_id,
                submission.user_vector,
                submission.user_comment,
            )
            logger.info(f"Created survey response: {survey_response_id}")

            # Store comparison pairs
            for idx, pair in enumerate(submission.comparison_pairs, 1):
                comparison_pair_id = create_comparison_pair(
                    survey_response_id,
                    idx,
                    pair.option_1,
                    pair.option_2,
                    pair.user_choice,
                )
                logger.debug(
                    f"Created comparison pair {idx}/{len(submission.comparison_pairs)}: "
                    f"{comparison_pair_id}"
                )

            # Mark survey as complete
            mark_survey_as_completed(survey_response_id)
            logger.info(
                f"Marked survey {submission.survey_id} as completed for user "
                f"{submission.user_id}"
            )

        except Exception as e:
            logger.error(
                f"Failed to process survey submission for user {submission.user_id}: "
                f"{str(e)}",
                exc_info=True,
            )
            raise


class SurveySessionData:
    """Helper class to manage survey session data."""

    def __init__(
        self, user_id: str, survey_id: int, user_vector: List[int], subjects: List[str]
    ):
        self.user_id = user_id
        self.survey_id = survey_id
        self.user_vector = user_vector
        self.subjects = subjects
        self.timestamp = datetime.now()

    def to_template_data(self) -> Dict:
        """Convert session data to template variables."""
        comparison_pairs, awareness_check = SurveyService.generate_survey_pairs(
            self.user_vector, len(self.subjects)
        )

        return {
            "user_vector": self.user_vector,
            "comparison_pairs": comparison_pairs,
            "awareness_check": awareness_check,
            "subjects": self.subjects,
            "user_id": self.user_id,
            "survey_id": self.survey_id,
            "zip": zip,
        }
