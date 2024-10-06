import logging

import pandas as pd

from analysis.analysis_utils import (
    calculate_optimization_stats,
    process_survey_responses,
    save_dataframe_to_csv,
)
from app import create_app
from database.queries import retrieve_completed_survey_responses

logger = logging.getLogger(__name__)

app = create_app()


def get_all_completed_survey_responses() -> pd.DataFrame:
    """
    Retrieves and processes all completed survey responses.

    Returns:
        pd.DataFrame: A DataFrame containing processed survey response data.
    """
    try:
        with app.app_context():
            raw_results = retrieve_completed_survey_responses()
        processed_results = process_survey_responses(raw_results)
        df: pd.DataFrame = pd.DataFrame(processed_results)
        logger.info(f"Successfully retrieved and processed {len(df)} survey responses")
        return df
    except Exception as e:
        logger.error(f"Error in get_all_completed_survey_responses: {e}")
        raise


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

    # Create a summary row
    summary = pd.DataFrame(
        {
            "survey_id": ["Total"],
            "unique_users": [grouped["unique_users"].sum()],
            "total_answers": [grouped["total_answers"].sum()],
            "sum_optimized": [grouped["sum_optimized"].sum()],
            "ratio_optimized": [grouped["ratio_optimized"].sum()],
            "sum_optimized_percentage": [
                (grouped["sum_optimized"].sum() / grouped["total_answers"].sum()) * 100
            ],
            "ratio_optimized_percentage": [
                (grouped["ratio_optimized"].sum() / grouped["total_answers"].sum())
                * 100
            ],
            "sum_count": [grouped["sum_count"].sum()],
            "ratio_count": [grouped["ratio_count"].sum()],
            "equal_count": [grouped["equal_count"].sum()],
            "sum_percentage": [
                (grouped["sum_count"].sum() / grouped["total_answers"].sum()) * 100 * 10
            ],
            "ratio_percentage": [
                (grouped["ratio_count"].sum() / grouped["total_answers"].sum())
                * 100
                * 10
            ],
            "equal_percentage": [
                (grouped["equal_count"].sum() / grouped["total_answers"].sum())
                * 100
                * 10
            ],
        }
    )

    # Concatenate the grouped data with the summary row
    result = pd.concat([grouped, summary], ignore_index=True)
    print(result)
    return result


def main() -> None:
    logger.info("Starting survey analysis process")
    try:
        # Retrieve and process survey responses and save
        all_completed_survey_responses_df = get_all_completed_survey_responses()

        save_dataframe_to_csv(
            all_completed_survey_responses_df, "data/all_completed_survey_responses.csv"
        )

        # Generate and save optimization stats
        survey_optimization_stats_df = generate_survey_optimization_stats(
            all_completed_survey_responses_df
        )
        save_dataframe_to_csv(
            survey_optimization_stats_df, "data/survey_optimization_stats.csv"
        )

        # Summarize and save stats by survey
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
