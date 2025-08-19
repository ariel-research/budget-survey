"""Test suite for ranking awareness check functionality."""

from unittest.mock import patch

import pytest

from application.schemas.validators import SurveySubmission
from application.services.awareness_check import generate_ranking_awareness_question
from application.services.survey_service import SurveySessionData


class TestRankingAwarenessGeneration:
    """Test awareness question generation for ranking surveys."""

    def test_awareness_question_generation_basic(self):
        """Test awareness question generates with user ideal as Option B."""
        user_vector = [90, 5, 5]
        question = generate_ranking_awareness_question(user_vector, 3)

        # User's ideal should be Option B (correct answer)
        assert question["option_b"] == tuple(user_vector)
        assert question["correct_answer"] == "B"
        assert question["is_awareness"] is True
        assert question["question_number"] == 3

        # Options A and C should be different from user's ideal
        assert question["option_a"] != tuple(user_vector)
        assert question["option_c"] != tuple(user_vector)

        # All options should sum to 100
        assert sum(question["option_a"]) == 100
        assert sum(question["option_b"]) == 100
        assert sum(question["option_c"]) == 100

        # All values should be within valid range
        for option in [
            question["option_a"],
            question["option_b"],
            question["option_c"],
        ]:
            assert all(0 <= val <= 100 for val in option)

    def test_awareness_question_generation_various_vectors(self):
        """Test awareness question generation with various user vectors."""
        test_vectors = [
            [35, 35, 30],
            [60, 25, 15],
            [20, 50, 30],
            [45, 30, 25],
        ]

        for user_vector in test_vectors:
            question = generate_ranking_awareness_question(user_vector, 3)

            # User's ideal should always be Option B
            assert question["option_b"] == tuple(user_vector)
            assert question["correct_answer"] == "B"

            # Options A and C should be clearly different
            assert question["option_a"] != tuple(user_vector)
            assert question["option_c"] != tuple(user_vector)
            assert question["option_a"] != question["option_c"]

    def test_awareness_question_validation_errors(self):
        """Test awareness question generation with invalid inputs."""
        # Wrong vector length
        with pytest.raises(ValueError, match="Vector length"):
            generate_ranking_awareness_question([50, 50], 3)

        # Vector doesn't sum to 100
        with pytest.raises(ValueError, match="Vector sum must be 100"):
            generate_ranking_awareness_question([50, 40, 5], 3)

        # Values out of range
        with pytest.raises(ValueError, match="Vector values must be between 0 and 95"):
            generate_ranking_awareness_question([100, 0, 0], 3)

        # Values too small (less than 5)
        with pytest.raises(
            ValueError, match="Non-zero vector values must be at least 5"
        ):
            generate_ranking_awareness_question([93, 3, 4], 3)


class TestRankingAwarenessValidation:
    """Test validation logic for ranking awareness checks."""

    def test_ranking_awareness_validation_success(self):
        """Test successful awareness validation."""
        # Mock form data for ranking survey with correct awareness answer
        form_data = {
            "user_vector": "35,35,30",
            "rank_1_q1": "A",  # Regular ranking question
            "rank_2_q1": "B",
            "rank_3_q1": "C",
            "rank_1_q2": "B",  # Regular ranking question
            "rank_2_q2": "A",
            "rank_3_q2": "C",
            "rank_1_q3": "B",  # Awareness question - correct answer
            "rank_2_q3": "A",
            "rank_3_q3": "C",
            "is_awareness_q3": "true",  # Mark as awareness question
            "rank_1_q4": "C",  # Regular ranking question
            "rank_2_q4": "A",
            "rank_3_q4": "B",
            "rank_1_q5": "A",  # Regular ranking question
            "rank_2_q5": "C",
            "rank_3_q5": "B",
            # Complete question metadata for all questions
            "question_1_option_a": "30,40,30",
            "question_1_option_b": "40,30,30",
            "question_1_option_c": "35,35,30",
            "question_1_magnitude": "6",
            "question_1_vector_type": "positive",
            "question_2_option_a": "25,45,30",
            "question_2_option_b": "45,25,30",
            "question_2_option_c": "35,35,30",
            "question_2_magnitude": "6",
            "question_2_vector_type": "negative",
            "question_3_option_a": "45,25,30",  # Awareness question options
            "question_3_option_b": "35,35,30",  # User's ideal (correct)
            "question_3_option_c": "25,45,30",
            "question_4_option_a": "23,47,30",
            "question_4_option_b": "47,23,30",
            "question_4_option_c": "35,35,30",
            "question_4_magnitude": "12",
            "question_4_vector_type": "positive",
            "question_5_option_a": "29,41,30",
            "question_5_option_b": "41,29,30",
            "question_5_option_c": "35,35,30",
            "question_5_magnitude": "12",
            "question_5_vector_type": "negative",
        }

        submission = SurveySubmission.from_form_data(form_data, "user123", 1)
        is_valid, error, status = submission.validate()

        assert is_valid is True
        assert error is None
        assert status == "complete"

    def test_ranking_awareness_validation_failure(self):
        """Test failed awareness validation."""
        # Mock form data for ranking survey with wrong awareness answer
        form_data = {
            "user_vector": "35,35,30",
            "rank_1_q1": "A",  # Regular ranking question
            "rank_2_q1": "B",
            "rank_3_q1": "C",
            "rank_1_q2": "B",  # Regular ranking question
            "rank_2_q2": "A",
            "rank_3_q2": "C",
            "rank_1_q3": "A",  # Awareness question - WRONG answer (should be B)
            "rank_2_q3": "B",
            "rank_3_q3": "C",
            "is_awareness_q3": "true",  # Mark as awareness question
            "rank_1_q4": "C",  # Regular ranking question
            "rank_2_q4": "A",
            "rank_3_q4": "B",
            "rank_1_q5": "A",  # Regular ranking question
            "rank_2_q5": "C",
            "rank_3_q5": "B",
            # Complete question metadata for all questions
            "question_1_option_a": "30,40,30",
            "question_1_option_b": "40,30,30",
            "question_1_option_c": "35,35,30",
            "question_1_magnitude": "6",
            "question_1_vector_type": "positive",
            "question_2_option_a": "25,45,30",
            "question_2_option_b": "45,25,30",
            "question_2_option_c": "35,35,30",
            "question_2_magnitude": "6",
            "question_2_vector_type": "negative",
            "question_3_option_a": "45,25,30",  # Awareness question options
            "question_3_option_b": "35,35,30",  # User's ideal (correct)
            "question_3_option_c": "25,45,30",
            "question_4_option_a": "23,47,30",
            "question_4_option_b": "47,23,30",
            "question_4_option_c": "35,35,30",
            "question_4_magnitude": "12",
            "question_4_vector_type": "positive",
            "question_5_option_a": "29,41,30",
            "question_5_option_b": "41,29,30",
            "question_5_option_c": "35,35,30",
            "question_5_magnitude": "12",
            "question_5_vector_type": "negative",
        }

        submission = SurveySubmission.from_form_data(form_data, "user123", 1)
        is_valid, error, status = submission.validate()

        assert is_valid is False
        assert status == "attention_failed"
        # Error message can be in Hebrew or English
        assert error is not None and len(error) > 0

    def test_traditional_survey_unaffected(self):
        """Ensure traditional surveys still work with existing awareness logic."""
        # Mock form data for traditional survey
        form_data = {
            "user_vector": "35,35,30",
            "awareness_check_0": 1,  # Traditional awareness checks
            "awareness_check_1": 2,
            "choice_0": 1,  # Regular comparison pairs
            "choice_1": 2,
            "option1_0": "30,35,35",
            "option2_0": "40,25,35",
            "option1_1": "25,40,35",
            "option2_1": "45,20,35",
            "option1_strategy_0": "Sum optimized",
            "option2_strategy_0": "Ratio optimized",
            "option1_strategy_1": "Sum optimized",
            "option2_strategy_1": "Ratio optimized",
            "is_awareness_0": "false",
            "is_awareness_1": "false",
            "was_swapped_0": "false",
            "was_swapped_1": "false",
        }

        submission = SurveySubmission.from_form_data(
            form_data, "user123", 1, total_questions=2
        )
        is_valid, error, status = submission.validate()

        assert is_valid is True
        assert error is None
        assert status == "complete"

    def test_traditional_survey_awareness_failure(self):
        """Test traditional survey awareness failure still works."""
        # Mock form data for traditional survey with wrong awareness answers
        form_data = {
            "user_vector": "35,35,30",
            "awareness_check_0": 2,  # Wrong - should be 1
            "awareness_check_1": 1,  # Wrong - should be 2
            "choice_0": 1,
            "choice_1": 2,
            "option1_0": "30,35,35",
            "option2_0": "40,25,35",
            "option1_1": "25,40,35",
            "option2_1": "45,20,35",
            "option1_strategy_0": "Sum optimized",
            "option2_strategy_0": "Ratio optimized",
            "option1_strategy_1": "Sum optimized",
            "option2_strategy_1": "Ratio optimized",
            "is_awareness_0": "false",
            "is_awareness_1": "false",
            "was_swapped_0": "false",
            "was_swapped_1": "false",
        }

        submission = SurveySubmission.from_form_data(
            form_data, "user123", 1, total_questions=2
        )
        is_valid, error, status = submission.validate()

        assert is_valid is False
        assert status == "attention_failed"


class TestRankingAwarenessPlacement:
    """Test awareness question placement in survey flow."""

    def test_awareness_question_placement(self):
        """Test that awareness question appears at position 3."""
        # Use mocks to avoid Flask application context issues
        from unittest.mock import MagicMock

        with (
            patch(
                "database.queries.get_survey_pair_generation_config"
            ) as mock_get_config,
            patch(
                "application.services.survey_service.SurveyService.generate_ranking_questions"
            ) as mock_generate_ranking,
            patch(
                "application.services.pair_generation.StrategyRegistry.get_strategy"
            ) as mock_get_strategy,
        ):

            # Mock database config
            mock_get_config.return_value = {
                "strategy": "preference_ranking_survey",
                "params": {"num_pairs": 12},
            }

            # Mock strategy to be ranking-based
            mock_strategy = MagicMock()
            mock_strategy.is_ranking_based.return_value = True
            mock_get_strategy.return_value = mock_strategy

            # Mock ranking questions generation
            mock_ranking_questions = [
                {"question_number": 1, "magnitude": 6, "vector_type": "positive"},
                {"question_number": 2, "magnitude": 6, "vector_type": "negative"},
                {"question_number": 4, "magnitude": 12, "vector_type": "positive"},
                {"question_number": 5, "magnitude": 12, "vector_type": "negative"},
            ]
            mock_generate_ranking.return_value = mock_ranking_questions

            # Create session data
            session_data = SurveySessionData(
                user_id="test_user",
                internal_survey_id=1,
                external_survey_id="ext123",
                user_vector=[35, 35, 30],
                subjects=["Health", "Education", "Defense"],
            )

            # Get template data
            template_data = session_data.to_template_data()

            # Verify structure
            assert "ranking_questions" in template_data
            assert "awareness_positions" in template_data
            assert (
                len(template_data["ranking_questions"]) == 5
            )  # 4 ranking + 1 awareness
            assert template_data["awareness_positions"] == [
                2
            ]  # 0-indexed position 2 = question 3

            # Verify awareness question is at position 3 (index 2)
            awareness_question = template_data["ranking_questions"][2]
            assert awareness_question["is_awareness"] is True
            assert awareness_question["question_number"] == 3
            assert awareness_question["option_b"] == tuple([35, 35, 30])  # User's ideal


class TestRankingAwarenessIntegration:
    """Integration tests for ranking awareness functionality."""

    def test_full_ranking_survey_flow(self):
        """Test complete flow from question generation to validation."""
        user_vector = [60, 25, 15]

        # Generate awareness question
        awareness_question = generate_ranking_awareness_question(user_vector, 3)

        # Verify question structure
        assert awareness_question["is_awareness"] is True
        assert awareness_question["option_b"] == tuple(user_vector)
        assert awareness_question["correct_answer"] == "B"

        # Simulate correct form submission
        form_data = {
            "user_vector": "60,25,15",
            "rank_1_q3": "B",  # Correct awareness answer
            "rank_2_q3": "A",
            "rank_3_q3": "C",
            "question_3_option_a": ",".join(map(str, awareness_question["option_a"])),
            "question_3_option_b": ",".join(map(str, awareness_question["option_b"])),
            "question_3_option_c": ",".join(map(str, awareness_question["option_c"])),
            "is_awareness_q3": "true",
        }

        # Create submission
        submission = SurveySubmission.from_form_data(form_data, "user123", 1)

        # Validate
        is_valid, error, status = submission.validate()

        assert is_valid is True
        assert status == "complete"
        assert len(submission.awareness_answers) == 1
        assert submission.awareness_answers[0] == "B"

    def test_edge_case_minimal_vector(self):
        """Test awareness generation with minimal valid vector."""
        user_vector = [90, 5, 5]  # Minimal case

        # Should still generate valid awareness question
        question = generate_ranking_awareness_question(user_vector, 3)

        assert question["option_b"] == tuple(user_vector)
        assert question["correct_answer"] == "B"

        # All options should be valid
        for option in [
            question["option_a"],
            question["option_b"],
            question["option_c"],
        ]:
            assert sum(option) == 100
            assert all(0 <= val <= 100 for val in option)

    def test_awareness_question_not_stored_in_database(self):
        """Test that awareness questions are filtered out of database storage."""
        # Mock form data for ranking survey with awareness question at position 3
        form_data = {
            "user_vector": "35,35,30",
            "rank_1_q1": "A",  # Regular ranking question
            "rank_2_q1": "B",
            "rank_3_q1": "C",
            "rank_1_q2": "B",  # Regular ranking question
            "rank_2_q2": "A",
            "rank_3_q2": "C",
            "rank_1_q3": "B",  # Awareness question - should be excluded
            "rank_2_q3": "A",
            "rank_3_q3": "C",
            "is_awareness_q3": "true",  # Mark as awareness question
            "rank_1_q4": "C",  # Regular ranking question
            "rank_2_q4": "A",
            "rank_3_q4": "B",
            "rank_1_q5": "A",  # Regular ranking question
            "rank_2_q5": "C",
            "rank_3_q5": "B",
            # Complete question metadata for all questions
            "question_1_option_a": "30,40,30",
            "question_1_option_b": "40,30,30",
            "question_1_option_c": "35,35,30",
            "question_1_magnitude": "6",
            "question_1_vector_type": "positive",
            "question_2_option_a": "25,45,30",
            "question_2_option_b": "45,25,30",
            "question_2_option_c": "35,35,30",
            "question_2_magnitude": "6",
            "question_2_vector_type": "negative",
            "question_3_option_a": "45,25,30",  # Awareness question options
            "question_3_option_b": "35,35,30",  # User's ideal (correct)
            "question_3_option_c": "25,45,30",
            "question_4_option_a": "23,47,30",
            "question_4_option_b": "47,23,30",
            "question_4_option_c": "35,35,30",
            "question_4_magnitude": "12",
            "question_4_vector_type": "positive",
            "question_5_option_a": "29,41,30",
            "question_5_option_b": "41,29,30",
            "question_5_option_c": "35,35,30",
            "question_5_magnitude": "12",
            "question_5_vector_type": "negative",
        }

        submission = SurveySubmission.from_form_data(form_data, "user123", 1)

        # Should have exactly 12 comparison pairs (4 questions × 3 pairs each)
        # Question 3 (awareness) should be excluded from database storage
        assert len(submission.comparison_pairs) == 12

        # Verify no pairs contain awareness question references
        awareness_pairs = [
            pair
            for pair in submission.comparison_pairs
            if "Q3" in pair.option1_strategy or "Q3" in pair.option2_strategy
        ]
        assert len(awareness_pairs) == 0, f"Found awareness pairs: {awareness_pairs}"

        # Verify we have pairs for Q1, Q2, Q4, Q5 (but not Q3)
        question_numbers = set()
        for pair in submission.comparison_pairs:
            # Extract question number from strategy string
            strategy = pair.option1_strategy
            if "Q" in strategy:
                q_part = strategy.split("Q")[1].split(" ")[0]
                question_numbers.add(int(q_part))

        expected_questions = {1, 2, 4, 5}  # No Q3 (awareness)
        assert question_numbers == expected_questions

        # Awareness validation should still work
        is_valid, error, status = submission.validate()
        assert is_valid is True  # Correct awareness answer
        assert status == "complete"
