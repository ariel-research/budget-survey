import pandas as pd
import pytest


@pytest.fixture
def sample_summary_stats():
    """Create sample summary statistics DataFrame."""
    return pd.DataFrame(
        {
            "survey_id": ["1", "2", "Total"],
            "total_survey_responses": [5, 3, 8],
            "unique_users": [5, 3, 8],
            "total_answers": [50, 30, 80],
            "sum_optimized": [30, 15, 45],
            "ratio_optimized": [20, 15, 35],
            "sum_optimized_percentage": [60.0, 50.0, 56.25],
            "ratio_optimized_percentage": [40.0, 50.0, 43.75],
            "sum_count": [3, 2, 5],
            "ratio_count": [2, 1, 3],
            "equal_count": [0, 0, 0],
        }
    )


@pytest.fixture
def sample_optimization_stats():
    """Create sample optimization statistics DataFrame."""
    return pd.DataFrame(
        {
            "survey_id": [1, 1, 2, 2],
            "user_id": [101, 102, 101, 103],
            "num_of_answers": [10, 10, 10, 10],
            "sum_optimized": [7, 4, 6, 8],
            "ratio_optimized": [3, 6, 4, 2],
            "result": ["sum", "ratio", "sum", "sum"],
        }
    )


@pytest.fixture
def sample_survey_responses():
    """Create sample survey responses DataFrame."""
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
