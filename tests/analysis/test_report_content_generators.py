import json
from unittest.mock import patch

import pytest

from analysis.report_content_generators import (
    _calculate_cyclic_shift_group_consistency,
    _deduce_rankings,
    _generate_cyclic_shift_consistency_table,
    _generate_final_ranking_summary_table,
    _generate_preference_ranking_pairwise_table,
    calculate_user_consistency,
    generate_detailed_user_choices,
    generate_executive_summary,
    generate_individual_analysis,
    generate_key_findings,
    generate_methodology_description,
    generate_overall_stats,
    generate_preference_ranking_consistency_tables,
    generate_survey_analysis,
    get_summary_value,
)


def test_get_summary_value(sample_summary_stats):
    """Test extraction of values from summary statistics."""
    assert get_summary_value(sample_summary_stats, "total_answers") == 80
    assert get_summary_value(sample_summary_stats, "sum_optimized") == 45
    assert get_summary_value(sample_summary_stats, "total_survey_responses") == 8


def test_calculate_user_consistency(sample_optimization_stats):
    """Test calculation of user consistency metrics."""
    consistency_pct, qualified_users, total_users, min_surveys, total_surveys = (
        calculate_user_consistency(sample_optimization_stats)
    )

    assert total_surveys == 2
    assert min_surveys == 2
    assert total_users == 3
    assert qualified_users == 1  # Only user 101 took both surveys
    assert consistency_pct == 100.0  # User 101 was consistent (sum preference)


def test_generate_executive_summary(
    sample_summary_stats, sample_optimization_stats, sample_survey_responses
):
    """Test generation of executive summary."""
    summary = generate_executive_summary(
        sample_summary_stats, sample_optimization_stats, sample_survey_responses
    )

    assert isinstance(summary, str)
    assert "2 surveys" in summary
    assert "8" in summary
    assert "80 answers" in summary
    assert "56.25% sum vs 43.75% ratio" in summary


def test_generate_overall_stats(sample_summary_stats, sample_optimization_stats):
    """Test generation of overall statistics."""
    stats = generate_overall_stats(sample_summary_stats, sample_optimization_stats)

    assert isinstance(stats, str)
    assert "Survey Overview" in stats
    assert "Total survey responses: 8" in stats
    assert "Total answers collected: 80" in stats
    assert "Participation Statistics" in stats
    assert "Response Details" in stats
    assert "Unique participants: 3" in stats
    assert "Participants who took multiple surveys: 5" in stats


def test_generate_survey_analysis(sample_summary_stats):
    """Test generation of survey-specific analysis."""
    analysis = generate_survey_analysis(sample_summary_stats)

    assert isinstance(analysis, str)
    assert "Survey 1" in analysis
    assert "5 participants" in analysis
    assert "Survey 2" in analysis
    assert "3 participants" in analysis
    assert "Sum optimization: 60.00%" in analysis
    assert "Ratio optimization: 50.00%" in analysis
    assert "Individual user preferences" in analysis
    assert "users preferred sum optimization" in analysis
    assert "users preferred ratio optimization" in analysis


def test_generate_individual_analysis(sample_optimization_stats):
    """Test generation of individual user analysis."""
    analysis = generate_individual_analysis(sample_optimization_stats)

    assert isinstance(analysis, str)
    assert "User 101" in analysis
    assert "User 102" in analysis
    assert "User 103" in analysis
    assert "70.0% sum, 30.0% ratio optimized" in analysis  # User 101


def test_generate_key_findings(sample_summary_stats, sample_optimization_stats):
    """Test generation of key findings."""
    findings = generate_key_findings(sample_summary_stats, sample_optimization_stats)

    assert isinstance(findings, str)
    assert "Overall Preference" in findings
    assert "Individual Consistency" in findings
    assert "Most Common Preference" in findings


def test_generate_methodology_description():
    """Test generation of methodology description."""
    methodology = generate_methodology_description()

    assert isinstance(methodology, str)
    assert "Data Collection" in methodology
    assert "Data Processing" in methodology
    assert "Analysis" in methodology
    assert "Visualization" in methodology
    assert "Reporting" in methodology


def test_generate_detailed_user_choices_empty(test_request_context, mock_translations):
    """Test generate_detailed_user_choices with empty input."""
    with patch(
        "analysis.report_content_generators.get_translation"
    ) as mock_get_translation:
        mock_get_translation.side_effect = (
            lambda key, section, **kwargs: mock_translations.get(key, f"[{key}]")
        )

        option_labels = ("Sum Optimized Vector", "Ratio Optimized Vector")
        result = generate_detailed_user_choices([], option_labels)
        assert isinstance(result, dict)
        assert "No detailed user choice data available" in result["combined_html"]


def test_generate_detailed_user_choices_single_user(
    test_request_context, mock_translations
):
    """Test generate_detailed_user_choices with a single user's data."""
    option_labels = ("Sum Optimized Vector", "Ratio Optimized Vector")
    test_data = [
        {
            "user_id": "test123",
            "survey_id": 1,
            "optimal_allocation": json.dumps([50, 30, 20]),
            "pair_number": 1,
            "option_1": json.dumps([50, 40, 10]),  # better sum
            "option_2": json.dumps([30, 50, 20]),  # better ratio
            "user_choice": 2,  # Choosing option 2 -- ratio optimization
        }
    ]

    with patch(
        "analysis.report_content_generators.get_translation"
    ) as mock_get_translation:
        mock_get_translation.side_effect = (
            lambda key, section, **kwargs: mock_translations.get(key, f"[{key}]")
        )

        result = generate_detailed_user_choices(test_data, option_labels)

        assert isinstance(result, dict)
        combined_html = result["combined_html"]
        assert "test123" in combined_html  # User ID appears in the HTML
        assert "1" in combined_html  # Survey ID appears in the HTML
        assert "[50, 30, 20]" in combined_html  # Ideal budget appears
        assert "Sum Optimized Vector" in combined_html
        assert "Ratio Optimized Vector" in combined_html


def test_generate_detailed_user_choices_multiple_optimizations(
    test_request_context, mock_translations
):
    """Test generate_detailed_user_choices with both sum and ratio optimizations."""
    optimal = [50, 30, 20]  # Base optimal allocation
    option_labels = ("Sum Optimized Vector", "Ratio Optimized Vector")
    test_data = [
        {
            "user_id": "test123",
            "survey_id": 1,
            "optimal_allocation": json.dumps(optimal),
            "pair_number": 1,
            "option_1": json.dumps([50, 40, 10]),  # better sum
            "option_2": json.dumps([30, 50, 20]),  # better ratio
            "user_choice": 2,  # Choosing option 2 -- ratio optimization
        },
        {
            "user_id": "test123",
            "survey_id": 1,
            "optimal_allocation": json.dumps(optimal),
            "pair_number": 2,
            "option_1": json.dumps([50, 40, 10]),  # better sum
            "option_2": json.dumps([30, 50, 20]),  # better ratio
            "user_choice": 1,  # Choosing option 1 -- sum optimization
        },
    ]

    with patch(
        "analysis.report_content_generators.get_translation"
    ) as mock_get_translation:
        mock_get_translation.side_effect = (
            lambda key, section, **kwargs: mock_translations.get(key, f"[{key}]")
        )

        result = generate_detailed_user_choices(test_data, option_labels)

        assert isinstance(result, dict)
        combined_html = result["combined_html"]
        assert "Sum Optimized Vector" in combined_html
        assert "Ratio Optimized Vector" in combined_html
        # Check for pair numbers in the HTML content
        assert "1" in combined_html  # Pair number 1
        assert "2" in combined_html  # Pair number 2


def test_generate_detailed_user_choices_multiple_surveys(
    test_request_context, mock_translations
):
    """Test generate_detailed_user_choices with multiple surveys for the same user."""
    option_labels = ("Sum Optimized Vector", "Ratio Optimized Vector")
    test_data = [
        {
            "user_id": "test123",
            "survey_id": 1,
            "optimal_allocation": json.dumps([25, 25, 50]),
            "pair_number": 1,
            "option_1": json.dumps([30, 20, 50]),
            "option_2": json.dumps([10, 60, 30]),
            "user_choice": 1,
        },
        {
            "user_id": "test123",
            "survey_id": 2,
            "optimal_allocation": json.dumps([40, 40, 20]),
            "pair_number": 1,
            "option_1": json.dumps([35, 35, 30]),
            "option_2": json.dumps([45, 45, 10]),
            "user_choice": 2,
        },
    ]

    with patch(
        "analysis.report_content_generators.get_translation"
    ) as mock_get_translation:
        mock_get_translation.side_effect = (
            lambda key, section, **kwargs: mock_translations.get(key, f"[{key}]")
        )

        result = generate_detailed_user_choices(test_data, option_labels)

        assert isinstance(result, dict)
        combined_html = result["combined_html"]
        assert "1" in combined_html  # Survey ID 1
        assert "2" in combined_html  # Survey ID 2
        assert "[25, 25, 50]" in combined_html  # First ideal budget
        assert "[40, 40, 20]" in combined_html  # Second ideal budget


def test_generate_detailed_user_choices_css_classes(
    test_request_context, mock_translations
):
    """Test that generate_detailed_user_choices includes correct CSS classes."""
    option_labels = ("Sum Optimized Vector", "Ratio Optimized Vector")
    test_data = [
        {
            "user_id": "test123",
            "survey_id": 1,
            "optimal_allocation": json.dumps([50, 30, 20]),
            "pair_number": 1,
            "option_1": json.dumps([50, 40, 10]),  # better sum
            "option_2": json.dumps([30, 50, 20]),  # better ratio
            "user_choice": 2,  # Choosing option 2 -- ratio optimization
        }
    ]

    with patch(
        "analysis.report_content_generators.get_translation"
    ) as mock_get_translation:
        mock_get_translation.side_effect = (
            lambda key, section, **kwargs: mock_translations.get(key, f"[{key}]")
        )

        result = generate_detailed_user_choices(test_data, option_labels)

        assert isinstance(result, dict)
        combined_html = result["combined_html"]

        # Check CSS classes
        assert 'class="user-choices"' in combined_html
        assert 'class="survey-choices"' in combined_html
        assert 'class="pairs-list"' in combined_html
        assert 'class="ideal-budget"' in combined_html
        assert 'class="selection-column"' in combined_html
        assert 'class="option-column"' in combined_html


def test_cyclic_shift_group_consistency():
    """Test cyclic shift group consistency calculation with binary metric."""
    # Mock choices for cyclic shift strategy with binary consistency
    # Group 1: AAB = 0% (not all same)
    # Group 2: AAA = 100% (all same)
    # Group 3: ABB = 0% (not all same)
    # Group 4: AB (incomplete) = 0% (incomplete group)
    choices = [
        # Group 1 (pairs 1-3)
        {
            "pair_number": 1,
            "option1_strategy": "Cyclic Pattern A (shift 0)",
            "option2_strategy": "Cyclic Pattern B (shift 0)",
            "user_choice": 1,
        },
        {
            "pair_number": 2,
            "option1_strategy": "Cyclic Pattern A (shift 1)",
            "option2_strategy": "Cyclic Pattern B (shift 1)",
            "user_choice": 1,
        },
        {
            "pair_number": 3,
            "option1_strategy": "Cyclic Pattern A (shift 2)",
            "option2_strategy": "Cyclic Pattern B (shift 2)",
            "user_choice": 2,
        },
        # Group 2 (pairs 4-6)
        {
            "pair_number": 4,
            "option1_strategy": "Cyclic Pattern A (shift 0)",
            "option2_strategy": "Cyclic Pattern B (shift 0)",
            "user_choice": 1,
        },
        {
            "pair_number": 5,
            "option1_strategy": "Cyclic Pattern A (shift 1)",
            "option2_strategy": "Cyclic Pattern B (shift 1)",
            "user_choice": 1,
        },
        {
            "pair_number": 6,
            "option1_strategy": "Cyclic Pattern A (shift 2)",
            "option2_strategy": "Cyclic Pattern B (shift 2)",
            "user_choice": 1,
        },
        # Group 3 (pairs 7-9)
        {
            "pair_number": 7,
            "option1_strategy": "Cyclic Pattern A (shift 0)",
            "option2_strategy": "Cyclic Pattern B (shift 0)",
            "user_choice": 2,
        },
        {
            "pair_number": 8,
            "option1_strategy": "Cyclic Pattern A (shift 1)",
            "option2_strategy": "Cyclic Pattern B (shift 1)",
            "user_choice": 2,
        },
        {
            "pair_number": 9,
            "option1_strategy": "Cyclic Pattern A (shift 2)",
            "option2_strategy": "Cyclic Pattern B (shift 2)",
            "user_choice": 1,
        },
        # Group 4 (pairs 10-11, missing pair 12)
        {
            "pair_number": 10,
            "option1_strategy": "Cyclic Pattern A (shift 0)",
            "option2_strategy": "Cyclic Pattern B (shift 0)",
            "user_choice": 1,
        },
        {
            "pair_number": 11,
            "option1_strategy": "Cyclic Pattern A (shift 1)",
            "option2_strategy": "Cyclic Pattern B (shift 1)",
            "user_choice": 2,
        },
    ]

    # Test consistency calculation
    consistencies = _calculate_cyclic_shift_group_consistency(choices)

    # Verify binary group consistencies
    assert consistencies["group_1"] == 0.0  # AAB = 0% (not all same)
    assert consistencies["group_2"] == 100.0  # AAA = 100% (all same)
    assert consistencies["group_3"] == 0.0  # ABB = 0% (not all same)
    assert consistencies["group_4"] == 0.0  # AB (incomplete) = 0%

    # Verify overall consistency (percentage of groups that are 100% consistent)
    # Only 1 out of 4 groups is 100% consistent
    assert consistencies["overall"] == 25.0  # 1/4 = 25%

    # Test HTML table generation with mocked translations
    with patch(
        "analysis.report_content_generators.get_translation"
    ) as mock_translation:
        # Mock translation to return English text for testing
        def mock_get_translation(key, section=None, **kwargs):
            translations = {
                "group_consistency": "Group Consistency",
                "group": "Group",
                "consistency_percent": "Consistency Percentage",
                "overall": "Overall",
                "consistency_explanation": (
                    "Higher percentages indicate more consistent choices "
                    "within each group"
                ),
            }
            return translations.get(key, f"[{key}]")

        mock_translation.side_effect = mock_get_translation

        table_html = _generate_cyclic_shift_consistency_table(choices)

        # Verify table contains expected binary consistency elements
        assert "Group Consistency" in table_html
        assert "0%" in table_html  # Groups 1, 3, 4 are 0%
        assert "100%" in table_html  # Group 2 is 100%
        assert "25%" in table_html  # Overall is 25%
        assert "Group 1" in table_html
        assert "Group 2" in table_html
        assert "Group 3" in table_html
        assert "Group 4" in table_html
        assert "Overall" in table_html
        # Verify binary consistency icons
        assert "✓" in table_html  # Checkmark for consistent group
        assert "✗" in table_html  # X mark for inconsistent groups


def create_preference_ranking_choice(
    question_label, pair_type, magnitude, vector_type, user_choice
):
    """Helper function to create a choice dictionary for preference ranking tests."""
    # Map question and pair type to pair number
    question_map = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}
    pair_type_map = {"A vs B": 1, "A vs C": 2, "B vs C": 3}

    question_num = question_map[question_label]
    pair_type_num = pair_type_map[pair_type]
    pair_number = (question_num - 1) * 3 + pair_type_num

    # Calculate ideal allocation that would produce the given magnitudes
    # For consistent testing, we need to use the same ideal allocation for all questions
    # Using [40, 30, 30] with min=30: X1 = 0.2 * 30 = 6, X2 = 0.4 * 30 = 12
    ideal_allocation = [40, 30, 30]  # min=30, X1=6, X2=12

    # Generate sample option vectors based on the pair type and question
    # This is simplified for testing - in reality these would come from the strategy
    if pair_type == "A vs B":
        option_1 = [
            ideal_allocation[0] + 5,
            ideal_allocation[1] - 2,
            ideal_allocation[2] - 3,
        ]
        option_2 = [
            ideal_allocation[0] - 3,
            ideal_allocation[1] + 5,
            ideal_allocation[2] - 2,
        ]
    elif pair_type == "A vs C":
        option_1 = [
            ideal_allocation[0] + 5,
            ideal_allocation[1] - 2,
            ideal_allocation[2] - 3,
        ]
        option_2 = [
            ideal_allocation[0] - 3,
            ideal_allocation[1] - 2,
            ideal_allocation[2] + 5,
        ]
    else:  # B vs C
        option_1 = [
            ideal_allocation[0] - 2,
            ideal_allocation[1] + 5,
            ideal_allocation[2] - 3,
        ]
        option_2 = [
            ideal_allocation[0] - 2,
            ideal_allocation[1] - 3,
            ideal_allocation[2] + 5,
        ]

    return {
        "pair_number": pair_number,
        "user_choice": user_choice,
        "option_1": option_1,
        "option_2": option_2,
        "optimal_allocation": ideal_allocation,
        "option1_strategy": "Option A",
        "option2_strategy": "Option B",
    }


def test_deduce_rankings_perfectly_consistent():
    """Test _deduce_rankings with perfectly consistent user (Example 1)."""
    # Create choices for perfectly consistent user: A > B > C for all questions
    # Based on ideal vector (40, 30, 30) with X1=6, X2=12
    choices = [
        # Question 1 (X1=6, positive): All pairs result in A > B > C
        create_preference_ranking_choice("Q1", "A vs B", 6, "positive", 1),  # A > B
        create_preference_ranking_choice("Q1", "A vs C", 6, "positive", 1),  # A > C
        create_preference_ranking_choice("Q1", "B vs C", 6, "positive", 1),  # B > C
        # Question 2 (X1=6, negative): All pairs result in A > B > C
        create_preference_ranking_choice("Q2", "A vs B", 6, "negative", 1),  # A > B
        create_preference_ranking_choice("Q2", "A vs C", 6, "negative", 1),  # A > C
        create_preference_ranking_choice("Q2", "B vs C", 6, "negative", 1),  # B > C
        # Question 3 (X2=12, positive): All pairs result in A > B > C
        create_preference_ranking_choice("Q3", "A vs B", 12, "positive", 1),  # A > B
        create_preference_ranking_choice("Q3", "A vs C", 12, "positive", 1),  # A > C
        create_preference_ranking_choice("Q3", "B vs C", 12, "positive", 1),  # B > C
        # Question 4 (X2=12, negative): All pairs result in A > B > C
        create_preference_ranking_choice("Q4", "A vs B", 12, "negative", 1),  # A > B
        create_preference_ranking_choice("Q4", "A vs C", 12, "negative", 1),  # A > C
        create_preference_ranking_choice("Q4", "B vs C", 12, "negative", 1),  # B > C
    ]

    result = _deduce_rankings(choices)

    assert result is not None
    assert result["magnitudes"] == (6, 12)

    # All pairwise preferences should be consistent for positive questions
    assert result["pairwise"]["A vs B"][6]["+"] == "A > B"
    assert result["pairwise"]["A vs B"][12]["+"] == "A > B"

    assert result["pairwise"]["A vs C"][6]["+"] == "A > C"
    assert result["pairwise"]["A vs C"][12]["+"] == "A > C"

    assert result["pairwise"]["B vs C"][6]["+"] == "B > C"
    assert result["pairwise"]["B vs C"][12]["+"] == "B > C"

    # For negative questions, preferences should be swapped
    assert result["pairwise"]["A vs B"][6]["–"] == "B > A"  # Swapped from A > B
    assert result["pairwise"]["A vs B"][12]["–"] == "B > A"  # Swapped from A > B

    assert result["pairwise"]["A vs C"][6]["–"] == "C > A"  # Swapped from A > C
    assert result["pairwise"]["A vs C"][12]["–"] == "C > A"  # Swapped from A > C

    assert result["pairwise"]["B vs C"][6]["–"] == "C > B"  # Swapped from B > C
    assert result["pairwise"]["B vs C"][12]["–"] == "C > B"  # Swapped from B > C

    # All rankings should be A > B > C for positive questions
    assert result["rankings"][6]["+"] == "A > B > C"
    assert result["rankings"][12]["+"] == "A > B > C"

    # For negative questions, rankings should be swapped to C > B > A
    assert result["rankings"][6]["–"] == "C > B > A"  # Swapped from A > B > C
    assert result["rankings"][12]["–"] == "C > B > A"  # Swapped from A > B > C


def test_deduce_rankings_partially_consistent():
    """Test _deduce_rankings with partially consistent user (Example 2)."""
    # Create choices for partially consistent user
    # Based on ideal vector (40, 30, 30) with X1=6, X2=12
    # Q1 (X1, +): A > B > C, Q2 (X1, -): A > B > C, Q3 (X2, +): B > A > C, Q4 (X2, -): B > C > A
    choices = [
        # Question 1 (X1=6, positive): A > B > C
        create_preference_ranking_choice("Q1", "A vs B", 6, "positive", 1),  # A > B
        create_preference_ranking_choice("Q1", "A vs C", 6, "positive", 1),  # A > C
        create_preference_ranking_choice("Q1", "B vs C", 6, "positive", 1),  # B > C
        # Question 2 (X1=6, negative): A > B > C (will be swapped to C > B > A)
        create_preference_ranking_choice(
            "Q2", "A vs B", 6, "negative", 1
        ),  # A > B becomes B > A
        create_preference_ranking_choice(
            "Q2", "A vs C", 6, "negative", 1
        ),  # A > C becomes C > A
        create_preference_ranking_choice(
            "Q2", "B vs C", 6, "negative", 1
        ),  # B > C becomes C > B
        # Question 3 (X2=12, positive): B > A > C
        create_preference_ranking_choice("Q3", "A vs B", 12, "positive", 2),  # B > A
        create_preference_ranking_choice("Q3", "A vs C", 12, "positive", 1),  # A > C
        create_preference_ranking_choice("Q3", "B vs C", 12, "positive", 1),  # B > C
        # Question 4 (X2=12, negative): B > C > A (will be swapped to A > C > B)
        create_preference_ranking_choice(
            "Q4", "A vs B", 12, "negative", 2
        ),  # B > A becomes A > B
        create_preference_ranking_choice(
            "Q4", "A vs C", 12, "negative", 2
        ),  # C > A becomes A > C
        create_preference_ranking_choice(
            "Q4", "B vs C", 12, "negative", 1
        ),  # B > C becomes C > B
    ]

    result = _deduce_rankings(choices)

    assert result is not None
    assert result["magnitudes"] == (6, 12)

    # Check specific pairwise preferences
    assert result["pairwise"]["A vs B"][6]["+"] == "A > B"
    assert result["pairwise"]["A vs B"][6]["–"] == "B > A"  # Swapped from A > B
    assert result["pairwise"]["A vs B"][12]["+"] == "B > A"
    assert result["pairwise"]["A vs B"][12]["–"] == "A > B"  # Swapped from B > A

    assert result["pairwise"]["A vs C"][6]["+"] == "A > C"
    assert result["pairwise"]["A vs C"][6]["–"] == "C > A"  # Swapped from A > C
    assert result["pairwise"]["A vs C"][12]["+"] == "A > C"
    assert result["pairwise"]["A vs C"][12]["–"] == "A > C"  # Swapped from C > A

    assert result["pairwise"]["B vs C"][6]["+"] == "B > C"
    assert result["pairwise"]["B vs C"][6]["–"] == "C > B"  # Swapped from B > C
    assert result["pairwise"]["B vs C"][12]["+"] == "B > C"
    assert result["pairwise"]["B vs C"][12]["–"] == "C > B"  # Swapped from B > C

    # Check rankings
    assert result["rankings"][6]["+"] == "A > B > C"
    assert result["rankings"][6]["–"] == "C > B > A"  # Swapped from A > B > C
    assert result["rankings"][12]["+"] == "B > A > C"
    assert result["rankings"][12]["–"] == "A > C > B"  # Swapped from B > C > A


def test_deduce_rankings_negative_question_preference_swapping():
    """Test that negative questions correctly swap preference directions."""
    # Create choices for a user where negative questions should swap preferences
    # Based on ideal vector (40, 30, 30) with X1=6, X2=12
    choices = [
        # Question 1 (X1=6, positive): A > B > C (no swapping needed)
        create_preference_ranking_choice("Q1", "A vs B", 6, "positive", 1),  # A > B
        create_preference_ranking_choice("Q1", "A vs C", 6, "positive", 1),  # A > C
        create_preference_ranking_choice("Q1", "B vs C", 6, "positive", 1),  # B > C
        # Question 2 (X1=6, negative): Should swap preferences
        create_preference_ranking_choice(
            "Q2", "A vs B", 6, "negative", 1
        ),  # A > B becomes B > A
        create_preference_ranking_choice(
            "Q2", "A vs C", 6, "negative", 1
        ),  # A > C becomes C > A
        create_preference_ranking_choice(
            "Q2", "B vs C", 6, "negative", 1
        ),  # B > C becomes C > B
        # Question 3 (X2=12, positive): A > B > C (no swapping needed)
        create_preference_ranking_choice("Q3", "A vs B", 12, "positive", 1),  # A > B
        create_preference_ranking_choice("Q3", "A vs C", 12, "positive", 1),  # A > C
        create_preference_ranking_choice("Q3", "B vs C", 12, "positive", 1),  # B > C
        # Question 4 (X2=12, negative): Should swap preferences
        create_preference_ranking_choice(
            "Q4", "A vs B", 12, "negative", 1
        ),  # A > B becomes B > A
        create_preference_ranking_choice(
            "Q4", "A vs C", 12, "negative", 1
        ),  # A > C becomes C > A
        create_preference_ranking_choice(
            "Q4", "B vs C", 12, "negative", 1
        ),  # B > C becomes C > B
    ]

    result = _deduce_rankings(choices)

    assert result is not None
    assert result["magnitudes"] == (6, 12)

    # Check that positive questions (Q1, Q3) maintain original preferences
    assert result["pairwise"]["A vs B"][6]["+"] == "A > B"  # Q1: no swap
    assert result["pairwise"]["A vs B"][12]["+"] == "A > B"  # Q3: no swap

    # Check that negative questions (Q2, Q4) have swapped preferences
    assert result["pairwise"]["A vs B"][6]["–"] == "B > A"  # Q2: swapped from A > B
    assert result["pairwise"]["A vs B"][12]["–"] == "B > A"  # Q4: swapped from A > B

    assert result["pairwise"]["A vs C"][6]["–"] == "C > A"  # Q2: swapped from A > C
    assert result["pairwise"]["A vs C"][12]["–"] == "C > A"  # Q4: swapped from A > C

    assert result["pairwise"]["B vs C"][6]["–"] == "C > B"  # Q2: swapped from B > C
    assert result["pairwise"]["B vs C"][12]["–"] == "C > B"  # Q4: swapped from B > C

    # Check rankings reflect the swapped preferences
    assert result["rankings"][6]["+"] == "A > B > C"  # Q1: original order
    assert result["rankings"][6]["–"] == "C > B > A"  # Q2: swapped order
    assert result["rankings"][12]["+"] == "A > B > C"  # Q3: original order
    assert result["rankings"][12]["–"] == "C > B > A"  # Q4: swapped order


def test_deduce_rankings_mixed_choices_with_swapping():
    """Test preference swapping with mixed user choices (not all 1s)."""
    # Create a simple test with just 6 choices to test the core swapping logic
    choices = [
        # Question 1 (X1=6, positive): A > B
        create_preference_ranking_choice("Q1", "A vs B", 6, "positive", 1),  # A > B
        # Question 2 (X1=6, negative): A > B (should be swapped to B > A)
        create_preference_ranking_choice(
            "Q2", "A vs B", 6, "negative", 1
        ),  # A > B becomes B > A
        # Question 3 (X2=12, positive): B > A
        create_preference_ranking_choice("Q3", "A vs B", 12, "positive", 2),  # B > A
        # Question 4 (X2=12, negative): B > A (should be swapped to A > B)
        create_preference_ranking_choice(
            "Q4", "A vs B", 12, "negative", 2
        ),  # B > A becomes A > B
        # Question 1 (X1=6, positive): A > C
        create_preference_ranking_choice("Q1", "A vs C", 6, "positive", 1),  # A > C
        # Question 2 (X1=6, negative): A > C (should be swapped to C > A)
        create_preference_ranking_choice(
            "Q2", "A vs C", 6, "negative", 1
        ),  # A > C becomes C > A
        # Question 3 (X2=12, positive): C > A
        create_preference_ranking_choice("Q3", "A vs C", 12, "positive", 2),  # C > A
        # Question 4 (X2=12, negative): C > A (should be swapped to A > C)
        create_preference_ranking_choice(
            "Q4", "A vs C", 12, "negative", 2
        ),  # C > A becomes A > C
        # Question 1 (X1=6, positive): B > C
        create_preference_ranking_choice("Q1", "B vs C", 6, "positive", 1),  # B > C
        # Question 2 (X1=6, negative): B > C (should be swapped to C > B)
        create_preference_ranking_choice(
            "Q2", "B vs C", 6, "negative", 1
        ),  # B > C becomes C > B
        # Question 3 (X2=12, positive): C > B
        create_preference_ranking_choice("Q3", "B vs C", 12, "positive", 2),  # C > B
        # Question 4 (X2=12, negative): C > B (should be swapped to B > C)
        create_preference_ranking_choice(
            "Q4", "B vs C", 12, "negative", 2
        ),  # C > B becomes B > C
    ]

    result = _deduce_rankings(choices)

    assert result is not None
    assert result["magnitudes"] == (6, 12)

    # Check positive question preferences (no swapping)
    assert result["pairwise"]["A vs B"][6]["+"] == "A > B"
    assert result["pairwise"]["A vs C"][6]["+"] == "A > C"
    assert result["pairwise"]["B vs C"][6]["+"] == "B > C"

    # Check negative question preferences (with swapping)
    assert result["pairwise"]["A vs B"][6]["–"] == "B > A"  # A > B was swapped
    assert result["pairwise"]["A vs C"][6]["–"] == "C > A"  # A > C was swapped
    assert result["pairwise"]["B vs C"][6]["–"] == "C > B"  # B > C was swapped

    # Check X2 preferences
    assert result["pairwise"]["A vs B"][12]["+"] == "B > A"
    assert result["pairwise"]["A vs C"][12]["+"] == "C > A"
    assert result["pairwise"]["B vs C"][12]["+"] == "C > B"

    # Check X2 negative preferences (with swapping)
    assert result["pairwise"]["A vs B"][12]["–"] == "A > B"  # B > A was swapped
    assert result["pairwise"]["A vs C"][12]["–"] == "A > C"  # C > A was swapped
    assert result["pairwise"]["B vs C"][12]["–"] == "B > C"  # C > B was swapped


def test_generate_pairwise_consistency_table_perfect():
    """Test _generate_preference_ranking_pairwise_table with perfect consistency."""
    pairwise_data = {3: {"+": "A > B", "–": "A > B"}, 6: {"+": "A > B", "–": "A > B"}}
    magnitudes = (3, 6)

    table_html = _generate_preference_ranking_pairwise_table(
        "Table: Preference A vs B", pairwise_data, magnitudes
    )

    # Check for expected content
    assert "Table: Preference A vs B" in table_html
    assert "A > B" in table_html
    assert "✓" in table_html  # Perfect consistency icon
    assert (
        "Final Score: 1" in table_html or "ניקוד סופי: 1" in table_html
    )  # Perfect score


def test_generate_pairwise_consistency_table_partial():
    """Test _generate_preference_ranking_pairwise_table with partial consistency."""
    pairwise_data = {6: {"+": "A > B", "–": "A > B"}, 12: {"+": "B > A", "–": "B > A"}}
    magnitudes = (6, 12)

    table_html = _generate_preference_ranking_pairwise_table(
        "Table: Preference A vs B", pairwise_data, magnitudes
    )

    # Check for expected content
    assert "Table: Preference A vs B" in table_html
    assert "A > B" in table_html
    assert "B > A" in table_html
    assert "✓" in table_html  # Row consistency icon
    assert "✗" in table_html  # Column consistency is inconsistent
    assert (
        "Final Score: 0" in table_html or "ניקוד סופי: 0" in table_html
    )  # Imperfect score


def test_generate_final_ranking_summary_table_perfect():
    """Test _generate_final_ranking_summary_table with perfect consistency."""
    deduced_data = {
        "magnitudes": (3, 6),
        "pairwise": {
            "A vs B": {
                3: {"+": "A > B", "–": "A > B"},
                6: {"+": "A > B", "–": "A > B"},
            },
            "A vs C": {
                3: {"+": "A > C", "–": "A > C"},
                6: {"+": "A > C", "–": "A > C"},
            },
            "B vs C": {
                3: {"+": "B > C", "–": "B > C"},
                6: {"+": "B > C", "–": "B > C"},
            },
        },
        "rankings": {
            3: {"+": "A > B > C", "–": "A > B > C"},
            6: {"+": "A > B > C", "–": "A > B > C"},
        },
    }

    table_html = _generate_final_ranking_summary_table(deduced_data)

    # Check for expected content
    assert (
        "Final Ranking Summary Table" in table_html
        or "טבלת סיכום דירוג סופי" in table_html
    )
    assert "A > B > C" in table_html
    assert "3/3" in table_html  # Perfect consistency scores
    assert "X₁=3" in table_html or "X<sub>1</sub>=3" in table_html
    assert "X₂=6" in table_html or "X<sub>2</sub>=6" in table_html


def test_generate_preference_ranking_consistency_tables_perfect():
    """Test full generate_preference_ranking_consistency_tables with perfect consistency."""
    # Create choices for perfectly consistent user
    choices = [
        # Question 1 (X1=3, positive)
        create_preference_ranking_choice("Q1", "A vs B", 3, "positive", 1),
        create_preference_ranking_choice("Q1", "A vs C", 3, "positive", 1),
        create_preference_ranking_choice("Q1", "B vs C", 3, "positive", 1),
        # Question 2 (X1=3, negative)
        create_preference_ranking_choice("Q2", "A vs B", 3, "negative", 1),
        create_preference_ranking_choice("Q2", "A vs C", 3, "negative", 1),
        create_preference_ranking_choice("Q2", "B vs C", 3, "negative", 1),
        # Question 3 (X2=6, positive)
        create_preference_ranking_choice("Q3", "A vs B", 6, "positive", 1),
        create_preference_ranking_choice("Q3", "A vs C", 6, "positive", 1),
        create_preference_ranking_choice("Q3", "B vs C", 6, "positive", 1),
        # Question 4 (X2=6, negative)
        create_preference_ranking_choice("Q4", "A vs B", 6, "negative", 1),
        create_preference_ranking_choice("Q4", "A vs C", 6, "negative", 1),
        create_preference_ranking_choice("Q4", "B vs C", 6, "negative", 1),
    ]

    result_html = generate_preference_ranking_consistency_tables(choices)

    # Check that result contains all expected tables (translations supported)
    assert (
        "User Preference Consistency Analysis" in result_html
        or "ניתוח עקביות העדפות המשתמש" in result_html
    )
    assert (
        "Table: Preference A vs B" in result_html
        or "טבלה: העדפה א לעומת ב" in result_html
    )
    assert (
        "Table: Preference A vs C" in result_html
        or "טבלה: העדפה א לעומת ג" in result_html
    )
    assert (
        "Table: Preference B vs C" in result_html
        or "טבלה: העדפה ב לעומת ג" in result_html
    )
    assert (
        "Final Ranking Summary Table" in result_html
        or "טבלת סיכום דירוג סופי" in result_html
    )

    # Check for perfect consistency indicators
    assert "Final Score: 1" in result_html or "ניקוד סופי: 1" in result_html
    assert "3/3" in result_html


def test_generate_preference_ranking_consistency_tables_partial():
    """Test full generate_preference_ranking_consistency_tables with partial consistency."""
    # Create choices for partially consistent user (Example 2)
    choices = [
        # Question 1 (X1=6, positive): A > B > C
        create_preference_ranking_choice("Q1", "A vs B", 6, "positive", 1),
        create_preference_ranking_choice("Q1", "A vs C", 6, "positive", 1),
        create_preference_ranking_choice("Q1", "B vs C", 6, "positive", 1),
        # Question 2 (X1=6, negative): A > B > C
        create_preference_ranking_choice("Q2", "A vs B", 6, "negative", 1),
        create_preference_ranking_choice("Q2", "A vs C", 6, "negative", 1),
        create_preference_ranking_choice("Q2", "B vs C", 6, "negative", 1),
        # Question 3 (X2=12, positive): B > A > C
        create_preference_ranking_choice("Q3", "A vs B", 12, "positive", 2),
        create_preference_ranking_choice("Q3", "A vs C", 12, "positive", 1),
        create_preference_ranking_choice("Q3", "B vs C", 12, "positive", 1),
        # Question 4 (X2=12, negative): B > C > A
        create_preference_ranking_choice("Q4", "A vs B", 12, "negative", 2),
        create_preference_ranking_choice("Q4", "A vs C", 12, "negative", 2),
        create_preference_ranking_choice("Q4", "B vs C", 12, "negative", 1),
    ]

    result_html = generate_preference_ranking_consistency_tables(choices)

    # Check that result contains all expected tables (translations supported)
    assert (
        "User Preference Consistency Analysis" in result_html
        or "ניתוח עקביות העדפות המשתמש" in result_html
    )
    assert (
        "Table: Preference A vs B" in result_html
        or "טבלה: העדפה א לעומת ב" in result_html
    )
    assert (
        "Table: Preference A vs C" in result_html
        or "טבלה: העדפה א לעומת ג" in result_html
    )
    assert (
        "Table: Preference B vs C" in result_html
        or "טבלה: העדפה ב לעומת ג" in result_html
    )
    assert (
        "Final Ranking Summary Table" in result_html
        or "טבלת סיכום דירוג סופי" in result_html
    )

    # Check for mixed consistency indicators
    assert (
        "Final Score: 0" in result_html or "ניקוד סופי: 0" in result_html
    )  # Some tables have score 0
    assert (
        "Final Score: 1" in result_html or "ניקוד סופי: 1" in result_html
    )  # Some tables have score 1


def test_generate_preference_ranking_consistency_tables_invalid_input():
    """Test generate_preference_ranking_consistency_tables with invalid input."""
    # Test with empty choices
    result_html = generate_preference_ranking_consistency_tables([])
    assert "exactly 12 choices" in result_html

    # Test with wrong number of choices
    choices = [create_preference_ranking_choice("Q1", "A vs B", 3, "positive", 1)]
    result_html = generate_preference_ranking_consistency_tables(choices)
    assert "exactly 12 choices" in result_html


class TestTemporalPreferenceAnalysis:
    """Test temporal preference analysis functions."""

    @pytest.fixture
    def mock_translations(self):
        """Mock translations for temporal preference tests."""

        def mock_get_translation(key, section=None, **kwargs):
            translations = {
                "temporal_preference_summary": "Temporal Preference Summary",
                "ideal_this_year": "Ideal This Year",
                "ideal_next_year": "Ideal Next Year",
                "consistency_level": "Consistency Level",
                "choice": "Choice",
                "percentage": "Percentage",
                "consistency_breakdown_title": "Consistency Breakdown",
                "num_of_users": "# of Users",
                "avg_ideal_this_year": "Avg. 'Ideal This Year' Choice",
                "avg_ideal_next_year": "Avg. 'Ideal Next Year' Choice",
                "total": "Total",
                "avg_consistency": "Average Consistency",
                "no_answers": "No answers available",
            }
            return translations.get(key, key)

        with patch(
            "analysis.report_content_generators.get_translation",
            side_effect=mock_get_translation,
        ):
            yield

    def create_temporal_choice(self, user_choice):
        """Create a mock temporal preference choice."""
        return {
            "user_choice": user_choice,
            "user_id": "test_user",
        }

    def test_calculate_temporal_preference_metrics_empty_choices(self):
        """Test metric calculation with empty choices."""
        from analysis.report_content_generators import (
            _calculate_temporal_preference_metrics,
        )

        result = _calculate_temporal_preference_metrics([])

        assert result["ideal_this_year_percent"] == 0.0
        assert result["ideal_next_year_percent"] == 0.0
        assert result["consistency_percent"] == 0.0

    def test_calculate_temporal_preference_metrics_7_3_split(self):
        """Test metric calculation with 7/3 split (7 ideal this year, 3 ideal next year)."""
        from analysis.report_content_generators import (
            _calculate_temporal_preference_metrics,
        )

        choices = []
        # 7 choices for "Ideal This Year" (option 1)
        for _ in range(7):
            choices.append(self.create_temporal_choice(1))
        # 3 choices for "Ideal Next Year" (option 2)
        for _ in range(3):
            choices.append(self.create_temporal_choice(2))

        result = _calculate_temporal_preference_metrics(choices)

        assert result["ideal_this_year_percent"] == 70.0
        assert result["ideal_next_year_percent"] == 30.0
        assert result["consistency_percent"] == 70.0  # max(7, 3) * 10 = 70

    def test_calculate_temporal_preference_metrics_6_4_split(self):
        """Test metric calculation with 6/4 split."""
        from analysis.report_content_generators import (
            _calculate_temporal_preference_metrics,
        )

        choices = []
        # 6 choices for "Ideal This Year" (option 1)
        for _ in range(6):
            choices.append(self.create_temporal_choice(1))
        # 4 choices for "Ideal Next Year" (option 2)
        for _ in range(4):
            choices.append(self.create_temporal_choice(2))

        result = _calculate_temporal_preference_metrics(choices)

        assert result["ideal_this_year_percent"] == 60.0
        assert result["ideal_next_year_percent"] == 40.0
        assert result["consistency_percent"] == 60.0  # max(6, 4) * 10 = 60

    def test_calculate_temporal_preference_metrics_perfect_consistency(self):
        """Test metric calculation with perfect consistency (10/0 split)."""
        from analysis.report_content_generators import (
            _calculate_temporal_preference_metrics,
        )

        choices = []
        # 10 choices for "Ideal This Year" (option 1)
        for _ in range(10):
            choices.append(self.create_temporal_choice(1))

        result = _calculate_temporal_preference_metrics(choices)

        assert result["ideal_this_year_percent"] == 100.0
        assert result["ideal_next_year_percent"] == 0.0
        assert result["consistency_percent"] == 100.0  # max(10, 0) * 10 = 100

    def test_generate_temporal_preference_table_empty(self):
        """Test temporal preference table generation with empty choices."""
        from analysis.report_content_generators import (
            _generate_temporal_preference_table,
        )

        result = _generate_temporal_preference_table([])
        assert result == ""

    def test_generate_temporal_preference_table_with_data(self, mock_translations):
        """Test temporal preference table generation with data."""
        from analysis.report_content_generators import (
            _generate_temporal_preference_table,
        )

        choices = []
        # Create 7/3 split
        for _ in range(7):
            choices.append(self.create_temporal_choice(1))
        for _ in range(3):
            choices.append(self.create_temporal_choice(2))

        result = _generate_temporal_preference_table(choices)

        assert "Temporal Preference Summary" in result
        assert "70.0%" in result  # Ideal This Year percentage
        assert "30.0%" in result  # Ideal Next Year percentage
        assert "highlight-row" in result  # Should highlight dominant choice

    def test_generate_consistency_breakdown_table_empty(self, mock_translations):
        """Test consistency breakdown table with empty data."""
        from analysis.report_content_generators import (
            generate_consistency_breakdown_table,
        )

        result = generate_consistency_breakdown_table([])
        assert "No answers available" in result

    def test_generate_consistency_breakdown_table_single_user(self, mock_translations):
        """Test consistency breakdown table with single user."""
        from analysis.report_content_generators import (
            generate_consistency_breakdown_table,
        )

        user_choices = []
        # User 1: 8/2 split (80% consistency)
        for _ in range(8):
            user_choices.append({"user_id": "user1", "user_choice": 1})
        for _ in range(2):
            user_choices.append({"user_id": "user1", "user_choice": 2})

        result = generate_consistency_breakdown_table(user_choices)

        assert "Consistency Breakdown" in result
        assert "80%" in result  # Consistency level
        assert "1" in result  # Number of users
        assert "80.0%" in result  # Average ideal this year

    def test_generate_consistency_breakdown_table_multiple_users(
        self, mock_translations
    ):
        """Test consistency breakdown table with multiple users at different consistency levels."""
        from analysis.report_content_generators import (
            generate_consistency_breakdown_table,
        )

        user_choices = []

        # User 1: 10/0 split (100% consistency, 100% ideal this year)
        for _ in range(10):
            user_choices.append({"user_id": "user1", "user_choice": 1})

        # User 2: 7/3 split (70% consistency, 70% ideal this year)
        for _ in range(7):
            user_choices.append({"user_id": "user2", "user_choice": 1})
        for _ in range(3):
            user_choices.append({"user_id": "user2", "user_choice": 2})

        # User 3: 6/4 split (60% consistency, 60% ideal this year)
        for _ in range(6):
            user_choices.append({"user_id": "user3", "user_choice": 1})
        for _ in range(4):
            user_choices.append({"user_id": "user3", "user_choice": 2})

        result = generate_consistency_breakdown_table(user_choices)

        # Should have users in 60%, 70%, and 100% consistency groups
        assert "60%" in result
        assert "70%" in result
        assert "100%" in result
        assert "Total" in result

        # Check that totals are calculated correctly
        assert "3" in result  # Total users

    def test_generate_consistency_breakdown_table_consistency_calculation(
        self, mock_translations
    ):
        """Test that consistency levels are calculated correctly."""
        from analysis.report_content_generators import (
            generate_consistency_breakdown_table,
        )

        user_choices = []

        # User with 5/5 split should be 50% consistent (max(5,5) * 10 = 50)
        for _ in range(5):
            user_choices.append({"user_id": "user_even", "user_choice": 1})
        for _ in range(5):
            user_choices.append({"user_id": "user_even", "user_choice": 2})

        result = generate_consistency_breakdown_table(user_choices)

        # Should place user in 50% consistency group
        assert "50%" in result
        assert "1" in result  # One user in that group
