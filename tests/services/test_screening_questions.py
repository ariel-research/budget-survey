"""Test suite for screening question generation."""

import pytest

from application.services.survey_service import SurveyService


class TestScreeningQuestions:
    """Tests for generate_screening_questions method."""

    def test_generates_two_questions(self):
        """Test that exactly 2 screening questions are generated."""
        user_vector = [60, 30, 10]
        subjects = ["Health", "Education", "Defense"]

        questions = SurveyService.generate_screening_questions(user_vector, subjects)

        assert len(questions) == 2
        assert questions[0]["question_number"] == 1
        assert questions[1]["question_number"] == 2

    def test_question_structure(self):
        """Test that each question has required fields."""
        user_vector = [60, 30, 10]
        subjects = ["Health", "Education", "Defense"]

        questions = SurveyService.generate_screening_questions(user_vector, subjects)

        for q in questions:
            assert "question_number" in q
            assert "fixed_year" in q
            assert "fixed_budget" in q
            assert "option_a" in q
            assert "option_b" in q
            assert "correct_answer" in q
            assert "prompt_key" in q

    def test_no_identical_options_in_question(self):
        """
        Test that option_a and option_b are never identical.

        This is a regression test for the bug where enumerate()
        caused r = user_vector, making both options identical.
        """
        user_vector = [60, 30, 10]
        subjects = ["Health", "Education", "Defense"]

        # Run multiple times to catch probabilistic failures
        for run in range(10):
            questions = SurveyService.generate_screening_questions(
                user_vector, subjects
            )

            for q in questions:
                option_a = q["option_a"]
                option_b = q["option_b"]

                assert option_a != option_b, (
                    f"Question {q['question_number']} (run {run + 1}) has "
                    f"identical options!\n"
                    f"  Option A: {option_a}\n"
                    f"  Option B: {option_b}\n"
                    f"  Fixed budget: {q['fixed_budget']}\n"
                    f"  User vector: {user_vector}"
                )

    def test_fixed_budget_different_from_user_vector(self):
        """Test that fixed budget is different from user's ideal vector."""
        user_vector = [60, 30, 10]
        subjects = ["Health", "Education", "Defense"]

        questions = SurveyService.generate_screening_questions(user_vector, subjects)

        for q in questions:
            fixed_budget = q["fixed_budget"]
            assert fixed_budget != tuple(user_vector), (
                f"Question {q['question_number']} has fixed_budget "
                f"identical to user_vector: {fixed_budget}"
            )

    def test_balancing_vector_is_valid(self):
        """Test that balancing vectors have all values in [0, 100]."""
        user_vector = [60, 30, 10]
        subjects = ["Health", "Education", "Defense"]

        questions = SurveyService.generate_screening_questions(user_vector, subjects)

        for q in questions:
            # Check all options are valid budgets
            for option_name, option in [
                ("option_a", q["option_a"]),
                ("option_b", q["option_b"]),
            ]:
                assert all(0 <= v <= 100 for v in option), (
                    f"Question {q['question_number']} {option_name} has "
                    f"invalid values: {option}"
                )
                assert sum(option) == 100, (
                    f"Question {q['question_number']} {option_name} doesn't "
                    f"sum to 100: {option} (sum={sum(option)})"
                )

    def test_user_ideal_appears_exactly_once_per_question(self):
        """Test that user's ideal vector appears as one option in each question."""
        user_vector = [60, 30, 10]
        subjects = ["Health", "Education", "Defense"]

        questions = SurveyService.generate_screening_questions(user_vector, subjects)

        # Question 1: option_a should be user_vector (correct_answer=1)
        assert questions[0]["option_a"] == tuple(user_vector)
        assert questions[0]["option_b"] != tuple(user_vector)
        assert questions[0]["correct_answer"] == 1

        # Question 2: option_b should be user_vector (correct_answer=2)
        assert questions[1]["option_a"] != tuple(user_vector)
        assert questions[1]["option_b"] == tuple(user_vector)
        assert questions[1]["correct_answer"] == 2

    def test_balancing_property(self):
        """
        Test that balancing vector satisfies: (r + q_balance) / 2 = user_vector.

        This is the mathematical property that screening questions test.
        """
        user_vector = [60, 30, 10]
        subjects = ["Health", "Education", "Defense"]

        questions = SurveyService.generate_screening_questions(user_vector, subjects)

        for q in questions:
            fixed_budget = q["fixed_budget"]

            # Identify which option is the balancing vector
            if q["option_a"] == tuple(user_vector):
                balancing = q["option_b"]
            else:
                balancing = q["option_a"]

            # Verify balancing property: (r + q_balance) / 2 = p
            average = tuple(
                (fixed_budget[i] + balancing[i]) / 2 for i in range(len(user_vector))
            )

            # Allow small floating point error
            for i, val in enumerate(average):
                assert abs(val - user_vector[i]) < 0.01, (
                    f"Question {q['question_number']} balancing property failed:\n"
                    f"  Fixed: {fixed_budget}\n"
                    f"  Balancing: {balancing}\n"
                    f"  Average: {average}\n"
                    f"  Expected: {user_vector}"
                )

    def test_different_fixed_budgets_between_questions(self):
        """Test that Question 1 and Question 2 use different fixed budgets."""
        user_vector = [60, 30, 10]
        subjects = ["Health", "Education", "Defense"]

        questions = SurveyService.generate_screening_questions(user_vector, subjects)

        fixed_budget_1 = questions[0]["fixed_budget"]
        fixed_budget_2 = questions[1]["fixed_budget"]

        assert (
            fixed_budget_1 != fixed_budget_2
        ), f"Both questions use the same fixed budget: {fixed_budget_1}"

    def test_works_with_edge_case_vectors(self):
        """Test screening generation works with edge case user vectors."""
        edge_cases = [
            [90, 5, 5],  # Extreme concentration
            [5, 5, 90],  # Different extreme
            [10, 10, 80],  # Another extreme
            [50, 25, 25],  # Balanced
            [70, 20, 10],  # Moderate
        ]
        subjects = ["Health", "Education", "Defense"]

        for user_vector in edge_cases:
            questions = SurveyService.generate_screening_questions(
                user_vector, subjects
            )

            # Verify basic properties
            assert len(questions) == 2

            for q in questions:
                # No identical options
                assert q["option_a"] != q["option_b"], (
                    f"Identical options for user_vector {user_vector}: "
                    f"{q['option_a']}"
                )

                # All options are valid
                assert all(0 <= v <= 100 for v in q["option_a"])
                assert all(0 <= v <= 100 for v in q["option_b"])
                assert sum(q["option_a"]) == 100
                assert sum(q["option_b"]) == 100

    def test_values_are_multiples_of_5(self):
        """Test that all generated values are multiples of 5."""
        user_vector = [60, 30, 10]
        subjects = ["Health", "Education", "Defense"]

        questions = SurveyService.generate_screening_questions(user_vector, subjects)

        for q in questions:
            for option_name, option in [
                ("fixed_budget", q["fixed_budget"]),
                ("option_a", q["option_a"]),
                ("option_b", q["option_b"]),
            ]:
                for i, val in enumerate(option):
                    assert val % 5 == 0, (
                        f"Question {q['question_number']} {option_name}[{i}] = {val} "
                        f"is not a multiple of 5"
                    )

    def test_deterministic_with_seed(self):
        """Test that results are deterministic when random seed is set."""
        import random

        user_vector = [60, 30, 10]
        subjects = ["Health", "Education", "Defense"]

        # Generate with seed 1
        random.seed(42)
        questions1 = SurveyService.generate_screening_questions(user_vector, subjects)

        # Generate with same seed
        random.seed(42)
        questions2 = SurveyService.generate_screening_questions(user_vector, subjects)

        # Should be identical
        assert questions1[0]["fixed_budget"] == questions2[0]["fixed_budget"]
        assert questions1[1]["fixed_budget"] == questions2[1]["fixed_budget"]

    def test_retry_loop_eventually_succeeds(self):
        """
        Test that retry loop handles difficult cases.

        For some user vectors, most random choices produce invalid balancing
        vectors. This test ensures the retry loop handles these cases.
        """
        # These vectors make it harder to find valid balancing pairs
        difficult_vectors = [
            [80, 15, 5],  # Challenging but feasible
            [15, 80, 5],  # Extreme in different position
            [70, 25, 5],  # Another challenging case
        ]
        subjects = ["Health", "Education", "Defense"]

        for user_vector in difficult_vectors:
            # Should not raise an error
            questions = SurveyService.generate_screening_questions(
                user_vector, subjects
            )

            assert len(questions) == 2

            # Verify no identical options (the bug we're testing)
            for q in questions:
                assert q["option_a"] != q["option_b"]

    def test_extremely_constrained_vectors_handled(self):
        """
        Test that extremely constrained vectors either succeed or raise clear error.

        Some vectors like [95, 3, 2] have very narrow valid ranges for r such that
        q_balance = 2*p - r stays in [0,100]. If generation fails, it should raise
        a clear ValueError rather than producing incorrect results.
        """
        # These are mathematically very constrained
        extreme_vectors = [
            [95, 3, 2],  # Requires r[0] in [90, 100] - very narrow!
            [2, 95, 3],  # Similar constraint
        ]
        subjects = ["Health", "Education", "Defense"]

        for user_vector in extreme_vectors:
            try:
                questions = SurveyService.generate_screening_questions(
                    user_vector, subjects
                )

                # If it succeeds, verify correctness
                assert len(questions) == 2
                for q in questions:
                    # Most importantly: no identical options (the bug)
                    assert q["option_a"] != q["option_b"]
                    # All values valid
                    assert all(0 <= v <= 100 for v in q["option_a"])
                    assert all(0 <= v <= 100 for v in q["option_b"])

            except ValueError as e:
                # It's acceptable to raise ValueError for impossible cases
                assert "Unable to generate valid screening pair" in str(e)
                # This is better than generating incorrect identical options!


class TestScreeningQuestionsRegressionBug:
    """
    Specific regression tests for the enumerate() bug.

    The bug was: using enumerate(user_vector) instead of range(len(user_vector))
    caused r = user_vector, making q_balance = user_vector, creating identical options.
    """

    def test_no_enumerate_bug_question_1(self):
        """Test Question 1 doesn't have the enumerate bug."""
        user_vector = [60, 30, 10]
        subjects = ["Health", "Education", "Defense"]

        for _ in range(20):  # Run multiple times
            questions = SurveyService.generate_screening_questions(
                user_vector, subjects
            )
            q1 = questions[0]

            # The bug made option_a == option_b == user_vector
            assert q1["option_a"] != q1["option_b"], (
                "Question 1 has identical options (enumerate bug):\n"
                f"  option_a: {q1['option_a']}\n"
                f"  option_b: {q1['option_b']}\n"
                f"  fixed_budget: {q1['fixed_budget']}"
            )

            # Also verify fixed_budget != user_vector
            assert q1["fixed_budget"] != tuple(
                user_vector
            ), "Question 1 fixed_budget equals user_vector (enumerate bug)"

    def test_no_enumerate_bug_question_2(self):
        """Test Question 2 doesn't have the enumerate bug."""
        user_vector = [60, 30, 10]
        subjects = ["Health", "Education", "Defense"]

        for _ in range(20):  # Run multiple times
            questions = SurveyService.generate_screening_questions(
                user_vector, subjects
            )
            q2 = questions[1]

            # The bug made option_a == option_b == user_vector
            assert q2["option_a"] != q2["option_b"], (
                "Question 2 has identical options (enumerate bug):\n"
                f"  option_a: {q2['option_a']}\n"
                f"  option_b: {q2['option_b']}\n"
                f"  fixed_budget: {q2['fixed_budget']}"
            )

            # Also verify fixed_budget != user_vector
            assert q2["fixed_budget"] != tuple(
                user_vector
            ), "Question 2 fixed_budget equals user_vector (enumerate bug)"

    def test_specific_bug_scenario(self):
        """
        Test the exact scenario from the screenshot.

        User vector: (60, 30, 10)
        Bug caused: fixed_budget = (60, 30, 10) and both options = (60, 30, 10)
        """
        user_vector = [60, 30, 10]
        subjects = ["Health", "Education", "Defense"]

        # Run many times to ensure bug doesn't occur
        for run in range(50):
            questions = SurveyService.generate_screening_questions(
                user_vector, subjects
            )

            for q in questions:
                # Bug symptom 1: fixed_budget == user_vector
                if q["fixed_budget"] == tuple(user_vector):
                    pytest.fail(
                        f"Run {run + 1}, Q{q['question_number']}: "
                        f"fixed_budget equals user_vector {user_vector}"
                    )

                # Bug symptom 2: option_a == option_b
                if q["option_a"] == q["option_b"]:
                    pytest.fail(
                        f"Run {run + 1}, Q{q['question_number']}: "
                        f"Identical options {q['option_a']}"
                    )

                # Bug symptom 3: All three are the same
                if (
                    q["fixed_budget"] == tuple(user_vector)
                    and q["option_a"] == tuple(user_vector)
                    and q["option_b"] == tuple(user_vector)
                ):
                    pytest.fail(
                        f"Run {run + 1}, Q{q['question_number']}: "
                        f"All values equal user_vector {user_vector} - "
                        f"This is the exact bug from the screenshot!"
                    )
