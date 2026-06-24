import json
from unittest.mock import patch

# Logic Layer (Stats Calculators)
from analysis.logic.stats_calculators import (
    calculate_user_consistency,
    get_summary_value,
)

# Modern Presentation Layer (For Web Report Tests)

# 4. Import from Service Layer
from analysis.report_service import generate_detailed_user_choices


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
    assert qualified_users == 1
    assert consistency_pct == 100.0




# --- Service Layer Tests ---


@patch("analysis.report_service.get_user_survey_performance_data")
@patch("analysis.report_service.get_subjects")
@patch("analysis.report_service.get_translation")
def test_generate_detailed_user_choices_empty(
    mock_get_translation, mock_get_subjects, mock_get_perf_data, mock_translations
):
    """Test generate_detailed_user_choices with empty input."""
    mock_get_translation.side_effect = (
        lambda key, section, **kwargs: mock_translations.get(key, f"[{key}]")
    )

    option_labels = ("Sum Optimized Vector", "Ratio Optimized Vector")
    result = generate_detailed_user_choices([], option_labels)

    assert isinstance(result, dict)
    # Updated to match actual output
    assert "No detailed user choice data available" in result["combined_html"]


@patch("analysis.report_service.get_user_survey_performance_data")
@patch("analysis.report_service.get_subjects")
@patch("analysis.presentation.html_renderers.get_translation")
def test_generate_detailed_user_choices_single_user(
    mock_get_translation, mock_get_subjects, mock_get_perf_data, mock_translations
):
    """Test generate_detailed_user_choices with a single user's data."""
    mock_get_translation.side_effect = (
        lambda key, section, **kwargs: mock_translations.get(key, f"[{key}]")
    )
    mock_get_perf_data.return_value = []
    mock_get_subjects.return_value = []

    option_labels = ("Sum Optimized Vector", "Ratio Optimized Vector")
    test_data = [
        {
            "user_id": "test123",
            "survey_id": 1,
            "optimal_allocation": json.dumps([50, 30, 20]),
            "pair_number": 1,
            "option_1": json.dumps([50, 40, 10]),
            "option_2": json.dumps([30, 50, 20]),
            "user_choice": 2,
            "response_created_at": "2023-01-01 12:00:00",
        }
    ]

    result = generate_detailed_user_choices(test_data, option_labels)

    assert isinstance(result, dict)
    combined_html = result["combined_html"]
    assert "test123" in combined_html
    assert "1" in combined_html
    assert "[50, 30, 20]" in combined_html
