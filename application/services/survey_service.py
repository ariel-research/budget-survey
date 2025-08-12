import logging
import random
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from application.exceptions import UnsuitableForStrategyError
from application.schemas.validators import SurveySubmission
from application.services.pair_generation import StrategyRegistry
from application.translations import get_translation
from database.queries import (
    check_user_participation,
    create_comparison_pair,
    create_survey_response,
    create_user,
    get_subjects,
    get_survey_description,
    get_survey_name,
    get_survey_pair_generation_config,
    is_user_blacklisted,
    mark_survey_as_completed,
    user_exists,
)

from .awareness_check import generate_awareness_questions

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
                - description: str: Survey description
                - subjects: List[str]: Survey subjects
                - survey_id: int: The survey ID
        """
        survey_name = get_survey_name(survey_id)
        if not survey_name:
            return False, ("survey_not_found", {"survey_id": survey_id}), None

        survey_description = get_survey_description(survey_id)
        if not survey_description:
            logger.info(f"No description found for survey: {survey_id}, using default")
            # Using empty string instead of failure, since description is optional
            survey_description = ""

        subjects = get_subjects(survey_id)
        if not subjects:
            return False, ("survey_not_found", {"survey_id": survey_id}), None

        return (
            True,
            None,
            {
                "name": survey_name,
                "description": survey_description,
                "subjects": subjects,
                "survey_id": survey_id,
            },
        )

    @staticmethod
    def check_user_eligibility(
        user_id: str, survey_id: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if user is eligible to take the survey.

        Checks both if user has already completed the survey and
        if user is blacklisted due to failing attention checks.

        Returns:
            Tuple of (eligible: bool, redirect_url: Optional[str])
        """
        # First check if user is blacklisted
        if is_user_blacklisted(user_id):
            logger.info(
                f"User {user_id} is blacklisted and cannot take survey {survey_id}"
            )
            return False, "blacklisted"

        # Then check if user has already completed this specific survey
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
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Generate survey pairs and awareness questions.

        Args:
            user_vector: User's ideal budget allocation
            num_subjects: Number of budget subjects
            survey_id: The internal survey identifier

        Returns:
            Tuple of (comparison_pairs, awareness_questions)

        Raises:
            ValueError: If strategy configuration is invalid
        """
        logger.debug(f"Generating pairs for survey {survey_id}")

        # Get strategy configuration
        config = get_survey_pair_generation_config(survey_id)
        if not config:
            logger.warning(f"No configuration found for survey {survey_id}")
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

            # Generate two awareness questions
            awareness_questions = generate_awareness_questions(
                user_vector, num_subjects
            )

            logger.info(
                f"Successfully generated {len(comparison_pairs)} pairs and {len(awareness_questions)} awareness questions"
            )
            return comparison_pairs, awareness_questions

        except UnsuitableForStrategyError:
            # Re-raise unsuitable strategy errors to be handled by the route
            raise
        except Exception as e:
            logger.error(f"Error generating pairs: {str(e)}")
            raise ValueError(get_translation("pair_generation_error", "messages"))

    @staticmethod
    def process_survey_submission(
        submission: SurveySubmission, attention_check_failed: bool = False
    ) -> None:
        """
        Process and store a survey submission.
        Creates user if needed, stores responses, and marks survey as complete.

        Args:
            submission: Validated survey submission data
            attention_check_failed: Whether the submission failed attention checks

        Raises:
            Exception: If database operations fail
        """
        try:
            # Ensure user exists
            if not user_exists(submission.user_id):
                create_user(submission.user_id)
                logger.info(f"Created new user: {submission.user_id}")

            # Create survey response with attention check status
            survey_response_id = create_survey_response(
                submission.user_id,
                submission.survey_id,
                submission.user_vector,
                submission.user_comment,
                attention_check_failed,
            )
            logger.info(
                f"Created survey response: {survey_response_id} "
                f"(attention_check_failed={attention_check_failed})"
            )

            # Store comparison pairs
            for idx, pair in enumerate(submission.comparison_pairs, 1):
                comparison_pair_id = create_comparison_pair(
                    survey_response_id=survey_response_id,
                    pair_number=idx,
                    option_1=pair.option_1,
                    option_2=pair.option_2,
                    user_choice=pair.user_choice,
                    raw_user_choice=pair.raw_user_choice,
                    option1_strategy=pair.option1_strategy,
                    option2_strategy=pair.option2_strategy,
                    option1_differences=pair.option1_differences,
                    option2_differences=pair.option2_differences,
                )
                logger.debug(
                    f"Created comparison pair {idx}/{len(submission.comparison_pairs)}: "
                    f"{comparison_pair_id} (raw_choice={pair.raw_user_choice}, "
                    f"adjusted_choice={pair.user_choice})"
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

    def _randomize_pair_options(
        self, pair: Dict[str, tuple]
    ) -> Tuple[tuple, tuple, bool, str, str, list, list]:
        """
        Randomly reorder options within a pair.

        Args:
            pair: Dictionary containing strategy descriptions and vectors

        Returns:
            Tuple containing:
            - option1: The first vector
            - option2: The second vector
            - was_swapped: Whether the options were swapped
            - option1_strategy: Strategy description for first option
            - option2_strategy: Strategy description for second option
            - option1_differences: Differences for option 1 (if available)
            - option2_differences: Differences for option 2 (if available)
        """
        # Identify the two vector entries robustly (ignore metadata keys)
        vector_items = [
            (k, v)
            for k, v in pair.items()
            if isinstance(v, (list, tuple)) and len(v) == 3 and sum(v) == 100
        ]

        if len(vector_items) < 2:
            # Fallback to previous behavior (assume first two values are vectors)
            strategy_descriptions = list(pair.keys())
            vectors = list(pair.values())
            option1_diffs = pair.get("option1_differences")
            option2_diffs = pair.get("option2_differences")
            if random.random() < 0.5:
                return (
                    vectors[1],
                    vectors[0],
                    True,
                    strategy_descriptions[1],
                    strategy_descriptions[0],
                    option2_diffs,
                    option1_diffs,
                )
            return (
                vectors[0],
                vectors[1],
                False,
                strategy_descriptions[0],
                strategy_descriptions[1],
                option1_diffs,
                option2_diffs,
            )

        # Map vector labels to their strategy text if available
        (label1, vec1), (label2, vec2) = vector_items[:2]
        opt1_text = label1
        opt2_text = label2

        provided_opt1 = pair.get("option1_strategy")
        provided_opt2 = pair.get("option2_strategy")

        # Prefer provided strategy strings (contain magnitude/type for asymmetric strategy)
        if provided_opt1 and provided_opt2:
            try:
                conc_label = get_translation("concentrated_changes", "answers")
                dist_label = get_translation("distributed_changes", "answers")
            except Exception:
                conc_label = "Concentrated"
                dist_label = "Distributed"

            def pick_text(lbl: str) -> str:
                if conc_label in lbl or "Concentrated" in lbl:
                    return provided_opt1
                if dist_label in lbl or "Distributed" in lbl:
                    return provided_opt2
                # Fallback to provided option1 for first and option2 for second
                return provided_opt1 if lbl == label1 else provided_opt2

            opt1_text = pick_text(label1)
            opt2_text = pick_text(label2)

        # Extract differences if they exist
        option1_diffs = pair.get("option1_differences")
        option2_diffs = pair.get("option2_differences")

        # Randomize order consistently for vectors, texts, and diffs
        if random.random() < 0.5:  # 50% chance to swap
            return (
                vec2,
                vec1,
                True,
                opt2_text,
                opt1_text,
                option2_diffs,
                option1_diffs,
            )

        return (
            vec1,
            vec2,
            False,
            opt1_text,
            opt2_text,
            option1_diffs,
            option2_diffs,
        )

    def to_template_data(self) -> Dict:
        """Convert session data to template variables."""
        original_pairs, awareness_questions = SurveyService.generate_survey_pairs(
            self.user_vector, len(self.subjects), self.internal_survey_id
        )

        # Combine pair data with its presentation state
        presentation_pairs = []

        # Add first awareness question
        presentation_pairs.append(
            {
                "display": (
                    awareness_questions[0]["option1"],
                    awareness_questions[0]["option2"],
                ),
                "was_swapped": False,
                "is_awareness": True,
                "question_number": 1,
            }
        )

        # Add first half of comparison pairs
        midpoint = len(original_pairs) // 2
        for i, pair in enumerate(original_pairs[:midpoint]):
            (
                option1,
                option2,
                was_swapped,
                option1_strategy,
                option2_strategy,
                option1_differences,
                option2_differences,
            ) = self._randomize_pair_options(pair)
            pair_data = {
                "display": (option1, option2),
                "was_swapped": was_swapped,
                "option1_strategy": option1_strategy,
                "option2_strategy": option2_strategy,
                "is_awareness": False,
                "question_number": i + 2,
            }
            # Add differences if they exist
            if option1_differences is not None:
                pair_data["option1_differences"] = option1_differences
            if option2_differences is not None:
                pair_data["option2_differences"] = option2_differences
            presentation_pairs.append(pair_data)

        # Add second awareness question
        presentation_pairs.append(
            {
                "display": (
                    awareness_questions[1]["option1"],
                    awareness_questions[1]["option2"],
                ),
                "was_swapped": False,
                "is_awareness": True,
                "question_number": midpoint + 2,
            }
        )

        # Add remaining comparison pairs
        for i, pair in enumerate(original_pairs[midpoint:]):
            (
                option1,
                option2,
                was_swapped,
                option1_strategy,
                option2_strategy,
                option1_differences,
                option2_differences,
            ) = self._randomize_pair_options(pair)
            pair_data = {
                "display": (option1, option2),
                "was_swapped": was_swapped,
                "option1_strategy": option1_strategy,
                "option2_strategy": option2_strategy,
                "is_awareness": False,
                "question_number": i + midpoint + 3,
            }
            # Add differences if they exist
            if option1_differences is not None:
                pair_data["option1_differences"] = option1_differences
            if option2_differences is not None:
                pair_data["option2_differences"] = option2_differences
            presentation_pairs.append(pair_data)

        return {
            "user_vector": self.user_vector,
            "comparison_pairs": presentation_pairs,
            "subjects": self.subjects,
            "user_id": self.user_id,
            "survey_id": self.external_survey_id,
            "zip": zip,
        }
