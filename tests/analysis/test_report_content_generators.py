import json
from unittest.mock import patch

from analysis.report_content_generators import (
    _calculate_cyclic_shift_group_consistency,
    _generate_cyclic_shift_consistency_table,
    calculate_user_consistency,
    generate_detailed_user_choices,
    generate_executive_summary,
    generate_individual_analysis,
    generate_key_findings,
    generate_methodology_description,
    generate_overall_stats,
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
