import base64

import matplotlib.pyplot as plt
import pandas as pd
import pytest

from analysis.utils.visualization_utils import (
    save_plot_to_base64,
    validate_dataframe,
    visualize_overall_majority_choice_distribution,
    visualize_per_survey_answer_percentages,
    visualize_total_answer_percentage_distribution,
    visualize_user_survey_majority_choices,
)


def assert_valid_base64_image(result: str) -> None:
    """
    Assert that the result is a valid base64 encoded string.

    Args:
        result: String to validate

    Raises:
        AssertionError: If result is not a string or not a valid base64 encoding
    """
    assert isinstance(result, str), "Result must be a string"
    try:
        base64.b64decode(result)
    except Exception:
        pytest.fail("Result is not a valid base64 string")


def test_save_plot_to_base64():
    """Test conversion of matplotlib figure to base64 string."""
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [1, 2, 3])

    result = save_plot_to_base64(fig)
    assert_valid_base64_image(result)


def test_visualize_per_survey_answer_percentages(sample_summary_stats):
    """Test generation of survey answer percentages visualization."""
    # Filter out the "Total" row as it's not used in visualization
    filtered_stats = sample_summary_stats[sample_summary_stats["survey_id"] != "Total"]
    result = visualize_per_survey_answer_percentages(filtered_stats)
    assert_valid_base64_image(result)


def test_visualize_user_survey_majority_choices(sample_optimization_stats):
    """Test generation of user survey majority choices visualization."""
    result = visualize_user_survey_majority_choices(sample_optimization_stats)
    assert_valid_base64_image(result)


def test_visualize_overall_majority_choice_distribution(sample_summary_stats):
    """Test generation of overall majority choice distribution visualization."""
    result = visualize_overall_majority_choice_distribution(sample_summary_stats)
    assert_valid_base64_image(result)


def test_visualize_total_answer_percentage_distribution(sample_summary_stats):
    """Test generation of total answer percentage distribution visualization."""
    result = visualize_total_answer_percentage_distribution(sample_summary_stats)
    assert_valid_base64_image(result)


def test_per_survey_visualization_content():
    """Test the content creation of per-survey visualization."""
    stats = pd.DataFrame(
        {
            "survey_id": ["1", "2"],
            "sum_optimized_percentage": [60.0, 50.0],
            "ratio_optimized_percentage": [40.0, 50.0],
        }
    )

    result = visualize_per_survey_answer_percentages(stats)
    assert_valid_base64_image(result)


def test_majority_choices_visualization_content():
    """Test the content creation of majority choices visualization."""
    stats = pd.DataFrame(
        {
            "survey_id": [1, 1, 2],
            "user_id": [101, 102, 101],
            "result": ["sum", "ratio", "sum"],
        }
    )

    result = visualize_user_survey_majority_choices(stats)
    assert_valid_base64_image(result)


def test_visualization_error_handling():
    """Test error handling in visualization functions with invalid data."""
    # Test with empty DataFrame
    empty_df = pd.DataFrame()
    with pytest.raises(ValueError, match="Input DataFrame is empty"):
        visualize_per_survey_answer_percentages(empty_df)

    # Test with DataFrame missing required columns
    invalid_df = pd.DataFrame({"wrong_column": [1, 2, 3]})
    with pytest.raises(ValueError, match="missing required columns"):
        visualize_per_survey_answer_percentages(invalid_df)

    with pytest.raises(ValueError, match="missing required columns"):
        visualize_user_survey_majority_choices(invalid_df)

    with pytest.raises(ValueError, match="missing required columns"):
        visualize_overall_majority_choice_distribution(invalid_df)

    with pytest.raises(ValueError, match="missing required columns"):
        visualize_total_answer_percentage_distribution(invalid_df)


def test_validate_dataframe():
    """Test the DataFrame validation function."""
    # Test empty DataFrame
    empty_df = pd.DataFrame()
    with pytest.raises(ValueError, match="Input DataFrame is empty"):
        validate_dataframe(empty_df, ["col1"])

    # Test missing columns
    df = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})
    with pytest.raises(ValueError, match="missing required columns"):
        validate_dataframe(df, ["col1", "col3"])

    # Test valid DataFrame
    validate_dataframe(df, ["col1", "col2"])  # Should not raise any exception
