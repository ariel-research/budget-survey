import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from analysis.report_content_generators import (
    calculate_user_consistency,
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
    assert get_summary_value(sample_summary_stats, "unique_users") == 8
    assert get_summary_value(sample_summary_stats, "total_answers") == 80
    assert get_summary_value(sample_summary_stats, "sum_optimized") == 45


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


def test_generate_executive_summary(sample_summary_stats, sample_optimization_stats):
    """Test generation of executive summary."""
    summary = generate_executive_summary(
        sample_summary_stats, sample_optimization_stats
    )

    assert isinstance(summary, str)
    assert "2 surveys" in summary
    assert "8 unique users" in summary
    assert "80 answers" in summary
    assert "56.25% sum vs 43.75% ratio" in summary


def test_generate_overall_stats(sample_summary_stats):
    """Test generation of overall statistics."""
    stats = generate_overall_stats(sample_summary_stats)

    assert isinstance(stats, str)
    assert "Total number of surveys: 2" in stats
    assert "Total number of participants: 8" in stats
    assert "Total answers collected: 80" in stats


def test_generate_survey_analysis(sample_summary_stats):
    """Test generation of survey-specific analysis."""
    analysis = generate_survey_analysis(sample_summary_stats)

    assert isinstance(analysis, str)
    assert "Survey 1" in analysis
    assert "Survey 2" in analysis
    assert "5 participants" in analysis
    assert "3 participants" in analysis


def test_generate_individual_analysis(sample_optimization_stats):
    """Test generation of individual user analysis."""
    analysis = generate_individual_analysis(sample_optimization_stats)

    assert isinstance(analysis, str)
    assert "User 101" in analysis
    assert "User 102" in analysis
    assert "User 103" in analysis
    assert "70.0% sum optimized" in analysis  # User 101, Survey 1


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
