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
    create_early_awareness_failure,
    create_survey_response,
    create_user,
    get_subjects,
    get_survey_awareness_pts,
    get_survey_description,
    get_survey_name,
    get_survey_pair_generation_config,
    is_user_blacklisted,
    mark_survey_as_completed,
    user_already_responded_to_survey,
    user_exists,
)

from .awareness_check import (
    generate_awareness_questions,
    generate_ranking_awareness_question,
)

logger = logging.getLogger(__name__)


def format_budget_vector_with_subjects(vector: tuple, subjects: List[str]) -> str:
    """
    Format a budget vector with subject names for display.

    Args:
        vector: Budget allocation tuple (e.g., (50, 30, 20))
        subjects: List of subject names (e.g., ["Health", "Education", "Defense"])

    Returns:
        Formatted string like "Health: 50, Education: 30, Defense: 20"
    """
    if len(vector) != len(subjects):
        logger.warning(
            f"Vector length {len(vector)} doesn't match subjects length {len(subjects)}"
        )
        return ", ".join(map(str, vector))  # Fallback to numbers only

    formatted_parts = []
    for subject, value in zip(subjects, vector):
        formatted_parts.append(f"{subject}: {value}")

    return ", ".join(formatted_parts)


class SurveyService:
    @staticmethod
    def generate_screening_questions(
        user_vector: List[int], subjects: List[str]
    ) -> List[Dict]:
        """
        Generate 2 screening questions for triangle inequality test.

        Tests whether user uses additive utility (prefers ideal in one year)
        or balancing utility (prefers average to be ideal).

        Args:
            user_vector: User's ideal budget allocation
            subjects: List of subject names

        Returns:
            List of 2 screening questions, each containing:
            - question_number: int
            - fixed_year: int (1 or 2)
            - fixed_budget: tuple
            - option_a: tuple
            - option_b: tuple
            - correct_answer: int (1 or 2)
            - prompt_key: str
        """

        if any(value == 0 for value in user_vector):
            logger.info(
                "User vector %s contains zero values; unsuitable for "
                "triangle inequality screening",
                user_vector,
            )
            raise UnsuitableForStrategyError(
                "User vector contains zero values and is unsuitable for triangle "
                "inequality strategy",
            )

        def create_random_vector(size: int) -> tuple:
            """Create a random budget vector that sums to 100."""
            # Generate random values
            values = []
            remaining = 100

            for i in range(size - 1):
                # Randomly allocate between 0 and remaining, in multiples of 5
                max_val = (
                    remaining - (size - i - 1) * 5
                )  # Leave at least 5 for each remaining
                max_val = max(0, min(95, max_val))
                val = random.randint(0, max_val // 5) * 5
                values.append(val)
                remaining -= val

            values.append(remaining)
            return tuple(values)

        def generate_valid_screening_pair(
            user_vector: tuple, existing_randoms: List[tuple]
        ) -> Tuple[tuple, tuple]:
            """
            Generate valid (r, q_balance) pair where q_balance = 2*p - r is valid.

            Uses retry loop pattern from dynamic_temporal_preference_strategy.

            Args:
                user_vector: User's ideal budget allocation
                existing_randoms: Already used random vectors to avoid duplicates

            Returns:
                Tuple of (r, q_balance) where both are valid and different from user_vector
            """
            max_attempts = 200

            for attempt in range(max_attempts):
                # Generate random vector
                r = create_random_vector(len(user_vector))

                # Ensure r is unique and different from user_vector
                if r == tuple(user_vector) or r in existing_randoms:
                    continue

                # Calculate balancing vector: q_balance = 2*p - r
                q_balance = tuple(
                    2 * user_vector[i] - r[i] for i in range(len(user_vector))
                )

                # Validate balancing vector
                if all(0 <= v <= 100 for v in q_balance) and q_balance != tuple(
                    user_vector
                ):
                    return r, q_balance

            # Should rarely reach here - raise error if we can't find valid pair
            logger.info(
                "Unable to generate valid screening pair for user_vector %s after "
                "%s attempts",
                user_vector,
                max_attempts,
            )
            raise UnsuitableForStrategyError(
                "Unable to generate screening questions for the provided user vector"
            )

        # Generate Question 1: Year 1 fixed, choose Year 2
        r1, q_balance_1 = generate_valid_screening_pair(tuple(user_vector), [])

        q1 = {
            "question_number": 1,
            "fixed_year": 1,
            "fixed_budget": r1,
            "option_a": tuple(user_vector),  # Additive (correct)
            "option_b": q_balance_1,  # Balancing
            "correct_answer": 1,
            "prompt_key": "screening_q1_prompt",
        }

        # Generate Question 2: Year 2 fixed, choose Year 1
        r2, q_balance_2 = generate_valid_screening_pair(tuple(user_vector), [r1])

        q2 = {
            "question_number": 2,
            "fixed_year": 2,
            "fixed_budget": r2,
            "option_a": q_balance_2,  # Balancing
            "option_b": tuple(user_vector),  # Additive (correct)
            "correct_answer": 2,
            "prompt_key": "screening_q2_prompt",
        }

        return [q1, q2]

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
                - strategy_name: str: The strategy name for this survey
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

        # Get strategy name
        config = get_survey_pair_generation_config(survey_id)
        strategy_name = config.get("strategy", "") if config else ""

        return (
            True,
            None,
            {
                "name": survey_name,
                "description": survey_description,
                "subjects": subjects,
                "survey_id": survey_id,
                "strategy_name": strategy_name,
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
                f"Successfully generated {len(comparison_pairs)} pairs and "
                f"{len(awareness_questions)} awareness questions"
            )
            return comparison_pairs, awareness_questions

        except UnsuitableForStrategyError:
            # Re-raise unsuitable strategy errors to be handled by the route
            raise
        except Exception as e:
            logger.error(f"Error generating pairs: {str(e)}")
            raise ValueError(get_translation("pair_generation_error", "messages"))

    @staticmethod
    def generate_ranking_questions(
        user_vector: List[int], num_subjects: int, survey_id: int
    ) -> List[Dict]:
        """
        Generate ranking questions for ranking-based strategies.

        Args:
            user_vector: User's ideal budget allocation
            num_subjects: Number of budget subjects
            survey_id: The internal survey identifier

        Returns:
            List of ranking questions with options A, B, C

        Raises:
            ValueError: If strategy configuration is invalid or strategy is not ranking-based
        """
        logger.debug(f"Generating ranking questions for survey {survey_id}")

        # Get strategy configuration
        config = get_survey_pair_generation_config(survey_id)
        if not config:
            logger.warning(f"No configuration found for survey {survey_id}")
            raise ValueError(get_translation("survey_not_found", "messages"))

        try:
            # Parse and validate configuration
            strategy_name = config.get("strategy")
            if not strategy_name:
                raise ValueError("Missing strategy name in configuration")

            # Get strategy and check if it's ranking-based
            strategy = StrategyRegistry.get_strategy(strategy_name)
            if not strategy.is_ranking_based():
                raise ValueError(f"Strategy {strategy_name} is not ranking-based")

            # Generate ranking questions using strategy's method
            ranking_questions = strategy.generate_ranking_questions(
                tuple(user_vector), vector_size=num_subjects
            )

            logger.info(
                f"Successfully generated {len(ranking_questions)} ranking questions"
            )
            return ranking_questions

        except UnsuitableForStrategyError:
            # Re-raise unsuitable strategy errors to be handled by the route
            raise
        except Exception as e:
            logger.error(f"Error generating ranking questions: {str(e)}")
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
                # Use original_pair_number if available (for interleaved strategies),
                # otherwise use enumeration index for backward compatibility
                pair_number = (
                    pair.original_pair_number if pair.original_pair_number else idx
                )

                comparison_pair_id = create_comparison_pair(
                    survey_response_id=survey_response_id,
                    pair_number=pair_number,
                    option_1=pair.option_1,
                    option_2=pair.option_2,
                    user_choice=pair.user_choice,
                    raw_user_choice=pair.raw_user_choice,
                    option1_strategy=pair.option1_strategy,
                    option2_strategy=pair.option2_strategy,
                    option1_differences=pair.option1_differences,
                    option2_differences=pair.option2_differences,
                    generation_metadata=pair.generation_metadata,
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

    @staticmethod
    def check_user_already_responded(user_id: str, survey_id: int) -> bool:
        """
        Check if a user has already responded to this survey.
        Prevents duplicate submissions and browser back-button exploits.

        Args:
            user_id: The user's identifier
            survey_id: The internal survey ID

        Returns:
            bool: True if user already has a response for this survey
        """
        return user_already_responded_to_survey(user_id, survey_id)

    @staticmethod
    def record_early_awareness_failure(
        user_id: str,
        survey_id: int,
        user_vector: List[int],
        pts_value: int,
    ) -> Optional[int]:
        """
        Record an early awareness check failure detected by the frontend.
        Creates user if not exists, then creates survey_response with failure data.

        Args:
            user_id: The user's identifier
            survey_id: The survey ID
            user_vector: The user's budget vector
            pts_value: Awareness failure code (1=first awareness, 2=second awareness)

        Returns:
            int: The ID of the created survey_response record, or None if creation fails
        """
        try:
            # Ensure user exists
            if not user_exists(user_id):
                create_user(user_id)
                logger.info(f"Created new user for early failure: {user_id}")

            # Record the early failure with completed=FALSE
            response_id = create_early_awareness_failure(
                user_id=user_id,
                survey_id=survey_id,
                optimal_allocation=user_vector,
                pts_value=pts_value,
            )

            logger.info(
                f"Early awareness failure recorded: user_id={user_id}, "
                f"survey_id={survey_id}, pts_value={pts_value}, response_id={response_id}"
            )
            return response_id

        except Exception as e:
            logger.error(
                f"Failed to record early awareness failure for user {user_id}: "
                f"{str(e)}",
                exc_info=True,
            )
            return None

    @staticmethod
    def get_awareness_token(survey_id: int, question_index: int) -> Optional[str]:
        """
        Fetch the per-survey awareness token for a given question index.

        Args:
            survey_id: The survey ID
            question_index: 0 for first awareness, 1 for second awareness

        Returns:
            Optional[str]: Token string if configured, otherwise None.
        """
        tokens = get_survey_awareness_pts(survey_id)
        if tokens is None:
            return None

        if not isinstance(question_index, int):
            return None

        if question_index == 0:
            return tokens.get("first")
        if question_index == 1:
            return tokens.get("second")
        return None


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
    ) -> Tuple[tuple, tuple, bool, str, str, list, list, dict, int, dict]:
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
            - instruction_context: Context for generating sub-survey specific instructions
            - original_pair_number: Original logical pair number (for interleaved strategies)
            - generation_metadata: Metadata about pair generation (for rank-based strategies)
        """
        # Extract and remove __metadata__ key before processing (so it's not treated as a vector)
        has_metadata = "__metadata__" in pair
        generation_metadata = pair.pop("__metadata__", None)
        logger.debug(
            "Randomizing pair original_num=%s has_metadata=%s metadata=%s",
            pair.get("original_pair_number"),
            has_metadata,
            generation_metadata,
        )

        # Identify the two vector entries robustly (ignore metadata keys)
        # Support both standard 3-element vectors and biennial 6-element vectors
        vector_items = [
            (k, v)
            for k, v in pair.items()
            if isinstance(v, (list, tuple))
            and (
                (len(v) == 3 and sum(v) == 100)  # Standard single-year budget
                or (len(v) == 6 and sum(v) == 200)  # Biennial two-year budget
            )
        ]

        # Extract instruction context if available
        instruction_context = pair.get("instruction_context", {}).copy()

        # If there's a fixed_vector in instruction_context, format it with subject names
        if "fixed_vector" in instruction_context:
            fixed_vector = instruction_context["fixed_vector"]
            formatted_vector = format_budget_vector_with_subjects(
                fixed_vector, self.subjects
            )
            instruction_context["fixed_vector_formatted"] = formatted_vector

        # Extract original pair number for interleaved strategies (default to 0 for backward compatibility)
        original_pair_number = pair.get("original_pair_number", 0)

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
                    instruction_context,
                    original_pair_number,
                    generation_metadata,
                )
            return (
                vectors[0],
                vectors[1],
                False,
                strategy_descriptions[0],
                strategy_descriptions[1],
                option1_diffs,
                option2_diffs,
                instruction_context,
                original_pair_number,
                generation_metadata,
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
                instruction_context,
                original_pair_number,
                generation_metadata,
            )

        return (
            vec1,
            vec2,
            False,
            opt1_text,
            opt2_text,
            option1_diffs,
            option2_diffs,
            instruction_context,
            original_pair_number,
            generation_metadata,
        )

    def to_template_data(self) -> Dict:
        """Convert session data to template variables."""
        # Get strategy configuration to check if it's ranking-based
        from application.services.pair_generation import StrategyRegistry
        from database.queries import get_survey_pair_generation_config

        config = get_survey_pair_generation_config(self.internal_survey_id)
        strategy_name = config.get("strategy") if config else None
        is_ranking_strategy = False

        if strategy_name:
            try:
                strategy = StrategyRegistry.get_strategy(strategy_name)
                is_ranking_strategy = strategy.is_ranking_based()
            except Exception:
                logger.warning(f"Could not check strategy {strategy_name}")

        if is_ranking_strategy:
            # Generate ranking questions for ranking-based strategies
            ranking_questions = SurveyService.generate_ranking_questions(
                self.user_vector, len(self.subjects), self.internal_survey_id
            )

            # Generate single ranking awareness question
            ranking_awareness_question = generate_ranking_awareness_question(
                self.user_vector, len(self.subjects)
            )

            # Insert awareness question at position 3 (after first 2 ranking questions)
            all_questions = (
                ranking_questions[:2]  # First 2 ranking questions
                + [ranking_awareness_question]  # Awareness question at position 3
                + ranking_questions[2:]  # Remaining 2 ranking questions
            )

            # Renumber all questions sequentially to avoid duplicates
            for i, question in enumerate(all_questions, 1):
                question["question_number"] = i

            return {
                "user_vector": self.user_vector,
                "ranking_questions": all_questions,
                "awareness_positions": [2],  # 0-indexed position of awareness question
                "subjects": self.subjects,
                "user_id": self.user_id,
                "external_survey_id": self.external_survey_id,
                "is_ranking_based": True,
                "strategy_name": strategy_name,
                "zip": zip,
            }
        else:
            # Generate pairs for traditional strategies
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
                    instruction_context,
                    original_pair_number,
                    generation_metadata,
                ) = self._randomize_pair_options(pair)
                pair_data = {
                    "display": (option1, option2),
                    "was_swapped": was_swapped,
                    "option1_strategy": option1_strategy,
                    "option2_strategy": option2_strategy,
                    "is_awareness": False,
                    "question_number": i + 2,
                    "instruction_context": instruction_context,
                    "original_pair_number": original_pair_number,
                }
                # Add differences if they exist
                if option1_differences is not None:
                    pair_data["option1_differences"] = option1_differences
                if option2_differences is not None:
                    pair_data["option2_differences"] = option2_differences
                # Add generation metadata if it exists
                if generation_metadata is not None:
                    pair_data["generation_metadata"] = generation_metadata
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
                    instruction_context,
                    original_pair_number,
                    generation_metadata,
                ) = self._randomize_pair_options(pair)
                pair_data = {
                    "display": (option1, option2),
                    "was_swapped": was_swapped,
                    "option1_strategy": option1_strategy,
                    "option2_strategy": option2_strategy,
                    "is_awareness": False,
                    "question_number": i + midpoint + 3,
                    "instruction_context": instruction_context,
                    "original_pair_number": original_pair_number,
                }
                # Add differences if they exist
                if option1_differences is not None:
                    pair_data["option1_differences"] = option1_differences
                if option2_differences is not None:
                    pair_data["option2_differences"] = option2_differences
                # Add generation metadata if it exists
                if generation_metadata is not None:
                    pair_data["generation_metadata"] = generation_metadata
                presentation_pairs.append(pair_data)

            return {
                "user_vector": self.user_vector,
                "comparison_pairs": presentation_pairs,
                "subjects": self.subjects,
                "user_id": self.user_id,
                "external_survey_id": self.external_survey_id,
                "is_ranking_based": False,
                "strategy_name": strategy_name,
                "zip": zip,
            }
