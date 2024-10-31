import logging
import math

import pandas as pd

logger = logging.getLogger(__name__)


def get_summary_value(df: pd.DataFrame, column: str) -> float:
    """
    Retrieve a specific value from the 'Total' row of a summary DataFrame.

    Args:
        df (pd.DataFrame): The summary DataFrame containing a 'Total' row.
        column (str): The name of the column from which to retrieve the value.

    Returns:
        float: The value from the specified column in the 'Total' row.
    """
    logger.debug(f"Retrieving summary value for column: {column}")
    return df.loc[df["survey_id"] == "Total", column].values[0]


def calculate_user_consistency(
    optimization_stats: pd.DataFrame, consistency_threshold: float = 0.8
) -> tuple[float, int, int, int, int]:
    """
    Calculate the percentage of users with consistent preferences across surveys.

    Methodology:
    1. Determine the minimum number of surveys required for analysis (min_surveys).
    2. Identify users who have completed at least min_surveys (qualified users).
    3. For each qualified user, calculate their consistency ratio:
       - Count the occurrences of each unique result (sum/ratio/equal).
       - Divide the count of the most frequent result by the total number of surveys taken.
    4. Users with a consistency ratio >= consistency_threshold are considered consistent.
    5. Calculate the percentage of consistent users among qualified users.

    Args:
    optimization_stats (pd.DataFrame): DataFrame containing user survey results.
    consistency_threshold (float): Minimum consistency ratio to be considered consistent (default: 0.8).

    Returns:
    tuple: (consistent_percentage, total_qualified_users, total_users, min_surveys, total_surveys)
        - consistent_percentage: Percentage of users with consistent preferences.
        - total_qualified_users: Number of users who completed the minimum required surveys.
        - total_users: Total number of users in the dataset.
        - min_surveys: Minimum number of surveys required for consistency analysis.
        - total_surveys: Total number of unique surveys in the dataset.
    """
    logger.info(f"Calculating user consistency with threshold {consistency_threshold}")

    total_surveys = optimization_stats["survey_id"].nunique()

    # Set minimum surveys to the max of: 2 or half the total surveys (rounded up)
    min_surveys = max(2, math.ceil(total_surveys / 2))

    # Count surveys per user
    survey_counts = optimization_stats.groupby("user_id")["survey_id"].nunique()

    # Filter users with at least min_surveys
    qualified_users = survey_counts[survey_counts >= min_surveys].index

    # Calculate consistency for qualified users
    user_consistency = (
        optimization_stats[optimization_stats["user_id"].isin(qualified_users)]
        .groupby("user_id")["result"]
        .agg(lambda x: x.value_counts().iloc[0] / len(x))
    )

    # Count users above the consistency threshold
    consistent_users = (user_consistency >= consistency_threshold).sum()
    total_qualified_users = len(qualified_users)

    # Calculate percentage of consistent users
    consistent_percentage = (
        (consistent_users / total_qualified_users) * 100
        if total_qualified_users > 0
        else 0
    )

    logger.info(
        f"User consistency calculation completed. Consistent users: {consistent_users}, Total qualified users: {total_qualified_users}"
    )
    return (
        consistent_percentage,
        total_qualified_users,
        len(survey_counts),
        min_surveys,
        total_surveys,
    )


def generate_executive_summary(
    summary_stats: pd.DataFrame, optimization_stats: pd.DataFrame
) -> str:
    """
    Generate an executive summary of the survey analysis.

    This function creates a high-level overview of the survey results,
    including total surveys, users, answers, overall preferences,
    and user consistency across surveys.

    Args:
        summary_stats (pd.DataFrame): DataFrame containing overall survey statistics.
        optimization_stats (pd.DataFrame): DataFrame containing user optimization preferences.

    Returns:
        str: HTML-formatted string containing the executive summary.
    """
    logger.info("Generating executive summary")
    total_surveys = len(summary_stats) - 1  # Excluding the "Total" row
    total_users = get_summary_value(summary_stats, "unique_users")
    total_answers = get_summary_value(summary_stats, "total_answers")
    overall_sum_pref = get_summary_value(summary_stats, "sum_optimized_percentage")
    overall_ratio_pref = get_summary_value(summary_stats, "ratio_optimized_percentage")

    # Calculate consistency metrics
    consistency_percentage, qualified_users, _, min_surveys, _ = (
        calculate_user_consistency(optimization_stats)
    )

    content = f"""
    <p>This report analyzes {total_surveys} surveys completed by {total_users} unique users, totaling {total_answers} answers.</p>
    
    <p>Key findings:</p>
    <ol>
        <li>Overall, users showed a {'sum' if overall_sum_pref > overall_ratio_pref else 'ratio'} optimization preference 
           ({overall_sum_pref:.2f}% sum vs {overall_ratio_pref:.2f}% ratio).</li>
        <li>{consistency_percentage:.2f}% of users who participated in at least {min_surveys} surveys consistently preferred the same optimization method (sum or ratio) across surveys (80% or more of their responses).</li>
        <li>The consistency analysis considered {qualified_users} out of {total_users} total users.</li>
    </ol>
    """

    logger.info("Executive summary generation completed")
    return content


def generate_overall_stats(summary_stats: pd.DataFrame) -> str:
    """
    Generate a string containing overall survey participation statistics.

    Args:
        summary_stats (pd.DataFrame): DataFrame containing summary statistics.

    Returns:
        str: HTML-formatted string with overall statistics.
    """
    logger.info("Generating overall statistics")
    total_row = summary_stats.iloc[-1]
    content = f"""
    <ul>
        <li>Total number of surveys: {len(summary_stats) - 1}</li>
        <li>Total number of participants: {total_row['unique_users']}</li>
        <li>Total answers collected: {total_row['total_answers']}</li>
    </ul>
    """
    logger.info("Overall statistics generation completed")
    return content


def generate_survey_analysis(summary_stats: pd.DataFrame) -> str:
    """
    Generate a detailed analysis for each survey.

    Args:
        summary_stats (pd.DataFrame): DataFrame containing summary statistics.

    Returns:
        str: HTML-formatted string with survey-wise analysis.
    """
    logger.info("Generating survey-wise analysis")
    content = ""
    for _, row in summary_stats[summary_stats["survey_id"] != "Total"].iterrows():
        preference = (
            "sum"
            if row["sum_optimized_percentage"] > row["ratio_optimized_percentage"]
            else "ratio"
        )
        strength = abs(
            row["sum_optimized_percentage"] - row["ratio_optimized_percentage"]
        )

        if strength < 10:
            interpretation = "no clear preference"
        elif strength < 30:
            interpretation = f"a slight preference for {preference} optimization"
        else:
            interpretation = f"a strong preference for {preference} optimization"

        content += f"""
        <h3>Survey {row['survey_id']}</h3>
        <p>This survey had {row['unique_users']} participants who provided a total of {row['total_answers']} answers.</p>
        <p>The results show {interpretation}:</p>
        <ul>
            <li>Sum optimization: {row['sum_optimized_percentage']:.2f}%</li>
            <li>Ratio optimization: {row['ratio_optimized_percentage']:.2f}%</li>
        </ul>
        <p>Individual user preferences:</p>
        <ul>
            <li>{row['sum_count']} users preferred sum optimization</li>
            <li>{row['ratio_count']} users preferred ratio optimization</li>
            <li>{row['equal_count']} users showed no clear preference</li>
        </ul>
        """
    logger.info("Survey-wise analysis generation completed")
    return content


def generate_individual_analysis(optimization_stats: pd.DataFrame) -> str:
    """
    Generate an analysis of individual participant preferences for each survey.

    Args:
        optimization_stats (pd.DataFrame): DataFrame containing optimization statistics.

    Returns:
        str: HTML-formatted string with individual participant analysis.
    """
    logger.info("Generating individual participant analysis")
    content = ""
    for survey_id in optimization_stats["survey_id"].unique():
        content += f"<h3>Survey {survey_id}</h3><ul>"
        survey_data = optimization_stats[optimization_stats["survey_id"] == survey_id]
        for _, row in survey_data.iterrows():
            content += f"<li>User {row['user_id']}: {row['sum_optimized'] / row['num_of_answers'] * 100:.1f}% sum optimized, {row['ratio_optimized'] / row['num_of_answers'] * 100:.1f}% ratio optimized</li>"
        content += "</ul>"
    logger.info("Individual participant analysis generation completed")
    return content


def generate_key_findings(
    summary_stats: pd.DataFrame, optimization_stats: pd.DataFrame
) -> str:
    """
    Generate key findings and conclusions from the survey analysis.

    Args:
        summary_stats (pd.DataFrame): DataFrame containing summary statistics.
        optimization_stats (pd.DataFrame): DataFrame containing optimization statistics.

    Returns:
        str: HTML-formatted string with key findings and conclusions.
    """
    logger.info("Generating key findings and conclusions")
    total_row = summary_stats.iloc[-1]
    overall_preference = (
        "sum" if total_row["sum_optimized"] > total_row["ratio_optimized"] else "ratio"
    )
    content = f"""
    <ol>
        <li>
            <strong>Overall Preference:</strong> Across all surveys, participants showed a general preference for {overall_preference} optimization 
            ({total_row['sum_optimized_percentage']:.2f}% sum vs {total_row['ratio_optimized_percentage']:.2f}% ratio).
        </li>
    """

    try:
        consistency_percentage, qualified_users, total_users, min_surveys, _ = (
            calculate_user_consistency(optimization_stats)
        )
        content += f"""
            <li>
                <strong>Individual Consistency:</strong> {consistency_percentage:.2f}% of users who participated in at least {min_surveys} surveys 
                showed consistent optimization preferences (80% or more consistent). This analysis considered {qualified_users} out of {total_users} total users.
            </li>
        """

        most_common_result = optimization_stats["result"].mode().iloc[0]
        result_counts = optimization_stats["result"].value_counts(normalize=True) * 100
        content += f"""
            <li>
                <strong>Most Common Preference:</strong> The most common optimization preference was "{most_common_result}" 
                (Sum: {result_counts.get('sum', 0):.2f}%, Ratio: {result_counts.get('ratio', 0):.2f}%, Equal: {result_counts.get('equal', 0):.2f}%).
            </li>
        """
    except Exception as e:
        logger.error(f"Error in calculating key findings: {str(e)}", exc_info=True)
        content += """
            <li>
                <strong>Data Analysis:</strong> Unable to calculate detailed statistics due to data processing error.
            </li>
        """

    content += "</ol>"
    logger.info("Key findings and conclusions generation completed")
    return content


def generate_methodology_description() -> str:
    """Generate a description of the methodology used in the analysis."""
    logger.info("Generating methodology description")
    methodology = """
    <p>This analysis was conducted using the following steps:</p>
    <ol>
        <li>Data Collection: Survey responses were collected from participants across multiple surveys.</li>
        <li>Data Processing: Responses were processed to calculate optimization preferences (sum vs ratio) for each user in each survey.</li>
        <li>Analysis:
            <ul>
                <li>Overall preferences were calculated by aggregating responses across all surveys.</li>
                <li>Individual survey analysis was performed to identify trends within each survey.</li>
                <li>User consistency was evaluated for participants who completed multiple surveys.</li>
            </ul>
        </li>
        <li>Visualization: Various charts and tables were generated to represent the findings visually.</li>
        <li>Reporting: This automated report was generated to summarize the key findings and present the analysis results.</li>
    </ol>
    <p>Note: The analysis considers a user's preference as consistent if they show the same optimization preference in at least 80% of the surveys they participated in, given they participated in at least half of the total surveys and at least two surveys.</p>
    """
    logger.info("Methodology description generation completed")
    return methodology
