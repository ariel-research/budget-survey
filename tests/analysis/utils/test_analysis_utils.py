import json

import pandas as pd
import pytest

from analysis.utils.analysis_utils import (
    calculate_optimization_stats,
    is_sum_optimized,
    process_survey_responses,
)


def test_is_sum_optimized():
    """Test is_sum_optimized function for correct optimization detection."""
    # Case 1: Option 1 has smaller sum of differences
    assert is_sum_optimized(
        (50, 30, 20),  # optimal
        (45, 30, 25),  # option 1 - sum_diff = 10
        (40, 35, 25),  # option 2 - sum_diff = 20
        1,  # choosing option 1 = sum optimized
    )

    # Case 2: Option 2 has smaller sum of differences
    assert is_sum_optimized(
        (50, 30, 20),  # optimal
        (35, 40, 25),  # option 1 - sum_diff = 30
        (45, 35, 20),  # option 2 - sum_diff = 10
        2,  # choosing option 2 = sum optimized
    )

    # Case 3: Option 1 has larger sum of differences (not sum optimized)
    assert not is_sum_optimized(
        (50, 30, 20),  # optimal
        (20, 50, 30),  # option 1 - sum_diff = 60
        (45, 35, 20),  # option 2 - sum_diff = 10
        1,  # choosing option 1 = ratio optimized
    )


def test_is_sum_optimized_invalid_input():
    """Test is_sum_optimized function with invalid input."""
    with pytest.raises(ValueError):
        is_sum_optimized((50, 30, 20), (40, 35, 25), (45, 30, 25), 3)


def test_process_survey_responses():
    """Test process_survey_responses function for proper data processing and structure."""
    raw_results = [
        # Survey Response 1 - First comparison pair
        {
            "survey_response_id": 1,
            "user_id": 101,
            "survey_id": 1,
            "optimal_allocation": json.dumps([50, 30, 20]),
            "completed": True,
            "response_created_at": "2023-01-01 10:00:00",
            "user_comment": "first survey comment",
            "pair_number": 1,
            "option_1": json.dumps([40, 35, 25]),
            "option_2": json.dumps([45, 30, 25]),
            "user_choice": 1,
        },
        # Survey Response 1 - Second comparison pair
        {
            "survey_response_id": 1,
            "user_id": 101,
            "survey_id": 1,
            "optimal_allocation": json.dumps([50, 30, 20]),
            "completed": True,
            "response_created_at": "2023-01-01 10:00:00",
            "user_comment": "first survey comment",
            "pair_number": 2,
            "option_1": json.dumps([55, 25, 20]),
            "option_2": json.dumps([45, 35, 20]),
            "user_choice": 2,
        },
        {
            "survey_response_id": 2,
            "user_id": 102,
            "survey_id": 1,
            "optimal_allocation": json.dumps([40, 40, 20]),
            "completed": True,
            "response_created_at": "2023-01-01 11:00:00",
            "user_comment": "second survey comment",
            "pair_number": 1,
            "option_1": json.dumps([35, 45, 20]),
            "option_2": json.dumps([45, 35, 20]),
            "user_choice": 2,
        },
    ]

    processed_results = process_survey_responses(raw_results)

    # Test basic structure
    assert isinstance(processed_results, list)
    assert len(processed_results) == 2  # Should have two distinct surveys

    # Test first survey response
    first_result = processed_results[0]
    assert first_result["survey_response_id"] == 1
    assert first_result["user_id"] == 101
    assert first_result["survey_id"] == 1
    assert first_result["optimal_allocation"] == [50, 30, 20]
    assert first_result["completed"] is True
    assert first_result["user_comment"] == "first survey comment"
    assert len(first_result["comparisons"]) == 2

    # Test second survey response
    second_result = processed_results[1]
    assert second_result["survey_response_id"] == 2
    assert second_result["user_id"] == 102
    assert second_result["optimal_allocation"] == [40, 40, 20]
    assert second_result["user_comment"] == "second survey comment"
    assert len(second_result["comparisons"]) == 1


def test_calculate_optimization_stats():
    """
    Test calculate_optimization_stats for sum, ratio, and equal optimization scenarios.
    """
    # Test case 1: More sum optimized choices
    row1 = pd.Series(
        {
            "optimal_allocation": [50, 30, 20],
            "comparisons": [
                {
                    "option_1": [45, 30, 25],  # sum_diff = 10
                    "option_2": [20, 50, 30],  # sum_diff = 60
                    "user_choice": 1,  # chose smaller difference
                },
                {
                    "option_1": [55, 25, 20],  # sum_diff = 10
                    "option_2": [35, 45, 20],  # sum_diff = 30
                    "user_choice": 1,  # chose smaller difference
                },
            ],
        }
    )
    result1 = calculate_optimization_stats(row1)
    assert result1["num_of_answers"] == 2
    assert result1["sum_optimized"] == 2
    assert result1["ratio_optimized"] == 0
    assert result1["result"] == "sum"

    # Test case 2: More ratio optimized choices
    row2 = pd.Series(
        {
            "optimal_allocation": [50, 30, 20],
            "comparisons": [
                {
                    "option_1": [20, 50, 30],  # sum_diff = 60
                    "option_2": [45, 35, 20],  # sum_diff = 10
                    "user_choice": 1,  # chose larger difference
                },
                {
                    "option_1": [55, 25, 20],  # sum_diff = 10
                    "option_2": [45, 40, 15],  # sum_diff = 20
                    "user_choice": 2,  # chose larger difference
                },
            ],
        }
    )
    result2 = calculate_optimization_stats(row2)
    assert result2["num_of_answers"] == 2
    assert result2["sum_optimized"] == 0
    assert result2["ratio_optimized"] == 2
    assert result2["result"] == "ratio"
