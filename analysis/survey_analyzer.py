import logging

import pandas as pd

from analysis.analysis_utils import is_sum_optimized
from analysis.survey_processor import (
    get_all_completed_survey_responses,
    process_data_to_dataframe,
)

logger = logging.getLogger(__name__)


def calculate_optimization_stats(row: pd.Series) -> pd.Series:
    """
    Calculate optimization statistics for a single survey response.

    Args:
        row (pd.Series): A row from the survey response DataFrame.

    Returns:
        pd.Series: Statistics including number of answers, sum and ratio optimized choices, and overall result.
    """
    sum_optimized_choices = 0
    ratio_optimized_choices = 0
    total_comparisons = len(row["comparisons"])

    for comparison in row["comparisons"]:
        if is_sum_optimized(
            row["optimal_allocation"],
            comparison["option_1"],
            comparison["option_2"],
            comparison["user_choice"],
        ):
            sum_optimized_choices += 1
        else:
            ratio_optimized_choices += 1

    result = (
        "sum"
        if sum_optimized_choices > ratio_optimized_choices
        else "ratio" if sum_optimized_choices < ratio_optimized_choices else "equal"
    )

    return pd.Series(
        {
            "num_of_answers": total_comparisons,
            "sum_optimized": sum_optimized_choices,
            "ratio_optimized": ratio_optimized_choices,
            "result": result,
        }
    )


def generate_survey_optimization_stats(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate optimization statistics for all survey responses.

    Args:
        df (pd.DataFrame): DataFrame containing survey response data.

    Returns:
        pd.DataFrame: DataFrame with survey response IDs and optimization statistics.
    """
    stats = df.apply(calculate_optimization_stats, axis=1)

    result_df = pd.concat([df[["survey_response_id", "user_id"]], stats], axis=1)

    print(result_df.head())
    return result_df


def main() -> None:
    """
    Main function to run the survey analysis process.
    """
    try:
        results = get_all_completed_survey_responses()
        df = process_data_to_dataframe(results)
        generate_survey_optimization_stats(df)
        logger.info("Survey analysis completed successfully")
    except Exception as e:
        logger.error(f"Error in main execution: {e}", exc_info=True)


if __name__ == "__main__":
    main()
