import os
import sys
from unittest.mock import patch

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from analysis.survey_analysis import (
    generate_survey_optimization_stats,
    get_all_completed_survey_responses,
    summarize_stats_by_survey,
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
    """Test that summarize_stats_by_survey returns a DataFrame with expected columns, row count, and summary row."""
    input_df = pd.DataFrame(
        {
            "survey_id": [1, 1, 2],
            "user_id": [101, 102, 103],
            "num_of_answers": [10, 10, 10],
            "sum_optimized": [6, 5, 7],
            "ratio_optimized": [4, 5, 3],
            "result": ["sum", "ratio", "sum"],
        }
    )

    result = summarize_stats_by_survey(input_df)

    assert isinstance(result, pd.DataFrame)
    assert "unique_users" in result.columns
    assert "total_answers" in result.columns
    assert "sum_optimized_percentage" in result.columns
    assert "ratio_optimized_percentage" in result.columns
    assert result.shape[0] == 3  # Two survey rows + one summary row

    # Check the summary row
    summary_row = result.iloc[-1]
    assert summary_row["survey_id"] == "Total"
    assert summary_row["unique_users"] == 3
    assert summary_row["total_answers"] == 30
    assert summary_row["sum_optimized"] == 18
    assert summary_row["ratio_optimized"] == 12
    assert np.isclose(summary_row["sum_optimized_percentage"], 60.0)
    assert np.isclose(summary_row["ratio_optimized_percentage"], 40.0)
    assert summary_row["sum_count"] == 2
    assert summary_row["ratio_count"] == 1
    assert summary_row["equal_count"] == 0
    assert np.isclose(summary_row["sum_percentage"], 66.66666, atol=1e-5)
    assert np.isclose(summary_row["ratio_percentage"], 33.33333, atol=1e-5)
    assert summary_row["equal_percentage"] == 0.0


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
