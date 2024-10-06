import json
import os
import sys
from unittest.mock import patch

import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))


from analysis.analysis_utils import (
    calculate_optimization_stats,
    ensure_directory_exists,
    is_sum_optimized,
    process_survey_responses,
    save_dataframe_to_csv,
)


def test_is_sum_optimized():
    """Test is_sum_optimized function for correct optimization detection."""
    assert is_sum_optimized((50, 30, 20), (40, 35, 25), (45, 30, 25), 1)
    assert not is_sum_optimized((50, 30, 20), (40, 35, 25), (45, 30, 25), 2)
    assert not is_sum_optimized((50, 30, 20), (45, 30, 25), (40, 35, 25), 1)


def test_is_sum_optimized_invalid_input():
    """Test is_sum_optimized function with invalid input."""
    with pytest.raises(ValueError):
        is_sum_optimized((50, 30, 20), (40, 35, 25), (45, 30, 25), 3)


def test_process_survey_responses():
    """Test process_survey_responses function for correct data processing."""
    raw_results = [
        {
            "survey_response_id": 1,
            "user_id": 101,
            "survey_id": 1,
            "optimal_allocation": json.dumps([50, 30, 20]),
            "completed": True,
            "response_created_at": "2023-01-01 10:00:00",
            "pair_number": 1,
            "option_1": json.dumps([40, 35, 25]),
            "option_2": json.dumps([45, 30, 25]),
            "user_choice": 1,
        },
        {
            "survey_response_id": 1,
            "user_id": 101,
            "survey_id": 1,
            "optimal_allocation": json.dumps([50, 30, 20]),
            "completed": True,
            "response_created_at": "2023-01-01 10:00:00",
            "pair_number": 2,
            "option_1": json.dumps([55, 25, 20]),
            "option_2": json.dumps([45, 35, 20]),
            "user_choice": 2,
        },
    ]

    processed_results = process_survey_responses(raw_results)

    assert len(processed_results) == 1
    assert processed_results[0]["survey_response_id"] == 1
    assert processed_results[0]["user_id"] == 101
    assert processed_results[0]["optimal_allocation"] == [50, 30, 20]
    assert len(processed_results[0]["comparisons"]) == 2
    assert processed_results[0]["comparisons"][0]["pair_number"] == 1
    assert processed_results[0]["comparisons"][1]["pair_number"] == 2


def test_save_dataframe_to_csv():
    """Test save_dataframe_to_csv function for successful CSV saving."""
    df = pd.DataFrame({"name": ["Alice", "Bob"], "age": [30, 25]})
    filename = "test_output.csv"

    with patch("analysis.analysis_utils.ensure_directory_exists") as mock_ensure_dir:
        with patch("pandas.DataFrame.to_csv") as mock_to_csv:
            save_dataframe_to_csv(df, filename)

    mock_ensure_dir.assert_called_once_with(filename)
    mock_to_csv.assert_called_once_with(filename, index=False)


def test_save_dataframe_to_csv_empty_dataframe():
    """Test save_dataframe_to_csv function with an empty DataFrame."""
    df = pd.DataFrame()
    filename = "empty_output.csv"

    with pytest.raises(ValueError, match="Input DataFrame is empty"):
        save_dataframe_to_csv(df, filename)


@patch("os.path.exists")
@patch("os.makedirs")
def test_ensure_directory_exists(mock_makedirs, mock_exists):
    """Test ensure_directory_exists function for directory creation."""
    mock_exists.return_value = False
    ensure_directory_exists("/path/to/file.csv")
    mock_makedirs.assert_called_once_with("/path/to")

    mock_exists.return_value = True
    mock_makedirs.reset_mock()
    ensure_directory_exists("/path/to/another_file.csv")
    mock_makedirs.assert_not_called()


def test_calculate_optimization_stats():
    """
    Test calculate_optimization_stats for sum, ratio, and equal optimization scenarios.
    """
    # Test case 1: More sum optimized choices
    row1 = pd.Series(
        {
            "optimal_allocation": [50, 30, 20],
            "comparisons": [
                {"option_1": [40, 35, 25], "option_2": [45, 30, 25], "user_choice": 1},
                {"option_1": [50, 20, 20], "option_2": [45, 35, 20], "user_choice": 2},
                {"option_1": [50, 30, 20], "option_2": [45, 25, 20], "user_choice": 1},
            ],
        }
    )
    result1 = calculate_optimization_stats(row1)
    assert result1["num_of_answers"] == 3
    assert result1["sum_optimized"] == 2
    assert result1["ratio_optimized"] == 1
    assert result1["result"] == "sum"

    # Test case 2: More ratio optimized choices
    row2 = pd.Series(
        {
            "optimal_allocation": [50, 30, 20],
            "comparisons": [
                {"option_1": [40, 35, 25], "option_2": [45, 30, 25], "user_choice": 2},
                {"option_1": [50, 20, 20], "option_2": [45, 35, 20], "user_choice": 1},
                {"option_1": [50, 30, 20], "option_2": [45, 25, 20], "user_choice": 2},
            ],
        }
    )
    result2 = calculate_optimization_stats(row2)
    assert result2["num_of_answers"] == 3
    assert result2["sum_optimized"] == 1
    assert result2["ratio_optimized"] == 2
    assert result2["result"] == "ratio"

    # Test case 3: Equal sum and ratio optimized choices
    row3 = pd.Series(
        {
            "optimal_allocation": [50, 30, 20],
            "comparisons": [
                {"option_1": [40, 35, 25], "option_2": [45, 30, 25], "user_choice": 1},
                {"option_1": [55, 25, 20], "option_2": [90, 10, 0], "user_choice": 1},
            ],
        }
    )
    result3 = calculate_optimization_stats(row3)
    assert result3["num_of_answers"] == 2
    assert result3["sum_optimized"] == 1
    assert result3["ratio_optimized"] == 1
    assert result3["result"] == "equal"
