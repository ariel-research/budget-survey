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
    process_data_to_dataframe,
    process_survey_responses,
)


def test_is_sum_optimized():
    # User optimizes for sum difference
    assert is_sum_optimized((50, 30, 20), (40, 35, 25), (45, 30, 25), 1)

    # User does not optimize for sum difference
    assert not is_sum_optimized((50, 30, 20), (40, 35, 25), (45, 30, 25), 2)

    # User does not optimize for sum difference
    assert not is_sum_optimized((50, 30, 20), (45, 30, 25), (40, 35, 25), 1)


def test_is_sum_optimized_invalid_input():
    # Invalid user choice
    with pytest.raises(ValueError):
        is_sum_optimized((50, 30, 20), (40, 35, 25), (45, 30, 25), 3)


def test_process_survey_responses():
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


def test_process_data_to_dataframe():
    data = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]

    df = process_data_to_dataframe(data)

    assert isinstance(df, pd.DataFrame)
    assert df.shape == (2, 2)
    assert list(df.columns) == ["name", "age"]
    assert df.iloc[0]["name"] == "Alice"
    assert df.iloc[1]["age"] == 25


def test_process_data_to_dataframe_empty_input():
    with pytest.raises(ValueError, match="Input data is empty"):
        process_data_to_dataframe([])


@patch("pandas.DataFrame.to_csv")
def test_process_data_to_dataframe_with_csv(mock_to_csv):
    data = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]

    df = process_data_to_dataframe(data, csv_filename="test.csv")

    assert isinstance(df, pd.DataFrame)
    mock_to_csv.assert_called_once_with("test.csv", index=False)


@patch("os.path.exists")
@patch("os.makedirs")
def test_ensure_directory_exists(mock_makedirs, mock_exists):
    # Test when directory doesn't exist
    mock_exists.return_value = False
    ensure_directory_exists("/path/to/file.csv")
    mock_makedirs.assert_called_once_with("/path/to")

    # Test when directory already exists
    mock_exists.return_value = True
    mock_makedirs.reset_mock()
    ensure_directory_exists("/path/to/another_file.csv")
    mock_makedirs.assert_not_called()
