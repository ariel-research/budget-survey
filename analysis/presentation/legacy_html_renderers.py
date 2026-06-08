"""
DEPRECATED: This module contains HTML renderers used exclusively by the old PDF report system.
These functions are maintained only for backward compatibility and should not be used in new code.
For the new web-based report system, see analysis/presentation/html_renderers.py.
"""

import html
import logging
from typing import Dict, List, Tuple

import pandas as pd

from analysis.logic.stats_calculators import (
    calculate_choice_statistics,
    calculate_user_consistency,
    get_summary_value,
)
from application.translations import get_translation

logger = logging.getLogger(__name__)


def generate_executive_summary(
    summary_stats: pd.DataFrame,
    optimization_stats: pd.DataFrame,
    responses_Stats: pd.DataFrame,
) -> str:
    """
    Generate an executive summary of the survey analysis.

    Creates high-level overview: total surveys, users, answers, overall
    preferences, and user consistency.

    Args:
        summary_stats: DataFrame with overall survey statistics.
        optimization_stats: DataFrame with user optimization preferences.
        responses_Stats: DataFrame with survey responses summarization.

    Returns:
        str: HTML-formatted executive summary.
    """
    logger.info("Generating executive summary")
    total_surveys = len(summary_stats) - 1  # Excluding the "Total" row
    total_survey_responses = get_summary_value(summary_stats, "total_survey_responses")
    total_answers = get_summary_value(summary_stats, "total_answers")
    total_uniqe_users = responses_Stats["user_id"].nunique()
    overall_sum_pref = get_summary_value(summary_stats, "sum_optimized_percentage")
    overall_ratio_pref = get_summary_value(summary_stats, "ratio_optimized_percentage")

    # Calculate consistency metrics
    consistency_percentage, qualified_users, _, min_surveys, _ = (
        calculate_user_consistency(optimization_stats)
    )

    # Build content string with f-string for clarity
    report_line = (
        f"This report analyzes {total_surveys} surveys completed by "
        f"{total_survey_responses} users ({total_uniqe_users} unique), "
        f"totaling {total_answers} answers."
    )
    pref_line = (
        f"Overall, users showed a "
        f"{'sum' if overall_sum_pref > overall_ratio_pref else 'ratio'} "
        f"optimization preference ({overall_sum_pref:.2f}% sum vs "
        f"{overall_ratio_pref:.2f}% ratio)."
    )
    consistency_line_1 = (
        f"{consistency_percentage:.2f}% of users who participated in at least "
        f"{min_surveys} surveys consistently preferred the same optimization "
        f"method (sum or ratio) across surveys (80% or more of responses)."
    )
    consistency_line_2 = (
        f"The consistency analysis considered {qualified_users} out of "
        f"{total_survey_responses} survey responses."
    )

    content = f"""
    <p>{report_line}</p>

    <p>Key findings:</p>
    <ol>
        <li>{pref_line}</li>
        <li>{consistency_line_1}</li>
        <li>{consistency_line_2}</li>
    </ol>
    """

    logger.info("Executive summary generation completed")
    return content


def _generate_survey_summary_html(
    choices: List[Dict], option_labels: Tuple[str, str]
) -> str:
    """Generate HTML for survey summary statistics.

    Args:
        choices: List of choices for a survey.
        option_labels: Tuple of labels for the two options.

    Returns:
        str: HTML for the survey summary.
    """
    stats = calculate_choice_statistics(choices)
    opt1_p = stats["option1_percent"]
    opt2_p = stats["option2_percent"]
    highlight1 = "highlight-row" if opt1_p > opt2_p else ""
    highlight2 = "highlight-row" if opt2_p > opt1_p else ""

    # Translations
    title = get_translation("survey_summary", "answers")
    th_choice = get_translation("choice", "answers")
    th_perc = get_translation("percentage", "answers")

    return f"""
    <div class="survey-stats">
        <h6 class="stats-title">{title}</h6>
        <div class="table-container">
            <table>
                <tr>
                    <th>{th_choice}</th>
                    <th>{th_perc}</th>
                </tr>
                <tr class="{highlight1}">
                    <td>{option_labels[0]}</td>
                    <td>{opt1_p:.0f}%</td>
                </tr>
                <tr class="{highlight2}">
                    <td>{option_labels[1]}</td>
                    <td>{opt2_p:.0f}%</td>
                </tr>
            </table>
        </div>
    </div>
    """


def generate_overall_stats(
    summary_stats: pd.DataFrame, optimization_stats: pd.DataFrame
) -> str:
    """
    Generate the overall statistics section of the report.

    Args:
        summary_stats: DataFrame containing summary statistics.
        optimization_stats: DataFrame containing optimization statistics.

    Returns:
        str: HTML-formatted string with overall statistics.
    """
    logger.info("Generating overall statistics section")
    # For now, this is a placeholder or minimal version as per original design.
    # The actual implementation might reuse generate_executive_summary logic
    # or present data tables.
    # Given the original code, this might have been intended for detailed stats.
    # We will simulate a simple table for 'Total' row stats.

    if "Total" not in summary_stats["survey_id"].values:
        return "<p>No overall statistics available.</p>"

    total_row = summary_stats[summary_stats["survey_id"] == "Total"].iloc[0]

    return f"""
    <h3>Overall Statistics</h3>
    <ul>
        <li>Total Surveys: {len(summary_stats) - 1}</li>
        <li>Total Responses: {total_row['total_survey_responses']}</li>
        <li>Total Answers: {total_row['total_answers']}</li>
        <li>Sum Optimized: {total_row['sum_optimized_percentage']:.2f}%</li>
        <li>Ratio Optimized: {total_row['ratio_optimized_percentage']:.2f}%</li>
    </ul>
    """


def generate_survey_analysis(summary_stats: pd.DataFrame) -> str:
    """
    Generate analysis for each individual survey.

    Args:
        summary_stats: DataFrame containing summary statistics per survey.

    Returns:
        str: HTML-formatted string with survey analysis.
    """
    logger.info("Generating survey analysis")
    content = []
    for _, row in summary_stats.iterrows():
        if row["survey_id"] == "Total":
            continue

        survey_id = row["survey_id"]

        content.append(
            f"""
        <div class="survey-analysis-item">
            <h4>Survey {survey_id}</h4>
            <p>Sum Optimized: {row['sum_optimized_percentage']:.1f}%</p>
            <p>Ratio Optimized: {row['ratio_optimized_percentage']:.1f}%</p>
            <p>Responses: {row['total_survey_responses']}</p>
        </div>
        """
        )

    logger.info("Survey analysis generation completed")
    return "\n".join(content)


def generate_individual_analysis(optimization_stats: pd.DataFrame) -> str:
    """
    Generate analysis of individual participant preferences for each survey.

    Args:
        optimization_stats: DataFrame containing optimization statistics.

    Returns:
        str: HTML-formatted string with individual participant analysis.
    """
    logger.info("Generating individual participant analysis")
    content = []
    for survey_id in optimization_stats["survey_id"].unique():
        survey_data = optimization_stats[optimization_stats["survey_id"] == survey_id]
        user_lines = []
        for _, row in survey_data.iterrows():
            sum_perc = row["sum_optimized"] / row["num_of_answers"] * 100
            ratio_perc = row["ratio_optimized"] / row["num_of_answers"] * 100
            user_lines.append(
                f"<li>User {row['user_id']}: {sum_perc:.1f}% sum, "
                f"{ratio_perc:.1f}% ratio optimized</li>"
            )

        content.append(f"<h3>Survey {survey_id}</h3><ul>{''.join(user_lines)}</ul>")

    logger.info("Individual participant analysis generation completed")
    return "\n".join(content)


def generate_user_comments_section(responses_df: pd.DataFrame) -> str:
    """
    Generate HTML content for the user comments section of the report.

    Args:
        responses_df: DataFrame containing survey responses.

    Returns:
        str: HTML formatted string containing all user comments.
    """
    logger.info("Generating user comments section")

    try:
        if "user_comment" not in responses_df.columns:
            logger.warning("user_comment column missing from DataFrame")
            return (
                '<div class="comments-container">'
                '<p class="no-comments">No user comments available.</p></div>'
            )

        df = responses_df.copy()

        # Ensure user_comment is string, handle NaN/None
        df["user_comment"] = df["user_comment"].fillna("").astype(str)

        # Filter out empty comments
        valid_comments = df[df["user_comment"].str.strip() != ""]

        if valid_comments.empty:
            logger.info("No valid comments found")
            return (
                '<div class="comments-container">'
                '<p class="no-comments">No user comments available.</p></div>'
            )

        # Sort by survey_id and survey_response_id
        comments = valid_comments.sort_values(["survey_id", "survey_response_id"])

        # Generate the comments HTML
        content = ['<div class="comments-container">']
        current_survey = None

        for _, row in comments.iterrows():
            # Add survey separator if starting a new survey
            if current_survey != row["survey_id"]:
                if current_survey is not None:
                    content.append("</div>")  # Close previous survey group
                current_survey = row["survey_id"]
                content.append(
                    f'<div class="survey-group"><h3>Survey {current_survey}</h3>'
                )

            # Clean and escape the comment text
            comment_text = html.escape(row["user_comment"].strip())

            # Generate individual comment HTML
            resp_id = row["survey_response_id"]
            comment_html = f"""
                <div class="comment-card">
                    <div class="comment-header">
                        <div class="comment-metadata">
                            <span class="response-id">Response ID: {resp_id}</span>
                        </div>
                    </div>
                    <div class="comment-body">
                        <p class="comment-text">{comment_text}</p>
                    </div>
                </div>
            """
            content.append(comment_html)

        # Close last survey group and main container
        if current_survey is not None:
            content.append("</div>")  # Close final survey group
        content.append("</div>")  # Close main container

        return "\n".join(content)

    except Exception as e:
        logger.error(f"Error generating comments section: {str(e)}", exc_info=True)
        return (
            '<div class="comments-container">'
            '<p class="error">Error generating comments section.</p></div>'
        )


def generate_key_findings(
    summary_stats: pd.DataFrame, optimization_stats: pd.DataFrame
) -> str:
    """
    Generate key findings and conclusions from the survey analysis.

    Args:
        summary_stats: DataFrame containing summary statistics.
        optimization_stats: DataFrame containing optimization statistics.

    Returns:
        str: HTML-formatted string with key findings and conclusions.
    """
    logger.info("Generating key findings and conclusions")
    # Ensure 'Total' row exists before accessing
    if "Total" not in summary_stats["survey_id"].values:
        logger.error(
            "Cannot generate key findings: 'Total' row missing in summary_stats."
        )
        return "<p>Error: Summary statistics are incomplete.</p>"

    total_row = summary_stats[summary_stats["survey_id"] == "Total"].iloc[0]
    sum_pref = total_row["sum_optimized_percentage"]
    ratio_pref = total_row["ratio_optimized_percentage"]
    overall_preference = "sum" if sum_pref > ratio_pref else "ratio"

    findings = []
    findings.append(
        f"<strong>Overall Preference:</strong> Across all surveys, participants "
        f"showed a general preference for {overall_preference} optimization "
        f"({sum_pref:.2f}% sum vs {ratio_pref:.2f}% ratio)."
    )

    try:
        (
            consistency_percentage,
            qualified_users,
            total_survey_responses,
            min_surveys,
            _,
        ) = calculate_user_consistency(optimization_stats)
        consistency_text = (
            f"<strong>Individual Consistency:</strong> {consistency_percentage:.2f}% "
            f"of users in >= {min_surveys} surveys showed consistent preferences "
            f"(80%+). Analysis included {qualified_users}/{total_survey_responses} "
            f"responses."
        )
        findings.append(consistency_text)

        # Check if 'result' column exists and is not empty
        if (
            "result" in optimization_stats.columns
            and not optimization_stats["result"].empty
        ):
            most_common_result = optimization_stats["result"].mode().iloc[0]
            result_counts = (
                optimization_stats["result"].value_counts(normalize=True) * 100
            )
            common_pref_text = (
                f"<strong>Most Common Preference:</strong> The most common preference was "
                f'"{most_common_result}" (Sum: {result_counts.get("sum", 0):.2f}%, '
                f'Ratio: {result_counts.get("ratio", 0):.2f}%, '
                f'Equal: {result_counts.get("equal", 0):.2f}%).'
            )
            findings.append(common_pref_text)
        else:
            findings.append(
                "<strong>Preference Distribution:</strong> Data unavailable."
            )

    except Exception as e:
        logger.error(f"Error calculating detailed findings: {str(e)}", exc_info=True)
        findings.append(
            "<strong>Data Analysis:</strong> Unable to calculate detailed statistics."
        )

    # Format as list items
    list_items = "\n".join([f"<li>{item}</li>" for item in findings])
    content = f"<ol>\n{list_items}\n</ol>"

    logger.info("Key findings and conclusions generation completed")
    return content


def generate_methodology_description() -> str:
    """Generate a description of the methodology used in the analysis."""
    logger.info("Generating methodology description")
    # Split long lines for readability
    steps = [
        "Data Collection: Survey responses collected from participants.",
        "Data Processing: Responses processed for optimization preferences.",
        "Analysis: Overall preferences, individual survey trends, and user "
        "consistency (>= 80% preference in >= half surveys, min 2) calculated.",
        "Visualization: Charts and tables generated.",
        "Reporting: Automated report summarizes key findings.",
    ]
    analysis_details = (
        "<li>Overall preferences aggregated across all surveys.</li>"
        "<li>Individual survey analysis identified trends within each survey.</li>"
        "<li>User consistency evaluated for multi-survey participants.</li>"
    )
    note = (
        "Note: Consistency requires same preference in >= 80% of surveys "
        "(min 2 surveys, >= half of total surveys)."
    )

    methodology = f"""
    <p>This analysis followed these steps:</p>
    <ol>
        <li>{steps[0]}</li>
        <li>{steps[1]}</li>
        <li>Analysis:
            <ul>{analysis_details}</ul>
        </li>
        <li>{steps[3]}</li>
        <li>{steps[4]}</li>
    </ol>
    <p>{note}</p>
    """
    logger.info("Methodology description generation completed")
    return methodology
