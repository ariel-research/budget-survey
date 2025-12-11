import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

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
    original_pair_number: int = None
    generation_metadata: Optional[Dict[str, Any]] = None

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

            # Validate sum: 100 for single-year, 200 for biennial budgets
            # Biennial budgets have 6 elements (2 years × 3 subjects)
            expected_sum = 200 if len(self.option_1) == 6 else 100

            if sum(self.option_1) != expected_sum or sum(self.option_2) != expected_sum:
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
    awareness_answers: List[Union[int, str]] = field(default_factory=list)
    comparison_pairs: List[ComparisonPair] = field(default_factory=list)
    expected_pairs: int = 10  # Default for backward compatibility

    def validate(self) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Validates the complete survey submission.

        Checks in order:
        1. Awareness checks (traditional: 2 answers [1,2], ranking: 1 'B')
        2. User vector validation (must have values and sum to 100)
        3. Value range validation
        4. Comparison pairs validation

        Returns:
            tuple[bool, Optional[str], Optional[str]]: A tuple containing:
                - is_valid: Whether the submission is valid
                - error_message: Error message if invalid, None if valid
                - submission_status: 'attention_failed', 'complete', or None if
                  other error
        """
        try:
            # Determine if ranking survey by checking for ranking data in pairs
            # or by the format of awareness answers (string vs int for ranking vs traditional)
            is_ranking_survey = any(
                hasattr(pair, "option1_strategy")
                and pair.option1_strategy
                and "Preference Ranking" in pair.option1_strategy
                for pair in self.comparison_pairs
            )

            # If no pairs, check awareness answer format to detect ranking surveys
            if not is_ranking_survey and len(self.comparison_pairs) == 0:
                is_ranking_survey = len(self.awareness_answers) == 1 and isinstance(
                    self.awareness_answers[0], str
                )
            # Validate awareness checks based on survey type
            if is_ranking_survey:
                # For ranking surveys: expect single answer 'B'
                if len(self.awareness_answers) != 1 or self.awareness_answers[0] != "B":
                    logger.info(
                        f"User {self.user_id} failed ranking awareness check "
                        f"with answer: {self.awareness_answers}"
                    )
                    return (
                        False,
                        get_translation("failed_awareness", "messages"),
                        "attention_failed",
                    )
            else:
                # For traditional surveys: expect two answers [1, 2]
                if (
                    len(self.awareness_answers) != 2
                    or self.awareness_answers[0] != 1  # First check must be 1
                    or self.awareness_answers[1] != 2
                ):  # Second check must be 2
                    logger.info(
                        f"User {self.user_id} failed awareness checks "
                        f"with answers: {self.awareness_answers}"
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
    def _convert_ranking_to_pairs(
        cls, form_data: Dict[str, Any]
    ) -> List["ComparisonPair"]:
        """
        Convert ranking question responses to pairs for storage.

        Each ranking question (A, B, C ranked 1-3) becomes 3 pairs:
        - A vs B, A vs C, B vs C

        Args:
            form_data: Form data containing ranking responses

        Returns:
            List of ComparisonPair objects converted from rankings
        """
        pairs = []

        # Find all ranking questions
        ranking_questions = set()
        for key in form_data.keys():
            if key.startswith("rank_1_q"):
                question_num = int(key.split("q")[1])
                ranking_questions.add(question_num)

        for question_num in sorted(ranking_questions):
            # Skip awareness questions (don't store in database)
            if form_data.get(f"is_awareness_q{question_num}") == "true":
                continue

            # Get the ranking responses
            rank_1 = form_data.get(f"rank_1_q{question_num}", "")  # Most preferred
            rank_2 = form_data.get(f"rank_2_q{question_num}", "")
            rank_3 = form_data.get(f"rank_3_q{question_num}", "")  # Least preferred

            # Get the option vectors
            option_a = list(
                map(
                    int,
                    form_data.get(f"question_{question_num}_option_a", "").split(","),
                )
            )
            option_b = list(
                map(
                    int,
                    form_data.get(f"question_{question_num}_option_b", "").split(","),
                )
            )
            option_c = list(
                map(
                    int,
                    form_data.get(f"question_{question_num}_option_c", "").split(","),
                )
            )

            # Get metadata
            magnitude = form_data.get(f"question_{question_num}_magnitude", "")
            vector_type = form_data.get(f"question_{question_num}_vector_type", "")

            # Convert option letters to vectors
            option_map = {"A": option_a, "B": option_b, "C": option_c}

            # Create ranking lookup: which option has which rank
            ranking = {rank_1: 1, rank_2: 2, rank_3: 3}

            # Generate the 3 pairs: A vs B, A vs C, B vs C
            option_pairs = [("A", "B"), ("A", "C"), ("B", "C")]

            for opt1, opt2 in option_pairs:
                # Determine which option is preferred based on ranking
                opt1_rank = ranking.get(opt1, 4)  # Default to 4 if not found
                opt2_rank = ranking.get(opt2, 4)

                # User choice: 1 if option1 is preferred, 2 if option2 is preferred
                user_choice = 1 if opt1_rank < opt2_rank else 2

                # Create strategy descriptions
                strategy_base = f"Preference Ranking Q{question_num} (mag={magnitude}, {vector_type})"
                option1_strategy = f"{strategy_base} - Option {opt1}"
                option2_strategy = f"{strategy_base} - Option {opt2}"

                pairs.append(
                    ComparisonPair(
                        option_1=option_map[opt1],
                        option_2=option_map[opt2],
                        user_choice=user_choice,
                        raw_user_choice=user_choice,
                        option1_strategy=option1_strategy,
                        option2_strategy=option2_strategy,
                        option1_differences=None,  # Not applicable for ranking
                        option2_differences=None,
                    )
                )

        logger.info(
            f"Converted {len(ranking_questions)} ranking questions to {len(pairs)} pairs"
        )
        return pairs

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

            # Check if this is a ranking-based survey
            is_ranking_survey = any(
                key.startswith("rank_1_q") for key in form_data.keys()
            )

            # Process awareness answers based on survey type
            if is_ranking_survey:
                # For ranking surveys: find the awareness question dynamically
                awareness_answers = []
                for key in form_data.keys():
                    if key.startswith("is_awareness_q"):
                        # Extract question number from is_awareness_q{N}
                        question_num = key.split("is_awareness_q")[1]
                        rank_1_key = f"rank_1_q{question_num}"
                        rank_1_answer = form_data.get(rank_1_key, "")
                        if rank_1_answer:
                            awareness_answers = [rank_1_answer]
                        break
            else:
                # For traditional surveys: extract two awareness check answers
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

            # Process pairs differently for ranking vs traditional surveys
            pairs = []

            if is_ranking_survey:
                # For ranking surveys: convert ranking responses to pairs
                pairs = cls._convert_ranking_to_pairs(form_data)
                expected_pairs = len(pairs)
            else:
                # Count awareness questions to calculate expected pairs
                awareness_count = sum(
                    1
                    for i in range(total_questions)
                    if form_data.get(f"is_awareness_{i}") == "true"
                )
                expected_pairs = total_questions - awareness_count

                # Process traditional comparison pairs
                for i in range(total_questions):
                    if form_data.get(f"is_awareness_{i}") == "true":
                        continue

                    option_1 = list(
                        map(int, form_data.get(f"option1_{i}", "").split(","))
                    )
                    option_2 = list(
                        map(int, form_data.get(f"option2_{i}", "").split(","))
                    )
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

                    # Extract original pair number for interleaved strategies
                    original_pair_number_str = form_data.get(
                        f"original_pair_number_{i}", ""
                    )
                    original_pair_number = (
                        int(original_pair_number_str)
                        if original_pair_number_str
                        else None
                    )

                    # Extract generation metadata if available (for rank-based strategies)
                    generation_metadata_str = form_data.get(
                        f"generation_metadata_{i}", ""
                    )
                    generation_metadata = None
                    if generation_metadata_str:
                        try:
                            import json

                            generation_metadata = json.loads(generation_metadata_str)
                        except (json.JSONDecodeError, TypeError):
                            logger.warning(
                                f"Failed to parse generation_metadata for pair {i}"
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
                            original_pair_number=original_pair_number,
                            generation_metadata=generation_metadata,
                        )
                    )

            logger.info(
                "SurveySubmission.from_form_data built %s pairs; first_metadata=%s",
                len(pairs),
                pairs[0].generation_metadata if pairs else None,
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
