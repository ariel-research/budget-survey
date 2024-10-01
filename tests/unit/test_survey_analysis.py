import os
import sys
from unittest.mock import patch

import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from analysis.survey_analysis import (
    generate_survey_optimization_stats,
    get_all_completed_survey_responses,
    summarize_stats_by_survey,
)


@pytest.fixture
def sample_survey_responses():
    """Provide a sample DataFrame of survey responses for testing."""
    return pd.DataFrame(
        {
            "survey_id": [1, 1, 2],
            "user_id": [101, 102, 103],
            "optimal_allocation": [[50, 30, 20], [40, 40, 20], [60, 20, 20]],
            "comparisons": [
                [
                    {
                        "option_1": [40, 35, 25],
                        "option_2": [45, 30, 25],
                        "user_choice": 1,
                    }
                ],
                [
                    {
                        "option_1": [35, 40, 25],
                        "option_2": [45, 35, 20],
                        "user_choice": 2,
                    }
                ],
                [
                    {
                        "option_1": [55, 25, 20],
                        "option_2": [65, 15, 20],
                        "user_choice": 1,
                    }
                ],
            ],
        }
    )


@patch("analysis.survey_analysis.retrieve_completed_survey_responses")
@patch("analysis.survey_analysis.process_survey_responses")
def test_get_all_completed_survey_responses(mock_process, mock_retrieve):
    """Test that get_all_completed_survey_responses returns a DataFrame and calls expected functions."""
    mock_retrieve.return_value = [{"some": "data"}]
    mock_process.return_value = [{"processed": "data"}]

    result = get_all_completed_survey_responses()

    assert isinstance(result, pd.DataFrame)
    mock_retrieve.assert_called_once()
    mock_process.assert_called_once_with([{"some": "data"}])


def test_generate_survey_optimization_stats(sample_survey_responses):
    """Test that generate_survey_optimization_stats returns a DataFrame with expected columns."""
    result = generate_survey_optimization_stats(sample_survey_responses)

    assert isinstance(result, pd.DataFrame)
    assert "num_of_answers" in result.columns
    assert "sum_optimized" in result.columns
    assert "ratio_optimized" in result.columns
    assert "result" in result.columns


def test_summarize_stats_by_survey():
    """Test that summarize_stats_by_survey returns a DataFrame with expected columns and row count."""
    input_df = pd.DataFrame(
        {
            "survey_id": [1, 1, 2],
            "user_id": [101, 102, 103],
            "num_of_answers": [10, 10, 10],
            "sum_optimized": [6, 5, 7],
            "ratio_optimized": [4, 5, 3],
            "result": ["sum", "equal", "sum"],
        }
    )

    result = summarize_stats_by_survey(input_df)

    assert isinstance(result, pd.DataFrame)
    assert "unique_users" in result.columns
    assert "total_answers" in result.columns
    assert "sum_optimized_percentage" in result.columns
    assert "ratio_optimized_percentage" in result.columns
    assert result.shape[0] == 2  # Two unique survey_ids


@patch("analysis.survey_analysis.get_all_completed_survey_responses")
@patch("analysis.survey_analysis.generate_survey_optimization_stats")
@patch("analysis.survey_analysis.summarize_stats_by_survey")
@patch("analysis.survey_analysis.save_dataframe_to_csv")
def test_main(mock_save, mock_summarize, mock_generate, mock_get):
    """Test that the main function calls all expected functions and saves three DataFrames."""
    mock_get.return_value = pd.DataFrame({"dummy": [1, 2, 3]})
    mock_generate.return_value = pd.DataFrame({"stats": [4, 5, 6]})
    mock_summarize.return_value = pd.DataFrame({"summary": [7, 8, 9]})

    from analysis.survey_analysis import main

    main()

    mock_get.assert_called_once()
    mock_generate.assert_called_once()
    mock_summarize.assert_called_once()
    assert (
        mock_save.call_count == 3
    )  # Called three times for three different DataFrames
