import html
import json
import logging
import math
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd

from analysis.utils import is_sum_optimized
from application.translations import get_translation

logger = logging.getLogger(__name__)

# Constants
EXTREME_VECTOR_EXPECTED_PAIRS = 12  # 3 core + 3*3 weighted = 12
WEIGHTED_PAIRS_PER_GROUP = 3  # Number of weighted pairs per comparison group


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
    Calculate user consistency percentage across surveys.

    Methodology:
    1. Determine min surveys required for analysis.
    2. Identify users who completed at least min_surveys (qualified users).
    3. For each qualified user, calculate consistency ratio:
       - Count occurrences of each unique result (sum/ratio/equal).
       - Divide max count by total surveys taken.
    4. Users with ratio >= threshold are consistent.
    5. Calculate percentage of consistent users among qualified.

    Args:
    optimization_stats: DataFrame with user survey results.
    consistency_threshold: Min ratio to be considered consistent (default: 0.8).

    Returns:
    tuple: (consistency_%, qualified_users, total_responses, min_surveys, total_surveys)
        - consistency_%: Percentage of users with consistent preferences.
        - qualified_users: # users completing min required surveys.
        - total_responses: Total number of survey responses in dataset.
        - min_surveys: Minimum surveys for consistency analysis.
        - total_surveys: Total unique surveys in dataset.
    """
    logger.info(f"Calculating user consistency (threshold {consistency_threshold})")

    total_surveys = optimization_stats["survey_id"].nunique()

    # Min surveys: max of 2 or half the total (rounded up)
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
        f"Consistency: {consistent_percentage:.1f}% ({consistent_users}/"
        + f"{total_qualified_users} qualified users)"
    )
    return (
        consistent_percentage,
        total_qualified_users,
        len(survey_counts),
        min_surveys,
        total_surveys,
    )


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


def generate_overall_stats(
    summary_stats: pd.DataFrame, optimization_stats: pd.DataFrame
) -> str:
    """
    Generate a string containing overall survey participation statistics.

    Args:
        summary_stats: DataFrame containing summary statistics.
        optimization_stats: DataFrame containing optimization statistics.

    Returns:
        str: HTML-formatted string with overall statistics.
    """
    logger.info("Generating overall statistics")

    total_surveys = len(summary_stats) - 1  # Excluding the 'Total' row
    total_survey_responses = summary_stats.iloc[-1][
        "total_survey_responses"
    ]  # Total participant entries
    unique_users = optimization_stats["user_id"].nunique()  # Actual unique participants
    total_answers = summary_stats.iloc[-1]["total_answers"]

    # Handle potential division by zero if no responses
    avg_answers_per_user = (
        (total_answers / total_survey_responses) if total_survey_responses > 0 else 0
    )
    multi_survey_users = total_survey_responses - unique_users

    content = f"""
    <div class="statistics-container">
        <div class="statistic-group">
            <h3>Survey Overview</h3>
            <ul>
                <li>Number of different surveys conducted: {total_surveys}</li>
            </ul>
        </div>

        <div class="statistic-group">
            <h3>Participation Statistics</h3>
            <ul>
                <li>Total survey responses: {total_survey_responses}
                    <ul>
                        <li>Unique participants: {unique_users}</li>
                        <li>Participants who took multiple surveys: {multi_survey_users}</li>
                    </ul>
                </li>
            </ul>
        </div>

        <div class="statistic-group">
            <h3>Response Details</h3>
            <ul>
                <li>Total answers collected: {total_answers}</li>
                <li>Average answers per survey response: {avg_answers_per_user:.1f}</li>
            </ul>
        </div>
    </div>
    """

    logger.info("Overall statistics generation completed")
    return content


def generate_survey_analysis(summary_stats: pd.DataFrame) -> str:
    """
    Generate a detailed analysis for each survey.

    Args:
        summary_stats: DataFrame containing summary statistics.

    Returns:
        str: HTML-formatted string with survey-wise analysis.
    """
    logger.info("Generating survey-wise analysis")
    content = []
    # Iterate only over actual surveys, excluding the 'Total' row
    for _, row in summary_stats[summary_stats["survey_id"] != "Total"].iterrows():
        sum_pref = row["sum_optimized_percentage"]
        ratio_pref = row["ratio_optimized_percentage"]
        preference = "sum" if sum_pref > ratio_pref else "ratio"
        strength = abs(sum_pref - ratio_pref)

        if strength < 10:
            interpretation = "no clear preference"
        elif strength < 30:
            interpretation = f"a slight preference for {preference} optimization"
        else:
            interpretation = f"a strong preference for {preference} optimization"

        survey_content = f"""
        <h3>Survey {row['survey_id']}</h3>
        <p>This survey had {row['total_survey_responses']} participants 
           providing {row['total_answers']} answers.</p>
        <p>The results show {interpretation}:</p>
        <ul>
            <li>Sum optimization: {sum_pref:.2f}%</li>
            <li>Ratio optimization: {ratio_pref:.2f}%</li>
        </ul>
        <p>Individual user preferences:</p>
        <ul>
            <li>{row['sum_count']} users preferred sum optimization</li>
            <li>{row['ratio_count']} users preferred ratio optimization</li>
            <li>{row['equal_count']} users showed no clear preference</li>
        </ul>
        """
        content.append(survey_content)

    logger.info("Survey-wise analysis generation completed")
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


def choice_explanation_string_version1(
    optimal_allocation: tuple, option_1: tuple, option_2: tuple, user_choice: int
) -> str:
    """
    Explain user's choice between two options (version 1).
    """
    is_sum = is_sum_optimized(
        tuple(optimal_allocation), tuple(option_1), tuple(option_2), user_choice
    )
    opt_type = "Sum" if is_sum else "Ratio"
    css_class = "optimization-sum" if is_sum else "optimization-ratio"
    chosen = "(1)" if user_choice == 1 else "(2)"
    return (
        f"{str(option_1)} vs {str(option_2)} → "
        f"<span class='{css_class}'>{opt_type}</span> {chosen}"
    )


def calculate_choice_statistics(choices: List[Dict]) -> Dict[str, float]:
    """
    Calculate optimization and answer choice statistics for a set of choices.

    Args:
        choices: List of choices for a single user's survey response.
                 Requires: optimal_allocation, option_1, option_2, user_choice

    Returns:
        Dict with percentages: sum_percent, ratio_percent,
                               option1_percent, option2_percent
    """
    total_choices = len(choices)
    if total_choices == 0:
        return {
            "sum_percent": 0,
            "ratio_percent": 0,
            "option1_percent": 0,
            "option2_percent": 0,
        }

    sum_optimized = 0
    option1_count = 0

    for choice in choices:
        optimal = json.loads(choice["optimal_allocation"])
        opt1 = json.loads(choice["option_1"])
        opt2 = json.loads(choice["option_2"])
        user_choice = choice["user_choice"]

        # Determine if choice optimizes sum or ratio
        is_sum = is_sum_optimized(optimal, opt1, opt2, user_choice)
        if is_sum:
            sum_optimized += 1

        # Count option choices
        if user_choice == 1:
            option1_count += 1

    sum_p = (sum_optimized / total_choices) * 100
    ratio_p = ((total_choices - sum_optimized) / total_choices) * 100
    opt1_p = (option1_count / total_choices) * 100
    opt2_p = ((total_choices - option1_count) / total_choices) * 100

    return {
        "sum_percent": sum_p,
        "ratio_percent": ratio_p,
        "option1_percent": opt1_p,
        "option2_percent": opt2_p,
    }


def choice_explanation_string_version2(
    optimal_allocation: tuple, option_1: tuple, option_2: tuple, user_choice: int
) -> str:
    """
    Explain user's choice between two options (formatted table, version 2).
    """
    from application.services.pair_generation import OptimizationMetricsStrategy
    from application.translations import get_translation

    strategy = OptimizationMetricsStrategy()  # Create instance
    sum_diff_1 = strategy.sum_of_differences(optimal_allocation, option_1)
    sum_diff_2 = strategy.sum_of_differences(optimal_allocation, option_2)
    min_ratio_1 = strategy.minimal_ratio(optimal_allocation, option_1)
    min_ratio_2 = strategy.minimal_ratio(optimal_allocation, option_2)

    user_choice_type = "none"
    # Determine if user choice aligns with sum or ratio optimization criteria
    if sum_diff_1 < sum_diff_2 and min_ratio_1 < min_ratio_2:
        # Option 1 is strictly better by both metrics
        user_choice_type = "sum" if user_choice == 1 else "ratio"
    elif sum_diff_1 > sum_diff_2 and min_ratio_1 > min_ratio_2:
        # Option 2 is strictly better by both metrics
        user_choice_type = "sum" if user_choice == 2 else "ratio"
    # Add more cases if needed for mixed scenarios

    # Format values for the table
    check_1 = "✓" if user_choice == 1 else ""
    check_2 = "✓" if user_choice == 2 else ""
    better_sum_1 = "better" if sum_diff_1 < sum_diff_2 else ""
    better_sum_2 = "better" if sum_diff_2 < sum_diff_1 else ""
    better_ratio_1 = "better" if min_ratio_1 > min_ratio_2 else ""
    better_ratio_2 = "better" if min_ratio_2 > min_ratio_1 else ""

    # Get translations
    user_optimizes = get_translation("user_optimizes", "answers")
    choice_label = get_translation("table_choice", "answers")
    option_label = get_translation("table_option", "answers")
    sum_diff_label = get_translation("sum_of_differences", "answers")
    min_ratio_label = get_translation("minimum_ratio", "answers")
    opt_type_trans = get_translation(
        user_choice_type, "answers", fallback=user_choice_type
    )

    return f"""
            <span class="user-optimizes user-optimizes-{user_choice_type}">
                {user_optimizes}: {opt_type_trans}
            </span>
            <div class="table-container">
                <table>
                    <tr>
                        <th>{choice_label}</th>
                        <th>{option_label}</th>
                        <th>{sum_diff_label}</th>
                        <th>{min_ratio_label}</th>
                    </tr>
                    <tr>
                        <td class="selection-column">{check_1}</td>
                        <td class="option-column">{str(option_1)}</td>
                        <td class="{better_sum_1}">{sum_diff_1}</td>
                        <td class="{better_ratio_1}">{round(min_ratio_1, 3)}</td>
                    </tr>
                    <tr>
                        <td class="selection-column">{check_2}</td>
                        <td class="option-column">{str(option_2)}</td>
                        <td class="{better_sum_2}">{sum_diff_2}</td>
                        <td class="{better_ratio_2}">{round(min_ratio_2, 3)}</td>
                    </tr>
                </table>
            </div>
    """


def _generate_choice_pair_html(choice: Dict, option_labels: Tuple[str, str]) -> str:
    """Generate HTML for a single choice pair."""
    option_1 = json.loads(choice["option_1"])
    option_2 = json.loads(choice["option_2"])
    user_choice = choice["user_choice"]
    raw_choice = choice.get("raw_user_choice")

    # Get strategy labels: DB -> survey -> default
    strategy_1 = choice.get("option1_strategy")
    strategy_2 = choice.get("option2_strategy")

    if not strategy_1 and not strategy_2:
        survey_labels = choice.get("strategy_labels", option_labels)
        strategy_1 = survey_labels[0]
        strategy_2 = survey_labels[1]

    # Generate raw choice info HTML
    trans_orig = get_translation("original_choice", "answers")
    trans_opt = get_translation("option_number", "answers", number=raw_choice)
    trans_na = get_translation("not_available", "answers")
    raw_choice_html = (
        f'<span class="raw-choice-label">{trans_orig}: </span>'
        f'<span class="raw-choice-value">{trans_opt}</span>'
        if raw_choice is not None
        else f'<span class="raw-choice-unavailable">{trans_orig}: {trans_na}</span>'
    )

    # Table headers
    th_choice = get_translation("table_choice", "answers")
    th_option = get_translation("table_option", "answers")
    th_type = get_translation("table_type", "answers")
    pair_num_label = get_translation("pair_number", "answers")

    check_1 = "✓" if user_choice == 1 else ""
    check_2 = "✓" if user_choice == 2 else ""

    return f"""
    <div class="choice-pair">
        <div class="pair-header">
            <h5>{pair_num_label} #{choice["pair_number"]}</h5>
            <div class="raw-choice-info">
                {raw_choice_html}
            </div>
        </div>
        <div class="table-container">
            <table>
                <tr>
                    <th>{th_choice}</th>
                    <th>{th_option}</th>
                    <th>{th_type}</th>
                </tr>
                <tr>
                    <td class="selection-column">{check_1}</td>
                    <td class="option-column">{str(option_1)}</td>
                    <td>{strategy_1}</td>
                </tr>
                <tr>
                    <td class="selection-column">{check_2}</td>
                    <td class="option-column">{str(option_2)}</td>
                    <td>{strategy_2}</td>
                </tr>
            </table>
        </div>
    </div>
    """


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


def _generate_extreme_vector_consistency_summary(choices: List[Dict]) -> str:
    """
    Generate a simple consistency summary for extreme vector surveys.

    Args:
        choices: List of choices for a single user's survey response using the
                extreme_vectors strategy.

    Returns:
        str: HTML string showing consistency percentages for each comparison group.
    """
    # Extract consistency information
    _, processed_pairs, _, consistency_info = _extract_extreme_vector_preferences(
        choices
    )

    if processed_pairs == 0 or not consistency_info:
        return ""  # Don't show summary if no valid data

    # Get translations
    title = get_translation("survey_summary", "answers")

    # Group labels
    a_vs_b = get_translation("a_vs_b", "answers")
    a_vs_c = get_translation("a_vs_c", "answers")
    b_vs_c = get_translation("b_vs_c", "answers")
    overall = get_translation(
        "overall_consistency", "answers", fallback="Overall consistency"
    )

    # Calculate consistency percentages for each group
    consistency_percentages = []
    for matches, total, _ in consistency_info:
        if total > 0:
            percentage = int(round(100 * matches / total))
        else:
            percentage = 0
        consistency_percentages.append(percentage)

    # Calculate overall consistency
    total_matches = sum(matches for matches, total, _ in consistency_info)
    total_pairs = sum(total for _, total, _ in consistency_info)
    overall_percentage = (
        int(round(100 * total_matches / total_pairs)) if total_pairs > 0 else 0
    )

    # Create HTML for the summary table
    return f"""
    <div class="survey-stats">
        <h6 class="stats-title">{title}</h6>
        <div class="table-container">
            <table>
                <tr>
                    <td>{a_vs_b} {get_translation("consistency", "answers")}:</td>
                    <td>{consistency_percentages[0]}%</td>
                </tr>
                <tr>
                    <td>{a_vs_c} {get_translation("consistency", "answers")}:</td>
                    <td>{consistency_percentages[1]}%</td>
                </tr>
                <tr>
                    <td>{b_vs_c} {get_translation("consistency", "answers")}:</td>
                    <td>{consistency_percentages[2]}%</td>
                </tr>
                <tr class="overall-consistency">
                    <td>{overall}:</td>
                    <td>{overall_percentage}%</td>
                </tr>
            </table>
        </div>
    </div>
    """


def _generate_survey_choices_html(
    survey_id: int,
    choices: List[Dict],
    option_labels: Tuple[str, str],
    strategy_name: str = None,
) -> str:
    """Generate HTML for all choices in a survey.

    Args:
        survey_id: ID of the survey.
        choices: List of choices for the survey.
        option_labels: Tuple of labels for the two options (fallback).
        strategy_name: Name of the pair generation strategy used.

    Returns:
        str: HTML for the survey choices.
    """
    if not choices:
        return ""  # Handle case with no choices for a survey

    optimal_allocation = json.loads(choices[0]["optimal_allocation"])

    # Get survey-specific labels if available
    survey_labels = choices[0].get("strategy_labels", option_labels)

    # Translations
    survey_id_label = get_translation("survey_id", "answers")
    ideal_budget_label = get_translation("ideal_budget", "answers")

    choices_html = [
        f'<div class="survey-choices">'
        f"<h4>{survey_id_label}: {survey_id}</h4>"
        f'<div class="ideal-budget">{ideal_budget_label}: {optimal_allocation}</div>'
        f'<div class="pairs-list">'
    ]

    # Add all pairs
    for choice in choices:
        choices_html.append(_generate_choice_pair_html(choice, survey_labels))

    # Add appropriate summary
    choices_html.append("</div>")  # Close pairs-list

    # Use extreme vector consistency summary for extreme vector strategy
    if strategy_name == "extreme_vectors":
        choices_html.append(_generate_extreme_vector_consistency_summary(choices))
    else:
        choices_html.append(_generate_survey_summary_html(choices, survey_labels))

    choices_html.append("</div>")  # Close survey-choices

    return "\n".join(choices_html)


def _generate_extreme_vector_analysis_table(choices: List[Dict]) -> str:
    """
    Generate HTML table summarizing single user's extreme vector preferences.

    Args:
        choices: List of choices for a single user's survey response using the
                extreme_vectors strategy.

    Returns:
        str: HTML table string, or an empty string if not applicable or error.
    """
    logger.debug("Generating extreme vector analysis summary table for single user.")

    # Extract preference data from choices
    counts, processed_pairs, expected_pairs, consistency_info = (
        _extract_extreme_vector_preferences(choices)
    )

    # If no valid pairs were processed, return empty string
    if processed_pairs == 0:
        logger.warning("No valid extreme vector pairs found for user response.")
        return ""  # Don't show empty table

    # Log warning if fewer pairs than expected were processed
    if processed_pairs != expected_pairs:
        logger.warning(
            f"Processed {processed_pairs} pairs, expected {expected_pairs}. "
            "Table might be incomplete."
        )

    # Generate HTML table from counts and consistency info
    return _generate_extreme_analysis_html(counts, processed_pairs, consistency_info)


def _extract_extreme_vector_preferences(
    choices: List[Dict],
) -> Tuple[List[List[int]], int, int, List[Tuple[int, int, Optional[str]]]]:
    """
    Extract extreme vector preferences from user choices, and calculate consistency for weighted pairs.

    Args:
        choices: List of choice dictionaries

    Returns:
        Tuple containing:
        - counts_matrix: 3x3 grid of preference counts
        - processed_pairs: number of successfully processed pairs
        - expected_pairs: expected number of pairs
        - consistency_info: list of (matches, total, core_preference) for each group (A vs B, ...)
    """
    # Extract the basic preference data
    counts, core_preferences, weighted_answers, processed_pairs = (
        _extract_preference_counts(choices)
    )

    # Calculate consistency metrics between core preferences and weighted answers
    consistency_info = _calculate_consistency_metrics(
        core_preferences, weighted_answers
    )

    return counts, processed_pairs, EXTREME_VECTOR_EXPECTED_PAIRS, consistency_info


def _extract_preference_counts(
    choices: List[Dict],
) -> Tuple[List[List[int]], List[Optional[str]], List[List[str]], int]:
    """
    Extract core preference counts and organize data for consistency analysis.

    Args:
        choices: List of choice dictionaries

    Returns:
        Tuple containing:
        - counts_matrix: 3x3 grid of preference counts
        - core_preferences: List of core preferences (A/B/C) for each group
        - weighted_answers: List of lists containing weighted pair preferences for each group
        - processed_pairs: Number of successfully processed pairs
    """
    index_to_name = {0: "A", 1: "B", 2: "C"}
    name_to_index = {"A": 0, "B": 1, "C": 2}
    group_names = [("A", "B"), ("A", "C"), ("B", "C")]

    # Initialize counts for the 3x3 grid
    counts = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
    processed_pairs = 0

    # Store for each group: core_preference, list of weighted answers
    core_preferences = [None, None, None]  # 0: A vs B, 1: A vs C, 2: B vs C
    weighted_answers = [[], [], []]  # Each is a list of user choices for weighted pairs

    for choice in choices:
        try:
            opt1_str = choice.get("option1_strategy", "")
            opt2_str = choice.get("option2_strategy", "")
            user_choice = choice["user_choice"]  # 1 or 2

            # Determine if this is a core extreme pair or a weighted pair
            is_core = opt1_str.startswith("Extreme Vector") and opt2_str.startswith(
                "Extreme Vector"
            )
            is_weighted = (
                "Weighted Average" in opt1_str and "Weighted Average" in opt2_str
            )

            idx1 = _extract_vector_index(opt1_str)
            idx2 = _extract_vector_index(opt2_str)

            if idx1 is None or idx2 is None:
                logger.debug(f"Skipping non-extreme pair: {opt1_str} vs {opt2_str}")
                continue
            if idx1 not in index_to_name or idx2 not in index_to_name:
                logger.warning(f"Invalid extreme index found: {idx1}, {idx2}")
                continue

            # Get the corresponding names
            name1 = index_to_name[idx1]
            name2 = index_to_name[idx2]

            # Which group is this? (A vs B, A vs C, B vs C)
            group_idx = None
            for i, (g1, g2) in enumerate(group_names):
                if set([name1, name2]) == set([g1, g2]):
                    group_idx = i
                    break
            if group_idx is None:
                continue

            # Process the comparison and update counts
            comparison_type, preferred_name = _determine_comparison_and_preference(
                name1, name2, user_choice
            )
            if comparison_type is None or preferred_name is None:
                continue
            if preferred_name not in name_to_index:
                logger.error(f"Invalid preferred name: {preferred_name}")
                continue
            preferred_index = name_to_index[preferred_name]

            # Increment the corresponding cell count
            counts[comparison_type][preferred_index] += 1
            processed_pairs += 1

            # Store for consistency calculation
            if is_core:
                # Core pair: store the user's preference for this group
                core_preferences[group_idx] = preferred_name
            elif is_weighted:
                # Weighted pair: store the user's answer (A/B/C) for this group
                weighted_answers[group_idx].append(preferred_name)

        except Exception as e:
            logger.error(f"Error processing extreme choice: {e}", exc_info=True)
            continue

    return counts, core_preferences, weighted_answers, processed_pairs


def _calculate_consistency_metrics(
    core_preferences: List[Optional[str]], weighted_answers: List[List[str]]
) -> List[Tuple[int, int, Optional[str]]]:
    """
    Calculate consistency metrics between core preferences and weighted answers.

    Args:
        core_preferences: List of core preferences (A/B/C) for each group
        weighted_answers: List of lists containing weighted pair preferences for each group

    Returns:
        List of tuples (matches, total, core_preference) for each group
    """
    consistency_info = []

    for i in range(len(core_preferences)):
        core = core_preferences[i]
        weighted = weighted_answers[i]

        if core is not None and weighted:
            matches = sum(1 for w in weighted if w == core)
            total = len(weighted)
        else:
            matches = 0
            total = 0

        consistency_info.append((matches, total, core))

    return consistency_info


def _extract_vector_index(strategy_string: str) -> Optional[int]:
    """
    Extract the vector index from a strategy string.

    Args:
        strategy_string: String describing the vector strategy

    Returns:
        int: Extracted index (0-based) or None if not found
    """
    # Extract extreme vector index from strategy string
    # Handles formats:
    #   "Extreme Vector 1" (core extremes)
    #   "75% Weighted Average (Extreme 1)" (weighted averages)
    pattern = r"Extreme (?:Vector )?(\d+)|Extreme\s+(\d+)"
    match = re.search(pattern, strategy_string)

    if not match:
        return None

    # Get the first non-None captured group
    idx_str = next((g for g in match.groups() if g is not None), None)

    if idx_str is None:
        return None

    # Convert to 0-based index (A=0, B=1, C=2)
    return int(idx_str) - 1


def _determine_comparison_and_preference(
    name1: str, name2: str, user_choice: int
) -> Tuple[Optional[int], Optional[str]]:
    """
    Determine the comparison type and preferred option.

    Args:
        name1: Name of the first option (A, B, or C)
        name2: Name of the second option (A, B, or C)
        user_choice: User's choice (1 or 2)

    Returns:
        tuple: (comparison_type, preferred_name)
            - comparison_type: 0 for A vs B, 1 for A vs C, 2 for B vs C
            - preferred_name: The preferred option name (A, B, or C)
    """
    # Determine comparison type and preferred category
    comparison_type = None  # 0: AvsB, 1: AvsC, 2: BvsC
    preferred_name = None

    pair_set = {name1, name2}
    if pair_set == {"A", "B"}:
        comparison_type = 0
        preferred_name = name1 if user_choice == 1 else name2
    elif pair_set == {"A", "C"}:
        comparison_type = 1
        preferred_name = name1 if user_choice == 1 else name2
    elif pair_set == {"B", "C"}:
        comparison_type = 2
        preferred_name = name1 if user_choice == 1 else name2
    else:
        # Should not happen if indices are valid
        logger.error(f"Unexpected pair set: {pair_set}")

    return comparison_type, preferred_name


def _generate_extreme_analysis_html(
    counts: List[List[int]],
    processed_pairs: int,
    consistency_info: List[Tuple[int, int, Optional[str]]] = None,
) -> str:
    """
    Generate HTML table for the extreme vector analysis, including consistency rows.

    Args:
        counts: 3x3 grid of preference counts
        processed_pairs: Number of pairs processed
        consistency_info: List of tuples (matches, total, core_preference) for each group

    Returns:
        str: HTML table as a string
    """
    title = get_translation(
        "extreme_analysis_title",
        "answers",
    )
    note = get_translation(
        "extreme_analysis_note",
        "answers",
        processed_pairs=processed_pairs,
    )

    # Get translations for table elements
    rh_a_vs_b = get_translation("a_vs_b", "answers")
    rh_a_vs_c = get_translation("a_vs_c", "answers")
    rh_b_vs_c = get_translation("b_vs_c", "answers")

    # Column headers
    th_consistent = get_translation("consistent", "answers")
    th_inconsistent = get_translation("inconsistent", "answers")

    # Get group labels
    group_labels = [rh_a_vs_b, rh_a_vs_c, rh_b_vs_c]

    # Generate the consistency row data
    rows = []
    for i, info in enumerate(consistency_info):
        rows.append(_generate_consistency_table_row(group_labels[i], info[0], info[1]))

    # Construct the HTML table
    table_html = f"""
    <div class="extreme-analysis-container">
        <h4 class="extreme-analysis-title">{title}</h4>
        <p class="extreme-analysis-note">{note}</p>
        <div class="table-container extreme-analysis-table">
            <table>
                <thead>
                    <tr>
                        <th></th>
                        <th>{th_consistent}</th>
                        <th>{th_inconsistent}</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(rows)}
                </tbody>
            </table>
        </div>
    </div>
    """

    logger.debug("Successfully generated extreme vector analysis summary table.")
    return table_html


def _generate_consistency_table_row(group_label: str, matches: int, total: int) -> str:
    """
    Generate HTML for a single consistency table row.

    Args:
        group_label: The label for this comparison group (e.g., "A vs B")
        matches: Number of weighted answers matching the core preference
        total: Total number of weighted answers for this group

    Returns:
        str: HTML string for a table row
    """
    if total == 0:
        consistent_text = "0% (0)"
        inconsistent_text = "0% (0)"
    else:
        inconsistent = total - matches
        consistent_percent = int(round(100 * matches / total)) if total > 0 else 0
        inconsistent_percent = (
            int(round(100 * inconsistent / total)) if total > 0 else 0
        )

        consistent_text = f"{consistent_percent}% ({matches})"
        inconsistent_text = f"{inconsistent_percent}% ({inconsistent})"

    # Add vectors information based on the group label - handle both English and Hebrew
    vector_info = ""
    if "A vs B" in group_label or "א לעומת ב" in group_label:
        vector_info = "[80, 10, 10] vs [10, 80, 10]"
    elif "A vs C" in group_label or "א לעומת ג" in group_label:
        vector_info = "[80, 10, 10] vs [10, 10, 80]"
    elif "B vs C" in group_label or "ב לעומת ג" in group_label:
        vector_info = "[10, 80, 10] vs [10, 10, 80]"

    return f"""
    <tr>
        <td class="row-header">
            <div class="group-label">{group_label}</div>
            <div class="vector-info">{vector_info}</div>
        </td>
        <td>{consistent_text}</td>
        <td>{inconsistent_text}</td>
    </tr>
    <tr class="separator-row"><td colspan="3"></td></tr>
    """


def generate_detailed_user_choices(
    user_choices: List[Dict],
    option_labels: Tuple[str, str],
    strategy_name: str = None,
    show_tables_only: bool = False,
    show_detailed_breakdown_table: bool = True,
    show_overall_survey_table=True,
) -> str:
    """Generate detailed analysis of each user's choices for each survey.

    Args:
        user_choices: List of dictionaries containing user choices data.
        option_labels: Tuple of labels for the two options.
        strategy_name: Name of the pair generation strategy used.
        show_tables_only: If True, only show summary tables.
        show_detailed_breakdown_table: If True, include detailed breakdown table.
        show_overall_survey_table: If True, include overall survey table.

    Returns:
        str: HTML-formatted string with detailed user choices.
    """
    if not user_choices:
        no_data_msg = get_translation("no_answers", "answers")
        return f'<div class="no-data">{no_data_msg}</div>'

    # Group choices by user and survey
    grouped_choices = {}
    all_summaries = []

    for choice in user_choices:
        user_id = choice["user_id"]
        survey_id = choice["survey_id"]
        if user_id not in grouped_choices:
            grouped_choices[user_id] = {}
        if survey_id not in grouped_choices[user_id]:
            grouped_choices[user_id][survey_id] = []
        grouped_choices[user_id][survey_id].append(choice)

    # Collect statistics for all surveys
    for user_id, surveys in grouped_choices.items():
        for survey_id, choices in surveys.items():
            stats = calculate_choice_statistics(choices)
            # Add timestamp from the first choice (should be same for response)
            response_created_at = choices[0].get("response_created_at")
            summary = {
                "user_id": user_id,
                "survey_id": survey_id,
                "stats": stats,
                "response_created_at": response_created_at,
            }
            # Add strategy labels from the first choice (same for survey)
            if choices and "strategy_labels" in choices[0]:
                summary["strategy_labels"] = choices[0]["strategy_labels"]

            # Add strategy name from the first choice (same for survey)
            if choices and "strategy_name" in choices[0]:
                summary["strategy_name"] = choices[0]["strategy_name"]

            # Store choices for extreme_vectors strategy to calculate consistency
            if strategy_name == "extreme_vectors" or (
                "strategy_name" in summary
                and summary["strategy_name"] == "extreme_vectors"
            ):
                summary["choices"] = choices

            all_summaries.append(summary)

    # Generate content
    content = []

    if show_overall_survey_table:
        # 1. Overall statistics table
        content.append(
            generate_overall_statistics_table(
                all_summaries, option_labels, strategy_name
            )
        )

    if show_detailed_breakdown_table:
        # 2. Detailed breakdown table
        content.append(
            generate_detailed_breakdown_table(
                all_summaries, option_labels, strategy_name
            )
        )

    # Include detailed user choices only if not show_tables_only
    if not show_tables_only:
        # 3. Detailed user choices with IDs for linking
        for user_id, surveys in grouped_choices.items():
            content.append(f'<section id="user-{user_id}" class="user-choices">')
            content.append(
                f"<h3>{get_translation('user_id', 'answers')}: {user_id}</h3>"
            )

            for survey_id, choices in surveys.items():
                # Get survey-specific strategy name if available
                survey_strategy_name = strategy_name
                if choices and "strategy_name" in choices[0]:
                    survey_strategy_name = choices[0]["strategy_name"]

                # Check if this is the extreme vectors strategy
                # Generate the specific summary table for this user/survey
                if survey_strategy_name == "extreme_vectors":
                    extreme_table_html = _generate_extreme_vector_analysis_table(
                        choices
                    )
                    if extreme_table_html:
                        content.append(extreme_table_html)

                # Generate the standard survey choices HTML
                # Pass the strategy_name to _generate_survey_choices_html for specialized summary
                content.append(
                    _generate_survey_choices_html(
                        survey_id, choices, option_labels, survey_strategy_name
                    )
                )

            content.append("</section>")

    return "\n".join(content)


def generate_detailed_breakdown_table(
    summaries: List[Dict], option_labels: Tuple[str, str], strategy_name: str = None
) -> str:
    """
    Generate detailed breakdown tables grouped by survey.

    Args:
        summaries: List of dictionaries containing survey summaries.
        option_labels: Default labels (fallback if survey-specific not found).
        strategy_name: Name of the strategy used for the survey.

    Returns:
        str: HTML tables showing detailed breakdown by survey.
    """
    if not summaries:
        return ""

    # Import strategy here to avoid circular imports
    from application.services.pair_generation.base import StrategyRegistry

    # Group summaries by survey_id
    survey_groups = {}
    for summary in summaries:
        survey_id = summary["survey_id"]
        if survey_id not in survey_groups:
            survey_groups[survey_id] = []
        survey_groups[survey_id].append(summary)

    # Sort survey_groups by survey_id
    sorted_survey_ids = sorted(survey_groups.keys())

    # Generate table for each survey
    tables = []
    for survey_id in sorted_survey_ids:
        survey_summaries = survey_groups[survey_id]

        # Get strategy for this survey
        survey_strategy_name = None

        # First try to get strategy name from the first summary (preferred)
        if survey_summaries and "strategy_name" in survey_summaries[0]:
            survey_strategy_name = survey_summaries[0]["strategy_name"]
        # Fallback to provided strategy_name parameter if no specific one found
        elif strategy_name:
            survey_strategy_name = strategy_name

        # Get column definitions from strategy
        strategy_columns = {}
        if survey_strategy_name:
            try:
                strategy = StrategyRegistry.get_strategy(survey_strategy_name)
                strategy_columns = strategy.get_table_columns()
            except (ValueError, AttributeError) as e:
                logger.warning(f"Error getting strategy columns: {e}")
                # Fall back to default columns based on option labels

        # Sort summaries within the survey group by response_created_at if available
        sorted_summaries = sorted(
            survey_summaries,
            key=lambda x: x.get("response_created_at", ""),
            reverse=True,  # Most recent first
        )

        # Generate table rows
        rows = []
        for summary in sorted_summaries:
            user_id = summary["user_id"]
            display_id, is_truncated = _format_user_id(user_id)

            # Generate links
            all_responses_link = f"/surveys/users/{user_id}/responses"
            survey_response_link = f"/surveys/{survey_id}/users/{user_id}/responses"

            # Format timestamp for display
            timestamp = ""
            created_at = summary.get("response_created_at")
            if created_at:
                if isinstance(created_at, datetime):
                    timestamp = created_at.strftime("%d-%m-%Y %H:%M")
                else:
                    # Attempt to handle string/other formats if necessary
                    # This part might need adjustment based on actual data types
                    try:
                        dt_obj = pd.to_datetime(created_at)
                        timestamp = dt_obj.strftime("%d-%m-%Y %H:%M")
                    except (ValueError, TypeError):
                        timestamp = str(created_at)[:16]  # Fallback: truncate

            tooltip = (
                f'<span class="user-id-tooltip">{user_id}</span>'
                if is_truncated
                else ""
            )

            # Generate data cells based on strategy columns
            data_cells = []

            # If we have strategy-specific columns
            if strategy_columns:
                if "consistency" in strategy_columns and "choices" in summary:
                    # Handle extreme_vectors strategy with consistency column
                    choices = summary["choices"]
                    _, processed_pairs, _, consistency_info = (
                        _extract_extreme_vector_preferences(choices)
                    )

                    # Calculate overall consistency
                    total_matches = sum(
                        matches for matches, total, _ in consistency_info
                    )
                    total_pairs = sum(total for _, total, _ in consistency_info)
                    overall_consistency = (
                        int(round(100 * total_matches / total_pairs))
                        if total_pairs > 0
                        else 0
                    )

                    # Highlight row if consistency is high
                    highlight = "highlight-row" if overall_consistency >= 70 else ""

                    data_cells.append(
                        f'<td class="{highlight}">{overall_consistency}%</td>'
                    )
                elif "sum" in strategy_columns and "ratio" in strategy_columns:
                    # Handle optimization_metrics strategy with sum/ratio columns
                    sum_percent = summary["stats"]["sum_percent"]
                    ratio_percent = summary["stats"]["ratio_percent"]

                    highlight_sum = (
                        "highlight-row" if sum_percent > ratio_percent else ""
                    )
                    highlight_ratio = (
                        "highlight-row" if ratio_percent > sum_percent else ""
                    )

                    data_cells.append(
                        f'<td class="{highlight_sum}">{format(sum_percent, ".1f")}%</td>'
                    )
                    data_cells.append(
                        f'<td class="{highlight_ratio}">{format(ratio_percent, ".1f")}%</td>'
                    )
                elif "rss" in strategy_columns and "sum" in strategy_columns:
                    # Handle root_sum_squared_sum strategy with rss/sum columns
                    sum_percent = summary["stats"]["sum_percent"]
                    ratio_percent = summary["stats"]["ratio_percent"]

                    # For this strategy, ratio_percent actually represents rss_percent
                    rss_percent = 100 - sum_percent

                    highlight_rss = "highlight-row" if rss_percent > sum_percent else ""
                    highlight_sum = "highlight-row" if sum_percent > rss_percent else ""

                    data_cells.append(
                        f'<td class="{highlight_rss}">{format(rss_percent, ".1f")}%</td>'
                    )
                    data_cells.append(
                        f'<td class="{highlight_sum}">{format(sum_percent, ".1f")}%</td>'
                    )
                elif "rss" in strategy_columns and "ratio" in strategy_columns:
                    # Handle root_sum_squared_ratio strategy with rss/ratio columns
                    sum_percent = summary["stats"]["sum_percent"]
                    ratio_percent = summary["stats"]["ratio_percent"]

                    # For this strategy, sum_percent actually represents rss_percent
                    rss_percent = 100 - ratio_percent

                    highlight_rss = (
                        "highlight-row" if rss_percent > ratio_percent else ""
                    )
                    highlight_ratio = (
                        "highlight-row" if ratio_percent > rss_percent else ""
                    )

                    data_cells.append(
                        f'<td class="{highlight_rss}">{format(rss_percent, ".1f")}%</td>'
                    )
                    data_cells.append(
                        f'<td class="{highlight_ratio}">{format(ratio_percent, ".1f")}%</td>'
                    )
                elif "option1" in strategy_columns and "option2" in strategy_columns:
                    # Default case with option1/option2 columns
                    opt1_percent = summary["stats"]["option1_percent"]
                    opt2_percent = summary["stats"]["option2_percent"]

                    highlight1 = "highlight-row" if opt1_percent > opt2_percent else ""
                    highlight2 = "highlight-row" if opt2_percent > opt1_percent else ""

                    data_cells.append(
                        f'<td class="{highlight1}">{format(opt1_percent, ".1f")}%</td>'
                    )
                    data_cells.append(
                        f'<td class="{highlight2}">{format(opt2_percent, ".1f")}%</td>'
                    )
            else:
                # Fallback to old behavior if no strategy columns
                opt1_percent = summary["stats"]["option1_percent"]
                opt2_percent = summary["stats"]["option2_percent"]

                highlight1 = "highlight-row" if opt1_percent > opt2_percent else ""
                highlight2 = "highlight-row" if opt2_percent > opt1_percent else ""

                data_cells.append(
                    f'<td class="{highlight1}">{format(opt1_percent, ".1f")}%</td>'
                )
                data_cells.append(
                    f'<td class="{highlight2}">{format(opt2_percent, ".1f")}%</td>'
                )

            # Generate view response cell
            view_cell = f"""
                <td>
                    <a href="{survey_response_link}" class="survey-response-link" target="_blank">
                        {get_translation('view_response', 'answers')}
                    </a>
                </td>
            """

            # Construct the complete row
            row = f"""
            <tr>
                <td class="user-id-cell{' truncated' if is_truncated else ''}">
                    <a href="{all_responses_link}" class="user-link" target="_blank">
                        {display_id}
                    </a>
                    {tooltip}
                </td>
                <td>{timestamp}</td>
                {"".join(data_cells)}
                {view_cell}
            </tr>
            """
            rows.append(row)

        # Translations for table header
        breakdown_title = get_translation("survey_response_breakdown", "answers")
        user_id_th = get_translation("user_id", "answers")
        resp_time_th = get_translation("response_time", "answers")
        view_resp_th = get_translation("view_response", "answers")

        # Generate header cells based on strategy columns
        header_cells = []

        if strategy_columns:
            for col_id, col_def in strategy_columns.items():
                header_cells.append(f'<th>{col_def["name"]}</th>')
        else:
            # Fallback to option labels if no strategy columns
            survey_specific_labels = None
            if survey_summaries and "strategy_labels" in survey_summaries[0]:
                survey_specific_labels = survey_summaries[0]["strategy_labels"]

            labels_to_use = survey_specific_labels or option_labels
            header_cells.append(f"<th>{labels_to_use[0]}</th>")
            header_cells.append(f"<th>{labels_to_use[1]}</th>")

        # Generate the complete table
        table = f"""
        <div class="summary-table-container">
            <h2>{breakdown_title} - Survey {survey_id}</h2>
            <div class="table-container detailed-breakdown">
                <table>
                    <thead>
                        <tr>
                            <th class="sortable" data-sort="user_id">{user_id_th}</th>
                            <th class="sortable" data-sort="created_at">{resp_time_th}</th>
                            {"".join(header_cells)}
                            <th>{view_resp_th}</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(rows)}
                    </tbody>
                </table>
            </div>
        </div>
        """
        tables.append(table)

    return "\n".join(tables)


def generate_overall_statistics_table(
    summaries: List[Dict], option_labels: Tuple[str, str], strategy_name: str = None
) -> str:
    """
    Generate overall statistics summary table across all survey responses.

    Args:
        summaries: List of dictionaries containing survey summaries.
        option_labels: Labels for the two options.
        strategy_name: Name of the strategy used for the survey.

    Returns:
        str: HTML table showing overall statistics.
    """
    if not summaries:
        return ""

    # Translations
    title = get_translation("overall_statistics", "answers")
    th_metric = get_translation("metric", "answers")
    th_avg_perc = get_translation("average_percentage", "answers")
    note = get_translation("based_on_responses", "answers", x=len(summaries))

    # Different table for extreme vectors strategy
    if strategy_name == "extreme_vectors":
        # Calculate average consistency across all responses
        total_consistency = 0
        valid_summaries = 0

        for summary in summaries:
            if "choices" in summary:
                choices = summary["choices"]
                _, processed_pairs, _, consistency_info = (
                    _extract_extreme_vector_preferences(choices)
                )

                if processed_pairs > 0 and consistency_info:
                    # Calculate overall consistency for this summary
                    total_matches = sum(
                        matches for matches, total, _ in consistency_info
                    )
                    total_pairs = sum(total for _, total, _ in consistency_info)

                    if total_pairs > 0:
                        consistency = (total_matches / total_pairs) * 100
                        total_consistency += consistency
                        valid_summaries += 1

        # Calculate average consistency
        avg_consistency = (
            total_consistency / valid_summaries if valid_summaries > 0 else 0
        )

        # Get translation for consistency
        overall_consistency_label = get_translation(
            "overall_consistency", "answers", fallback="Overall consistency"
        )

        overall_table = f"""
        <div class="summary-table-container">
            <h2>{title}</h2>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>{th_metric}</th>
                            <th>{th_avg_perc}</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr class="highlight-row">
                            <td>{overall_consistency_label}</td>
                            <td>{avg_consistency:.1f}%</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <p class="summary-note">{note}</p>
        </div>
        """
    elif strategy_name in ["root_sum_squared_sum", "root_sum_squared_ratio"]:
        # Handle root sum squared strategies
        # Calculate overall averages
        total_responses = len(summaries)
        avg_sum = (
            sum(s["stats"]["sum_percent"] for s in summaries) / total_responses
            if total_responses > 0
            else 0
        )
        avg_ratio = (
            sum(s["stats"]["ratio_percent"] for s in summaries) / total_responses
            if total_responses > 0
            else 0
        )

        # For root_sum_squared strategies, the columns differ
        col1_name = get_translation("root_sum_squared", "answers")
        col2_name = (
            get_translation("sum", "answers")
            if strategy_name == "root_sum_squared_sum"
            else get_translation("ratio", "answers")
        )

        # For these strategies, we need to adjust the percentages
        # sum_percent is actually the sum% for root_sum_squared_sum and rss% for root_sum_squared_ratio
        # ratio_percent is actually rss% for root_sum_squared_sum and ratio% for root_sum_squared_ratio
        if strategy_name == "root_sum_squared_sum":
            avg_rss = 100 - avg_sum  # RSS is the complement of sum
            avg_col1 = avg_rss
            avg_col2 = avg_sum
        else:  # root_sum_squared_ratio
            avg_rss = 100 - avg_ratio  # RSS is the complement of ratio
            avg_col1 = avg_rss
            avg_col2 = avg_ratio

        highlight1 = "highlight-row" if avg_col1 > avg_col2 else ""
        highlight2 = "highlight-row" if avg_col2 > avg_col1 else ""

        overall_table = f"""
        <div class="summary-table-container">
            <h2>{title}</h2>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>{th_metric}</th>
                            <th>{th_avg_perc}</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr class="{highlight1}">
                            <td>{col1_name}</td>
                            <td>{avg_col1:.1f}%</td>
                        </tr>
                        <tr class="{highlight2}">
                            <td>{col2_name}</td>
                            <td>{avg_col2:.1f}%</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <p class="summary-note">{note}</p>
        </div>
        """
    else:
        # Original table for other strategies
        # Calculate overall averages
        total_responses = len(summaries)
        avg_opt1 = (
            sum(s["stats"]["option1_percent"] for s in summaries) / total_responses
            if total_responses > 0
            else 0
        )
        avg_opt2 = (
            sum(s["stats"]["option2_percent"] for s in summaries) / total_responses
            if total_responses > 0
            else 0
        )

        highlight1 = "highlight-row" if avg_opt1 > avg_opt2 else ""
        highlight2 = "highlight-row" if avg_opt2 > avg_opt1 else ""

        overall_table = f"""
        <div class="summary-table-container">
            <h2>{title}</h2>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>{th_metric}</th>
                            <th>{th_avg_perc}</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr class="{highlight1}">
                            <td>{option_labels[0]}</td>
                            <td>{avg_opt1:.1f}%</td>
                        </tr>
                        <tr class="{highlight2}">
                            <td>{option_labels[1]}</td>
                            <td>{avg_opt2:.1f}%</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <p class="summary-note">{note}</p>
        </div>
        """

    return overall_table


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


def _format_user_id(user_id: str, max_length: int = 12) -> tuple[str, bool]:
    """
    Format user ID for display, truncating if too long.

    Args:
        user_id: The user identifier.
        max_length: Maximum length before truncating.

    Returns:
        Tuple of (display_id, is_truncated).
    """
    if len(user_id) > max_length:
        return f"{user_id[:max_length-3]}...", True  # Ensure ellipsis fits
    return user_id, False


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


if __name__ == "__main__":
    # Basic usage example - requires actual data loading for full test
    print("Report content generator module.")
    # Example: Load data into DataFrames (summary_stats, optimization_stats, responses_df)
    # then call functions like generate_executive_summary(summary_stats, optimization_stats, responses_df)
    # and generate_detailed_user_choices(user_choices_list)
