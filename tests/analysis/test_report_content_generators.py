import json

from analysis.report_content_generators import (
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
    assert "70.0% sum optimized" in analysis  # User 101


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


def test_generate_detailed_user_choices_empty():
    """Test generate_detailed_user_choices with empty input."""
    option_labels = ("Option 1", "Option 2")
    result = generate_detailed_user_choices([], option_labels)
    assert "No detailed user choice data available" in result


def test_generate_detailed_user_choices_single_user():
    """Test generate_detailed_user_choices with a single user's data."""
    option_labels = ("Sum Optimized", "Ratio Optimized")
    test_data = [
        {
            "user_id": "test123",
            "survey_id": 1,
            "optimal_allocation": json.dumps([50, 30, 20]),
            "pair_number": 1,
            "option_1": json.dumps([50, 40, 10]),  # better sum
            "option_2": json.dumps([30, 50, 20]),  # better ratio
            "user_choice": 2,  # Choosing option 2 -- ratio optimization
        },
    ]

    result = generate_detailed_user_choices(test_data, option_labels)

    # Check basic structure with corrected assertions
    assert "User ID: test123" in result
    assert "Survey ID: 1" in result
    assert "Ideal budget: [50, 30, 20]" in result
    assert "<td>Ratio Optimized</td>" in result


def test_generate_detailed_user_choices_multiple_optimizations():
    """Test generate_detailed_user_choices with both sum and ratio optimizations."""
    optimal = [50, 30, 20]  # Base optimal allocation
    option_labels = ("Sum Optimized", "Ratio Optimized")
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

    result = generate_detailed_user_choices(test_data, option_labels)

    assert "<td>Sum Optimized</td>" in result
    assert "<td>Ratio Optimized</td>" in result
    assert "Pair #1" in result
    assert "Pair #2" in result


def test_generate_detailed_user_choices_multiple_surveys():
    """Test generate_detailed_user_choices with multiple surveys for the same user."""
    option_labels = ("Sum Optimized", "Ratio Optimized")
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

    result = generate_detailed_user_choices(test_data, option_labels)

    # Check multiple survey sections
    assert "Survey ID: 1" in result
    assert "Survey ID: 2" in result
    assert "Ideal budget: [25, 25, 50]" in result
    assert "Ideal budget: [40, 40, 20]" in result


def test_generate_detailed_user_choices_css_classes():
    """Test that generate_detailed_user_choices includes correct CSS classes."""
    option_labels = ("Sum Optimized", "Ratio Optimized")
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

    result = generate_detailed_user_choices(test_data, option_labels)

    # Check CSS classes
    assert 'class="user-choices"' in result
    assert 'class="survey-choices"' in result
    assert 'class="pairs-list"' in result
    assert 'class="ideal-budget"' in result
    assert 'class="selection-column"' in result
    assert 'class="option-column"' in result
