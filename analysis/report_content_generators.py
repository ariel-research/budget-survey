import html
import json
import logging
import math
import re
from datetime import datetime
from typing import Dict, List, Tuple

import pandas as pd

from analysis.utils import is_sum_optimized
from application.translations import get_translation

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

    return f"""
            <span class="user-optimizes user-optimizes-{user_choice_type}">
                User optimizes: {user_choice_type}
            </span>
            <div class="table-container">
                <table>
                    <tr>
                        <th>Choice</th>
                        <th>Option</th>
                        <th>Sum of differences</th>
                        <th>Minimum ratio</th>
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


def _generate_survey_choices_html(
    survey_id: int, choices: List[Dict], option_labels: Tuple[str, str]
) -> str:
    """Generate HTML for all choices in a survey.

    Args:
        survey_id: ID of the survey.
        choices: List of choices for the survey.
        option_labels: Tuple of labels for the two options (fallback).

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

    # Add summary with correct labels
    choices_html.append("</div>")  # Close pairs-list
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

    # Mapping from strategy's internal index (0, 1, 2) to names (A, B, C)
    index_to_name = {0: "A", 1: "B", 2: "C"}
    name_to_index = {"A": 0, "B": 1, "C": 2}

    # Initialize counts for the 3x3 grid
    # rows: 0: A vs B, 1: A vs C, 2: B vs C
    # cols: 0: Pref A, 1: Pref B, 2: Pref C
    counts = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]

    processed_pairs = 0
    expected_pairs = 12  # 3 core + 3*3 weighted = 12

    for choice in choices:
        try:
            opt1_str = choice.get("option1_strategy", "")
            opt2_str = choice.get("option2_strategy", "")
            user_choice = choice["user_choice"]  # 1 or 2

            # Extract extreme vector index from strategy string
            # Handles formats:
            #   "Extreme Vector 1" (core extremes)
            #   "75% Weighted Average (Extreme 1)" (weighted averages)
            # Uses (?:Vector )? to optionally match "Vector" and (\d+) to capture index
            match1 = re.search(r"Extreme (?:Vector )?(\d+)|Extreme\s+(\d+)", opt1_str)
            match2 = re.search(r"Extreme (?:Vector )?(\d+)|Extreme\s+(\d+)", opt2_str)

            if not match1 or not match2:
                logger.debug(f"Skipping non-extreme pair: {opt1_str} vs {opt2_str}")
                continue

            # Filters out the None values (returns the first non-None value it finds)
            idx1_str = next(g for g in match1.groups() if g is not None)
            idx2_str = next(g for g in match2.groups() if g is not None)

            # Convert to 0-based index (A=0, B=1, C=2)
            idx1 = int(idx1_str) - 1
            idx2 = int(idx2_str) - 1

            if idx1 not in index_to_name or idx2 not in index_to_name:
                logger.warning(f"Invalid extreme index found: {idx1}, {idx2}")
                continue

            # Get the corresponding names
            name1 = index_to_name[idx1]
            name2 = index_to_name[idx2]

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
                continue

            if preferred_name not in name_to_index:
                logger.error(f"Invalid preferred name: {preferred_name}")
                continue

            preferred_index = name_to_index[preferred_name]

            # Increment the corresponding cell count
            counts[comparison_type][preferred_index] += 1
            processed_pairs += 1
            logger.debug(
                f"Processed: {name1} vs {name2}, Pref={preferred_name} "
                f"from {opt1_str} vs {opt2_str}"
            )

        except Exception as e:
            logger.error(f"Error processing extreme choice: {e}", exc_info=True)
            continue

    # Check if processed_pairs matches expected_pairs
    if processed_pairs == 0:
        logger.warning("No valid extreme vector pairs found for user response.")
        return ""  # Don't show empty table
    elif processed_pairs != expected_pairs:
        logger.warning(
            f"Processed {processed_pairs} pairs, expected {expected_pairs}. "
            "Table might be incomplete."
        )

    # Generate HTML
    title = get_translation(
        "extreme_analysis_title",
        "answers",
        default="Extreme Vector Preferences Summary (Single User)",
    )
    note = get_translation(
        "extreme_analysis_note",
        "answers",
        processed_pairs=processed_pairs,
        default="Note: Table summarizes user choices ({processed_pairs} pairs).",
    )
    th_empty = get_translation("th_empty", "answers", default="")
    th_pref_a = get_translation("prefer_a", "answers", default="Prefer A")
    th_pref_b = get_translation("prefer_b", "answers", default="Prefer B")
    th_pref_c = get_translation("prefer_c", "answers", default="Prefer C")
    rh_a_vs_b = get_translation("a_vs_b", "answers", default="A vs B")
    rh_a_vs_c = get_translation("a_vs_c", "answers", default="A vs C")
    rh_b_vs_c = get_translation("b_vs_c", "answers", default="B vs C")

    table_html = f"""
    <div class="extreme-analysis-container">
        <h4 class="extreme-analysis-title">{title}</h4>
        <p class="extreme-analysis-note">{note}</p>
        <div class="table-container extreme-analysis-table">
            <table>
                <thead>
                    <tr>
                        <th>{th_empty}</th>
                        <th>{th_pref_a}</th>
                        <th>{th_pref_b}</th>
                        <th>{th_pref_c}</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td class="row-header">{rh_a_vs_b}</td>
                        <td>{counts[0][0]}</td>
                        <td>{counts[0][1]}</td>
                        <td>{counts[0][2]}</td>
                    </tr>
                    <tr class="separator-row"><td colspan="4"></td></tr>
                    <tr>
                        <td class="row-header">{rh_a_vs_c}</td>
                        <td>{counts[1][0]}</td>
                        <td>{counts[1][1]}</td>
                        <td>{counts[1][2]}</td>
                    </tr>
                    <tr class="separator-row"><td colspan="4"></td></tr>
                    <tr>
                        <td class="row-header">{rh_b_vs_c}</td>
                        <td>{counts[2][0]}</td>
                        <td>{counts[2][1]}</td>
                        <td>{counts[2][2]}</td>
                    </tr>
                    <tr class="separator-row"><td colspan="4"></td></tr>
                </tbody>
            </table>
        </div>
    </div>
    """

    logger.debug("Successfully generated extreme vector analysis summary table.")
    return table_html


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
        return '<div class="no-data">No detailed user choice data available.</div>'

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
            all_summaries.append(summary)

    # Generate content
    content = []

    if show_overall_survey_table:
        # 1. Overall statistics table
        content.append(generate_overall_statistics_table(all_summaries, option_labels))

    if show_detailed_breakdown_table:
        # 2. Detailed breakdown table
        content.append(generate_detailed_breakdown_table(all_summaries, option_labels))

    # Include detailed user choices only if not show_tables_only
    if not show_tables_only:
        # 3. Detailed user choices with IDs for linking
        for user_id, surveys in grouped_choices.items():
            content.append(f'<section id="user-{user_id}" class="user-choices">')
            content.append(
                f"<h3>{get_translation('user_id', 'answers')}: {user_id}</h3>"
            )

            for survey_id, choices in surveys.items():
                # Check if this is the extreme vectors strategy
                # Generate the specific summary table for this user/survey
                if strategy_name == "extreme_vectors":
                    extreme_table_html = _generate_extreme_vector_analysis_table(
                        choices
                    )
                    if extreme_table_html:
                        content.append(extreme_table_html)

                # Generate the standard survey choices HTML
                # (ideal budget, pairs list, summary)
                content.append(
                    _generate_survey_choices_html(survey_id, choices, option_labels)
                )

            content.append("</section>")

    return "\n".join(content)


def generate_detailed_breakdown_table(
    summaries: List[Dict], option_labels: Tuple[str, str]
) -> str:
    """
    Generate detailed breakdown tables grouped by survey.

    Args:
        summaries: List of dictionaries containing survey summaries.
        option_labels: Default labels (fallback if survey-specific not found).

    Returns:
        str: HTML tables showing detailed breakdown by survey.
    """
    if not summaries:
        return ""

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

        # Sort summaries within the survey group by user_id or timestamp if needed
        # Example: sorted_summaries = sorted(survey_summaries, key=lambda x: x['user_id'])
        sorted_summaries = survey_summaries  # Using pre-sorted for now

        # Generate table rows
        rows = []
        for summary in sorted_summaries:
            opt1_percent = summary["stats"]["option1_percent"]
            opt2_percent = summary["stats"]["option2_percent"]
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

            highlight1 = "highlight-row" if opt1_percent > opt2_percent else ""
            highlight2 = "highlight-row" if opt2_percent > opt1_percent else ""
            tooltip = (
                f'<span class="user-id-tooltip">{user_id}</span>'
                if is_truncated
                else ""
            )

            row = f"""
            <tr>
                <td class="user-id-cell{' truncated' if is_truncated else ''}">
                    <a href="{all_responses_link}" class="user-link" target="_blank">
                        {display_id}
                    </a>
                    {tooltip}
                </td>
                <td>{timestamp}</td>
                <td class="{highlight1}">{format(opt1_percent, '.1f')}%</td>
                <td class="{highlight2}">{format(opt2_percent, '.1f')}%</td>
                <td>
                    <a href="{survey_response_link}" class="survey-response-link" target="_blank">
                        {get_translation('view_response', 'answers')}
                    </a>
                </td>
            </tr>
            """
            rows.append(row)

        # Translations for table header
        breakdown_title = get_translation("survey_response_breakdown", "answers")
        user_id_th = get_translation("user_id", "answers", default="User ID")
        resp_time_th = get_translation(
            "response_time", "answers", default="Response Time"
        )
        view_resp_th = get_translation(
            "view_response", "answers", default="View Response"
        )

        # Generate table for this survey
        table = f"""
        <div class="summary-table-container">
            <h2>{breakdown_title} - Survey {survey_id}</h2>
            <div class="table-container detailed-breakdown">
                <table>
                    <thead>
                        <tr>
                            <th class="sortable" data-sort="user_id">{user_id_th}</th>
                            <th class="sortable" data-sort="created_at">{resp_time_th}</th>
                            <th>{option_labels[0]}</th>
                            <th>{option_labels[1]}</th>
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
    summaries: List[Dict], option_labels: Tuple[str, str]
) -> str:
    """
    Generate overall statistics summary table across all survey responses.

    Args:
        summaries: List of dictionaries containing survey summaries.
        option_labels: Labels for the two options.

    Returns:
        str: HTML table showing overall statistics.
    """
    if not summaries:
        return ""

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

    # Translations
    title = get_translation("overall_statistics", "answers")
    th_metric = get_translation("metric", "answers")
    th_avg_perc = get_translation("average_percentage", "answers")
    note = get_translation("based_on_responses", "answers", x=total_responses)
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
