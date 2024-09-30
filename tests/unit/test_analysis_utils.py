import json
import os
import sys
from unittest.mock import patch

import pandas as pd
import pytest

# Add the parent directory to the system path to allow importing from the backend module.
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from analysis.analysis_utils import (
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
