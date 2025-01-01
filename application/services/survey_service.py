import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from application.schemas.validators import SurveySubmission
from application.services.pair_generation import StrategyRegistry
from application.translations import get_translation
from database.queries import (
    check_user_participation,
    create_comparison_pair,
    create_survey_response,
    create_user,
    get_subjects,
    get_survey_name,
    get_survey_pair_generation_config,
    mark_survey_as_completed,
    user_exists,
)

from .survey_vector_generator import (
    generate_awareness_check,
)

logger = logging.getLogger(__name__)


class SurveyService:
    @staticmethod
    def check_survey_exists(
        survey_id: int,
    ) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        Verify survey exists and get its data.

        Args:
            survey_id: The internal survey ID

        Returns:
            Tuple containing:
            - exists: bool: Whether the survey exists
            - error_message: Optional[str]: Error message if survey doesn't exist
            - data: Optional[Dict]: Survey data if exists, containing:
                - name: str: Survey name
                - subjects: List[str]: Survey subjects
                - survey_id: int: The survey ID
        """
        survey_name = get_survey_name(survey_id)
        if not survey_name:
            return False, ("survey_not_found", {"survey_id": survey_id}), None

        subjects = get_subjects(survey_id)
        if not subjects:
            return False, ("survey_not_found", {"survey_id": survey_id}), None

        return (
            True,
            None,
            {"name": survey_name, "subjects": subjects, "survey_id": survey_id},
        )

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
        """
        Validate user's budget allocation vector.

        Args:
            vector: List of integers representing budget allocations
            num_subjects: Expected number of subjects in the survey

        Returns:
            bool: True if vector is valid, False otherwise

        Validation rules:
        - Vector length must match number of subjects
        - Each value must be between 0 and 95
        - Sum of all values must be exactly 100
        - All values must be divisible by 5
        """
        return (
            len(vector) == num_subjects
            and sum(vector) == 100
            and all(0 <= v <= 95 and v % 5 == 0 for v in vector)
        )

    @staticmethod
    def generate_survey_pairs(
        user_vector: List[int], num_subjects: int, survey_id: int
    ) -> Tuple[List[Dict], Dict]:
        """
        Generate survey pairs and awareness check, using configured strategy.

        Args:
            user_vector: User's ideal budget allocation
            num_subjects: Number of budget subjects
            survey_id: The internal survey identifier

        Returns:
            Tuple of (comparison_pairs, awareness_check)

        Raises:
            ValueError: If strategy configuration is invalid
        """
        logger.debug(f"Generating pairs for survey {survey_id}")

        # Get strategy configuration
        config = get_survey_pair_generation_config(survey_id)
        if not config:
            logger.error(f"No configuration found for survey {survey_id}")
            raise ValueError(get_translation("survey_not_found", "messages"))

        try:
            # Parse and validate configuration
            strategy_name = config.get("strategy")
            params = config.get("params", {})

            if not strategy_name:
                raise ValueError("Missing strategy name in configuration")

            # Get and execute strategy
            strategy = StrategyRegistry.get_strategy(strategy_name)
            comparison_pairs = strategy.generate_pairs(
                tuple(user_vector),
                n=params.get("num_pairs", 10),
                vector_size=num_subjects,
            )

            # Generate awareness check
            awareness_check = generate_awareness_check(user_vector, num_subjects)

            logger.info(f"Successfully generated {len(comparison_pairs)} pairs")
            return comparison_pairs, awareness_check

        except Exception as e:
            logger.error(f"Error generating pairs: {str(e)}")
            raise ValueError(get_translation("pair_generation_error", "messages"))

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
        self,
        user_id: str,
        internal_survey_id: int,
        external_survey_id: int,
        user_vector: List[int],
        subjects: List[str],
    ):
        self.user_id = user_id
        self.internal_survey_id = internal_survey_id
        self.external_survey_id = external_survey_id
        self.user_vector = user_vector
        self.subjects = subjects
        self.timestamp = datetime.now()

    def to_template_data(self) -> Dict:
        """Convert session data to template variables."""
        comparison_pairs, awareness_check = SurveyService.generate_survey_pairs(
            self.user_vector, len(self.subjects), self.internal_survey_id
        )

        return {
            "user_vector": self.user_vector,
            "comparison_pairs": comparison_pairs,
            "awareness_check": awareness_check,
            "subjects": self.subjects,
            "user_id": self.user_id,
            "survey_id": self.external_survey_id,
            "zip": zip,
        }
