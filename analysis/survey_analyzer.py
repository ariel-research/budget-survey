import logging

import pandas as pd

from analysis.analysis_utils import is_sum_optimized, save_dataframe_to_csv
from analysis.survey_processor import get_all_completed_survey_responses

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
    logger.info(f"Generating optimization stats for {len(df)} survey responses")
    stats = df.apply(calculate_optimization_stats, axis=1)

    result_df = pd.concat([df[["survey_id", "user_id"]], stats], axis=1)
    logger.info(f"Optimization stats generated. Result shape: {result_df.shape}")

    return result_df


def summarize_stats_by_survey(df: pd.DataFrame) -> pd.DataFrame:
    """
    Summarize statistics by survey_id.

    Args:
        df (pd.DataFrame): DataFrame containing survey results.

    Returns:
        pd.DataFrame: Summarized statistics by survey_id.
    """
    grouped = (
        df.groupby("survey_id")
        .agg(
            {
                "user_id": "nunique",
                "num_of_answers": "sum",
                "sum_optimized": "sum",
                "ratio_optimized": "sum",
                "result": lambda x: x.value_counts().to_dict(),
            }
        )
        .reset_index()
    )

    # Rename columns for clarity
    grouped.columns = [
        "survey_id",
        "unique_users",
        "total_answers",
        "sum_optimized",
        "ratio_optimized",
        "result_counts",
    ]

    # Calculate percentages
    grouped["sum_optimized_percentage"] = (
        grouped["sum_optimized"] / grouped["total_answers"]
    ) * 100
    grouped["ratio_optimized_percentage"] = (
        grouped["ratio_optimized"] / grouped["total_answers"]
    ) * 100

    # Extract individual result counts
    grouped["sum_count"] = grouped["result_counts"].apply(lambda x: x.get("sum", 0))
    grouped["ratio_count"] = grouped["result_counts"].apply(lambda x: x.get("ratio", 0))
    grouped["equal_count"] = grouped["result_counts"].apply(lambda x: x.get("equal", 0))

    # Calculate result percentages
    total_results = (
        grouped["sum_count"] + grouped["ratio_count"] + grouped["equal_count"]
    )
    grouped["sum_percentage"] = (grouped["sum_count"] / total_results) * 100
    grouped["ratio_percentage"] = (grouped["ratio_count"] / total_results) * 100
    grouped["equal_percentage"] = (grouped["equal_count"] / total_results) * 100

    # Drop the intermediate 'result_counts' column
    grouped = grouped.drop("result_counts", axis=1)

    return grouped


def main() -> None:
    """
    Main function to run the survey analysis process.
    """
    logger.info("Starting survey analysis process")
    try:
        results = get_all_completed_survey_responses()
        logger.info(f"Retrieved {len(results)} completed survey responses")

        df = pd.DataFrame(results)
        logger.info(f"Processed survey data to DataFrame. Shape: {df.shape}")

        survey_optimization_stats_df = generate_survey_optimization_stats(df)
        save_dataframe_to_csv(
            survey_optimization_stats_df, "data/survey_optimization_stats.csv"
        )

        summarize_stats_by_survey_df = summarize_stats_by_survey(
            survey_optimization_stats_df
        )
        save_dataframe_to_csv(
            summarize_stats_by_survey_df, "data/summarize_stats_by_survey.csv"
        )

        logger.info("Survey analysis completed successfully")
    except Exception as e:
        logger.error(f"Error in main execution: {e}", exc_info=True)


if __name__ == "__main__":
    main()
