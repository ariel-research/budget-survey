import html
import json
import logging
import math
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd

from analysis.transitivity_analyzer import TransitivityAnalyzer
from analysis.utils import is_sum_optimized
from application.translations import get_translation
from database.queries import get_subjects

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
    tuple: (consistency_%, qualified_users, total_responses, min_surveys,
    total_surveys)
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
    unique_users = optimization_stats["user_id"].nunique()  # Actual unique
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
                        <li>
                            Participants who took multiple surveys: {multi_survey_users}
                        </li>
                    </ul>
                </li>
            </ul>
        </div>

        <div class="statistic-group">
            <h3>Response Details</h3>
            <ul>
                <li>Total answers collected: {total_answers}</li>
                <li>
                    Average answers per survey response:
                    {avg_answers_per_user:.1f}
                </li>
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
        tuple(optimal_allocation),
        tuple(option_1),
        tuple(option_2),
        user_choice,
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

    # Check if this is a biennial budget strategy (uses 6-element vectors)
    # These strategies have their own analysis metrics and can't use
    # sum/ratio optimization
    # Two ways to detect: explicit strategy_name or vector length check
    is_biennial = False

    if choices and "strategy_name" in choices[0]:
        strategy_name = choices[0]["strategy_name"]
        if strategy_name == "triangle_inequality_test":
            is_biennial = True
    elif choices:
        # Fallback: Check if vectors are 6 elements (biennial) vs 3 (single year)
        try:
            first_choice = choices[0]
            option_1 = json.loads(first_choice.get("option_1", "[]"))
            if len(option_1) == 6:
                # This is a biennial budget (2 years × 3 subjects = 6 elements)
                is_biennial = True
        except (json.JSONDecodeError, TypeError, KeyError):
            pass

    if is_biennial:
        # Only calculate option selection percentages
        # Strategy-specific metrics are calculated by
        # _calculate_triangle_inequality_metrics()
        option1_count = sum(1 for choice in choices if choice.get("user_choice") == 1)
        opt1_p = (option1_count / total_choices) * 100
        opt2_p = ((total_choices - option1_count) / total_choices) * 100

        return {
            # Not applicable for biennial strategies
            "sum_percent": None,
            "ratio_percent": None,
            "option1_percent": opt1_p,
            "option2_percent": opt2_p,
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
    from application.services.pair_generation import (
        OptimizationMetricsStrategy,
    )
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
    opt_type_trans = get_translation(user_choice_type, "answers")

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


def _format_biennial_option(option: list) -> str:
    """
    Format a biennial budget option (6 elements) into Year 1 and Year 2 display.

    Args:
        option: List of 6 elements [year1_val1, year1_val2, year1_val3, year2_val1, year2_val2, year2_val3]

    Returns:
        str: Formatted HTML with Year 1 and Year 2 on separate lines
    """
    if len(option) != 6:
        # Not a biennial budget, return as-is
        return str(option)

    # Split into Year 1 (first 3) and Year 2 (last 3)
    year1 = option[:3]
    year2 = option[3:]

    # Get translations
    year1_label = get_translation("year_1", "survey")
    year2_label = get_translation("year_2", "survey")

    return f"""<div class="biennial-budget-display">
        <div class="year-budget"><strong>{year1_label}:</strong> {year1}</div>
        <div class="year-budget"><strong>{year2_label}:</strong> {year2}</div>
    </div>"""


def _generate_choice_pair_html(
    choice: Dict, option_labels: Tuple[str, str], subjects: List[str] = None
) -> str:
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

    # For cyclic shift strategy, calculate actual differences
    if "Cyclic Pattern" in str(strategy_1) or "Cyclic Pattern" in str(strategy_2):
        # Get the user's optimal allocation for this choice
        optimal_allocation = json.loads(choice["optimal_allocation"])

        changes_label = get_translation("changes", "answers")

        def calculate_actual_differences(ideal_vector, final_vector):
            """Calculate actual differences between ideal and final vectors."""
            return [final - ideal for final, ideal in zip(final_vector, ideal_vector)]

        def format_differences(diffs):
            """Format difference vector for display."""
            formatted = []
            for d in diffs:
                if d > 0:
                    formatted.append(f"+{d}")
                elif d == 0:
                    formatted.append("0")
                else:
                    formatted.append(str(d))
            return "[" + ", ".join(formatted) + "]"

        # Calculate actual differences for both options
        actual_diff_1 = calculate_actual_differences(optimal_allocation, option_1)
        actual_diff_2 = calculate_actual_differences(optimal_allocation, option_2)

        diff_1_formatted = format_differences(actual_diff_1)
        diff_2_formatted = format_differences(actual_diff_2)

        strategy_1 = (
            f"{strategy_1}<br><small>{changes_label}: " f"{diff_1_formatted}</small>"
        )
        strategy_2 = (
            f"{strategy_2}<br><small>{changes_label}: " f"{diff_2_formatted}</small>"
        )

    # For linear symmetry strategy, use stored differences
    elif "Linear Pattern" in str(strategy_1) or "Linear Pattern" in str(strategy_2):
        changes_label = get_translation("changes", "answers")

        def format_differences(diffs):
            """Format difference vector for display."""
            formatted = []
            for d in diffs:
                if d > 0:
                    formatted.append(f"+{d}")
                elif d == 0:
                    formatted.append("0")
                else:
                    formatted.append(str(d))
            return "[" + ", ".join(formatted) + "]"

        # Get stored differences for both options
        diff_1 = choice.get("option1_differences", [])
        diff_2 = choice.get("option2_differences", [])

        if diff_1:
            diff_1_formatted = format_differences(diff_1)
            strategy_1 = (
                f"{strategy_1}<br><small>{changes_label}: "
                f"{diff_1_formatted}</small>"
            )

        if diff_2:
            diff_2_formatted = format_differences(diff_2)
            strategy_2 = (
                f"{strategy_2}<br><small>{changes_label}: "
                f"{diff_2_formatted}</small>"
            )

    # For asymmetric_loss_distribution strategy, create new UI with
    # target and action labels. Make detection language-agnostic by
    # preferring the explicit strategy_name on the choice when available.
    elif (
        choice.get("strategy_name") == "asymmetric_loss_distribution"
        or "Concentrated Changes" in str(strategy_1)
        or "Distributed Changes" in str(strategy_1)
        or "שינויים מרוכזים" in str(strategy_1)
        or "שינויים מבוזרים" in str(strategy_1)
        or get_translation("concentrated_changes", "answers") in str(strategy_1)
        or get_translation("distributed_changes", "answers") in str(strategy_1)
        or get_translation("concentrated_changes", "answers") in str(strategy_2)
        or get_translation("distributed_changes", "answers") in str(strategy_2)
    ):
        try:
            # Helper function to format vector with bold target element
            def format_vector_with_bold(vector, target_idx):
                parts = [
                    f"<b>{val}</b>" if i == target_idx else str(val)
                    for i, val in enumerate(vector)
                ]
                return f"[{', '.join(parts)}]"

            # Get target category from choice dictionary
            target_category = choice.get("target_category")

            # If target_category is missing, find it from the vectors
            if target_category is None:
                try:
                    optimal_allocation = json.loads(choice["optimal_allocation"])

                    # Calculate differences for both options to find target
                    diff_1 = [
                        abs(option_1[i] - optimal_allocation[i])
                        for i in range(len(option_1))
                    ]
                    diff_2 = [
                        abs(option_2[i] - optimal_allocation[i])
                        for i in range(len(option_2))
                    ]

                    # Find the target category (the one with maximum change)
                    max_diff_1 = max(diff_1)
                    target_category = diff_1.index(max_diff_1)

                except (KeyError, ValueError, json.JSONDecodeError):
                    target_category = None

            # If we have target_category, format and label regardless of subjects
            if target_category is not None:
                try:
                    optimal_allocation = json.loads(choice["optimal_allocation"])

                    # Calculate actual changes for the target category
                    target_value_ideal = optimal_allocation[target_category]
                    change_1 = option_1[target_category] - target_value_ideal
                    change_2 = option_2[target_category] - target_value_ideal

                    # Generate labels based on actual changes
                    if change_1 < 0:
                        strategy_1 = get_translation(
                            "decrease_target_by",
                            "answers",
                            amount=abs(change_1),
                        )
                    else:
                        strategy_1 = get_translation(
                            "increase_target_by",
                            "answers",
                            amount=change_1,
                        )

                    if change_2 < 0:
                        strategy_2 = get_translation(
                            "decrease_target_by",
                            "answers",
                            amount=abs(change_2),
                        )
                    else:
                        strategy_2 = get_translation(
                            "increase_target_by",
                            "answers",
                            amount=change_2,
                        )

                    # Get target category name (fallback without subjects)
                    if subjects and target_category < len(subjects):
                        target_name = subjects[target_category]
                    else:
                        target_name = f"Category {target_category + 1}"

                    # Update the option display to use bold formatting
                    option_1_formatted = format_vector_with_bold(
                        option_1, target_category
                    )
                    option_2_formatted = format_vector_with_bold(
                        option_2, target_category
                    )

                    # Store formatted options for later use
                    choice["_formatted_option_1"] = option_1_formatted
                    choice["_formatted_option_2"] = option_2_formatted
                    choice["_target_name"] = target_name

                except (KeyError, ValueError, json.JSONDecodeError):
                    # Fallback to original strategy names if calculation fails
                    pass

            else:
                # Fallback to original magnitude display
                if "(" not in str(strategy_1) and ")" not in str(strategy_1):
                    try:
                        optimal_allocation = json.loads(choice["optimal_allocation"])
                        diff_1 = [
                            abs(option_1[i] - optimal_allocation[i])
                            for i in range(len(option_1))
                        ]
                        diff_2 = [
                            abs(option_2[i] - optimal_allocation[i])
                            for i in range(len(option_2))
                        ]
                        magnitude_1 = max(diff_1)
                        magnitude_2 = max(diff_2)
                        strategy_1 = f"{strategy_1} ({magnitude_1})"
                        strategy_2 = f"{strategy_2} ({magnitude_2})"
                    except (KeyError, ValueError, json.JSONDecodeError):
                        pass

        except (KeyError, ValueError, json.JSONDecodeError) as e:
            logger.warning(
                "Failed to process asymmetric_loss_distribution strategy: " f"{e}"
            )

    # Generate raw choice info HTML
    trans_orig = get_translation("original_choice", "answers")
    trans_opt = get_translation("option_number", "answers", number=raw_choice)
    trans_na = get_translation("not_available", "answers")
    raw_choice_html = (
        f'<span class="raw-choice-label">{trans_orig}: </span>'
        f'<span class="raw-choice-value">{trans_opt}</span>'
        if raw_choice is not None
        else (
            f'<span class="raw-choice-unavailable">{trans_orig}: ' f"{trans_na}</span>"
        )
    )

    # Table headers
    th_choice = get_translation("table_choice", "answers")
    th_option = get_translation("table_option", "answers")
    th_type = get_translation("table_type", "answers")
    pair_num_label = get_translation("pair_number", "answers")

    check_1 = "✓" if user_choice == 1 else ""
    check_2 = "✓" if user_choice == 2 else ""

    # Check if we have formatted options and target name
    option_1_display = choice.get("_formatted_option_1", str(option_1))
    option_2_display = choice.get("_formatted_option_2", str(option_2))
    target_name = choice.get("_target_name")

    # For triangle inequality test, format biennial budgets with Year 1/Year 2 split
    strategy_name = choice.get("strategy_name")
    if strategy_name == "triangle_inequality_test":
        # Only format if not already formatted
        if not choice.get("_formatted_option_1"):
            option_1_display = _format_biennial_option(option_1)
        if not choice.get("_formatted_option_2"):
            option_2_display = _format_biennial_option(option_2)

    # Build the pair header with target info if available
    header_content = f"{pair_num_label} #{choice['pair_number']}"
    if target_name:
        target_label = get_translation("target_is", "answers", target_name=target_name)
        header_content += f" ({target_label})"

    # Generate metadata section for l1_vs_leontief_rank_comparison strategy
    metadata_html = ""
    if (
        choice.get("strategy_name") == "l1_vs_leontief_rank_comparison"
        and choice.get("generation_metadata")
        and isinstance(choice.get("generation_metadata"), dict)
        and "score" in choice.get("generation_metadata", {})
    ):
        score = choice["generation_metadata"]["score"]
        metadata_html = f"""
        <div class="pair-metadata">
            <span class="pair-metadata-label">Generation Score:</span>
            <span class="pair-metadata-value">{score:.2f}</span>
        </div>
        """

    return f"""
    <div class="choice-pair">
        <div class="pair-header">
            <h5>{header_content}</h5>
            <div class="raw-choice-info">
                {raw_choice_html}
            </div>
        </div>
        {metadata_html}
        <div class="table-container">
            <table>
                <tr>
                    <th>{th_choice}</th>
                    <th>{th_option}</th>
                    <th>{th_type}</th>
                </tr>
                <tr>
                    <td class="selection-column">{check_1}</td>
                    <td class="option-column">{option_1_display}</td>
                    <td>{strategy_1}</td>
                </tr>
                <tr>
                    <td class="selection-column">{check_2}</td>
                    <td class="option-column">{option_2_display}</td>
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


def _generate_extreme_vector_consistency_summary(
    choices: List[Dict],
) -> str:
    """
    Generate a simple consistency summary for extreme vector surveys.

    Args:
        choices: List of choices for a single user's survey response using the
                peak_linearity_test strategy.

    Returns:
        str: HTML string showing consistency percentages for each group.
    """
    # Extract consistency information
    (
        _,
        processed_pairs,
        _,
        consistency_info,
        _,
    ) = _extract_extreme_vector_preferences(choices)

    if processed_pairs == 0 or not consistency_info:
        return ""  # Don't show summary if no valid data

    # Get translations
    title = get_translation("survey_summary", "answers")

    # Group labels
    a_vs_b = get_translation("a_vs_b", "answers")
    a_vs_c = get_translation("a_vs_c", "answers")
    b_vs_c = get_translation("b_vs_c", "answers")
    overall = get_translation("overall_consistency", "answers")

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
                    <td>
                        {a_vs_b} {get_translation("consistency", "answers")}:
                    </td>
                    <td>{consistency_percentages[0]}%</td>
                </tr>
                <tr>
                    <td>
                        {a_vs_c} {get_translation("consistency", "answers")}:
                    </td>
                    <td>{consistency_percentages[1]}%</td>
                </tr>
                <tr>
                    <td>
                        {b_vs_c} {get_translation("consistency", "answers")}:
                    </td>
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
    """Generate HTML for choices made in a single survey.
    Args:
        survey_id: ID of the survey
        choices: List of choices for a single survey
        option_labels: Labels for the two options
        strategy_name: Name of the strategy used for the survey
    Returns:
        str: HTML for the survey choices
    """
    if not choices:
        return ""

    # Get survey-specific option labels if available
    survey_labels = choices[0].get("strategy_labels", option_labels)

    # Get survey subjects for asymmetric_loss_distribution strategy
    subjects = None
    if strategy_name == "asymmetric_loss_distribution":
        try:
            subjects = get_subjects(survey_id)
        except Exception as e:
            logger.warning(f"Failed to get subjects for survey {survey_id}: {e}")

    # Survey header and ideal budget
    first_choice = choices[0]
    optimal_allocation = json.loads(first_choice["optimal_allocation"])
    survey_id_label = get_translation("survey_id", "answers")
    ideal_budget_label = get_translation("ideal_budget", "answers")

    html_parts = [
        '<div class="survey-choices">',
        f"<h4>{survey_id_label}: {survey_id}</h4>",
        f'<div class="ideal-budget">{ideal_budget_label}: '
        f"{optimal_allocation}</div>",
    ]

    # Special handling for peak_linearity_test strategy
    if strategy_name == "peak_linearity_test":
        consistency_summary = _generate_extreme_vector_consistency_summary(choices)
        if consistency_summary:
            html_parts.append(consistency_summary)

    # Special handling for component_symmetry_test strategy
    elif strategy_name == "component_symmetry_test":
        consistency_table = _generate_cyclic_shift_consistency_table(choices)
        if consistency_table:
            html_parts.append(consistency_table)

    # Special handling for sign_symmetry_test strategy
    elif strategy_name == "sign_symmetry_test":
        consistency_table = _generate_linear_symmetry_consistency_table(choices)
        if consistency_table:
            html_parts.append(consistency_table)

    # Special handling for triangle_inequality_test strategy
    elif strategy_name == "triangle_inequality_test":
        triangle_table = _generate_triangle_inequality_table(choices)
        if triangle_table:
            html_parts.append(triangle_table)

    # Special handling for asymmetric_loss_distribution strategy (single-user matrix)
    elif strategy_name == "asymmetric_loss_distribution":
        matrix_html = _generate_single_user_asymmetric_matrix_table(choices, survey_id)
        if matrix_html:
            html_parts.append(matrix_html)

    # Special handling for biennial_budget_preference strategy - three separate tables
    elif strategy_name == "biennial_budget_preference":
        temporal_sub_tables_html = _generate_temporal_sub_survey_tables(choices)
        if temporal_sub_tables_html:
            html_parts.append(temporal_sub_tables_html)

    # Standard summary for other strategies
    else:
        survey_summary = _generate_survey_summary_html(choices, survey_labels)
        html_parts.append(survey_summary)

    # Generate individual choice pairs
    pairs_list = []
    for i, choice in enumerate(choices):
        pair_html = _generate_choice_pair_html(choice, survey_labels, subjects)
        pairs_list.append(f'<div class="choice-pair">{pair_html}</div>')

    if pairs_list:
        pairs_list_label = get_translation("pairs_list", "answers")

        # Add group/rotation explanation once for triangle inequality test
        group_rotation_info = ""
        if strategy_name == "triangle_inequality_test":
            line1 = get_translation("group_rotation_explanation_line1", "survey")
            line2 = get_translation("group_rotation_explanation_line2", "survey")
            group_rotation_info = f"""<div class="group-rotation-info">
                <div class="info-icon">ℹ️</div>
                <div class="info-content">
                    <div class="info-line">{line1}</div>
                    <div class="info-line">{line2}</div>
                </div>
            </div>"""

        html_parts.extend(
            [
                f"<h5>{pairs_list_label}</h5>",
                group_rotation_info,
                '<div class="pairs-list">',
                "".join(pairs_list),
                "</div>",
            ]
        )

    html_parts.append("</div>")
    return "".join(html_parts)


def _generate_extreme_vector_analysis_table(choices: List[Dict]) -> str:
    """
    Generate HTML table summarizing single user's extreme vector preferences.

    Args:
        choices: List of choices for a single user's survey response using the
                peak_linearity_test strategy.

    Returns:
        str: HTML table string, or an empty string if not applicable or error.
    """
    logger.debug("Generating extreme vector analysis summary table for single user.")

    # Extract preference data from choices
    (
        counts,
        processed_pairs,
        expected_pairs,
        consistency_info,
        percentile_data,
    ) = _extract_extreme_vector_preferences(choices)

    logger.debug(f"counts: {counts}")
    logger.debug(f"processed_pairs: {processed_pairs}")
    logger.debug(f"expected_pairs: {expected_pairs}")
    logger.debug(f"consistency_info: {consistency_info}")
    logger.debug(f"percentile_data: {percentile_data}")

    # If no valid pairs were processed, return empty string
    if processed_pairs == 0:
        logger.info("No valid extreme vector pairs found for user response.")
        return ""  # Don't show empty table

    # Log warning if fewer pairs than expected were processed
    if processed_pairs != expected_pairs:
        logger.warning(
            f"Processed {processed_pairs} pairs, expected {expected_pairs}. "
            "Table might be incomplete."
        )

    # Generate both tables
    main_table_html = _generate_extreme_analysis_html(
        counts, processed_pairs, consistency_info
    )
    percentile_table_html = _generate_percentile_breakdown_table(percentile_data)

    # Generate transitivity analysis table
    transitivity_table = generate_transitivity_analysis_table(choices)

    # Return all tables
    return main_table_html + percentile_table_html + transitivity_table


def _generate_single_user_asymmetric_matrix_data(
    choices: List[Dict], survey_id: int
) -> Dict:
    """
    Process single user's asymmetric loss distribution choices into matrix format.

    Returns a dictionary with matrix data, totals, type distribution, subjects,
    ideal budget and magnitude levels present for this user's choices.
    """
    try:
        # Subjects for target categories with fallback labels
        subjects = []
        try:
            subjects = get_subjects(survey_id) or []
        except Exception as e:
            logger.warning(f"get_subjects failed for survey {survey_id}: {e}")
        if not subjects:
            subjects = [
                f"Category {i}" for i in range(3)
            ]  # Fallback if DB subjects missing

        # Ideal budget
        ideal_budget: List[int] = []
        if choices and choices[0].get("optimal_allocation"):
            try:
                ideal_budget = list(json.loads(choices[0]["optimal_allocation"]))
            except Exception:
                ideal_budget = []

        # Helpers to robustly extract fields
        def extract_target_category(choice: Dict) -> Optional[int]:
            tc = choice.get("target_category")
            if tc is not None:
                return int(tc)
            pair_num = choice.get("pair_number")
            if isinstance(pair_num, int) and pair_num > 0:
                return min(2, (pair_num - 1) // 4)
            return None

        magnitude_levels_set = set()
        type_a_count = 0
        type_b_count = 0

        # matrix[target][magnitude] = { 'decrease_chosen': bool, 'has_data': bool }
        matrix: Dict[int, Dict[int, Dict[str, bool]]] = {0: {}, 1: {}, 2: {}}

        # Regex to capture magnitude and type from strategy strings like "(..., Type A)"
        type_pattern = re.compile(r"Type\s*([AB])", re.IGNORECASE)
        mag_in_paren_pattern = re.compile(r"\((\d+)\s*,\s*Type\s*[AB]\)")

        for choice in choices:
            # Determine target category
            target_category = extract_target_category(choice)
            if target_category is None or target_category not in (0, 1, 2):
                logger.warning(
                    f"Skipping choice without valid target_category: {choice.get('id', '')}"
                )
                continue

            # Determine magnitude (prefer explicit field or parse from strategy)
            magnitude: Optional[int] = None
            if "magnitude" in choice and isinstance(
                choice.get("magnitude"), (int, float)
            ):
                magnitude = int(choice["magnitude"])
            else:
                s1 = str(choice.get("option1_strategy", ""))
                s2 = str(choice.get("option2_strategy", ""))
                m = mag_in_paren_pattern.search(s1) or mag_in_paren_pattern.search(s2)
                if m:
                    try:
                        magnitude = int(m.group(1))
                    except Exception:
                        magnitude = None

            # Fallback: infer target, type and magnitude from vectors and ideal budget
            # Initialize pair_type early so it exists for later checks
            pair_type = str(choice.get("pair_type", "")).upper()
            # Load ideal allocation robustly (already-parsed list or JSON string)
            opt_alloc = []
            raw_opt = choice.get("optimal_allocation")
            if ideal_budget:
                opt_alloc = list(ideal_budget)
            elif isinstance(raw_opt, (list, tuple)):
                opt_alloc = list(raw_opt)
            elif isinstance(raw_opt, str):
                try:
                    opt_alloc = list(json.loads(raw_opt))
                except Exception:
                    opt_alloc = []

            # Load vectors robustly (already list or JSON string)
            vec1 = None
            vec2 = None
            raw_v1 = choice.get("option_1")
            raw_v2 = choice.get("option_2")
            if isinstance(raw_v1, (list, tuple)):
                vec1 = list(raw_v1)
            elif isinstance(raw_v1, str):
                try:
                    vec1 = list(json.loads(raw_v1))
                except Exception:
                    vec1 = None
            if isinstance(raw_v2, (list, tuple)):
                vec2 = list(raw_v2)
            elif isinstance(raw_v2, str):
                try:
                    vec2 = list(json.loads(raw_v2))
                except Exception:
                    vec2 = None

            if (
                (target_category is None or magnitude is None)
                and opt_alloc
                and vec1
                and vec2
            ):
                # Compute deltas relative to ideal
                d1 = [v - o for v, o in zip(vec1, opt_alloc)]
                d2 = [v - o for v, o in zip(vec2, opt_alloc)]

                # Infer target index by selecting the largest total movement.
                # This is robust for both Type A and Type B pairs and avoids
                # mis-detecting index 0 when equal-opposite patterns are not
                # strictly present in stored data.
                inferred_idx = max(
                    range(len(opt_alloc)), key=lambda i: abs(d1[i]) + abs(d2[i])
                )

                if target_category is None:
                    target_category = inferred_idx

                # Infer magnitude and type
                delta_target_abs = max(abs(d1[inferred_idx]), abs(d2[inferred_idx]))
                other_idxs = [i for i in range(len(opt_alloc)) if i != inferred_idx]
                a1 = [abs(d1[i]) for i in other_idxs]
                a2 = [abs(d2[i]) for i in other_idxs]

                is_type_a_pattern = (
                    a1[0] == a1[1]
                    and a2[0] == a2[1]
                    and a1[0] == a2[0]
                    and (2 * a1[0]) == delta_target_abs
                )

                if magnitude is None:
                    magnitude = (
                        int(delta_target_abs // 2)
                        if is_type_a_pattern
                        else int(delta_target_abs)
                    )

                # Record inferred pair_type, counting will be handled uniformly later
                if pair_type not in ("A", "B"):
                    pair_type = "A" if is_type_a_pattern else "B"

            if magnitude is None:
                logger.warning(
                    f"Skipping choice without determinable magnitude: {choice.get('id', '')}"
                )
                continue

            magnitude_levels_set.add(magnitude)

            # Determine Type A/B (finalize and count once)
            pair_type = (
                str(choice.get("pair_type", "")).upper()
                if pair_type not in ("A", "B")
                else pair_type
            )
            if pair_type not in ("A", "B"):
                s1 = str(choice.get("option1_strategy", ""))
                s2 = str(choice.get("option2_strategy", ""))
                mt = type_pattern.search(s1) or type_pattern.search(s2)
                if mt:
                    pair_type = mt.group(1).upper()
            if pair_type == "A":
                type_a_count += 1
            elif pair_type == "B":
                type_b_count += 1

            # Determine user choice as decrease vs increase
            user_choice = choice.get("user_choice")
            if user_choice not in (1, 2):
                logger.warning(
                    f"Skipping choice with invalid user_choice: {choice.get('id', '')}"
                )
                continue

            # Prefer vector-based detection of decrease
            chose_decrease = None
            if opt_alloc and vec1 and vec2 and target_category is not None:
                d1 = [v - o for v, o in zip(vec1, opt_alloc)]
                d2 = [v - o for v, o in zip(vec2, opt_alloc)]
                chose_decrease = (user_choice == 1 and d1[target_category] < 0) or (
                    user_choice == 2 and d2[target_category] < 0
                )
            else:
                option1_strategy = str(choice.get("option1_strategy", ""))
                option2_strategy = str(choice.get("option2_strategy", ""))
                is_opt1_decrease = "Concentrated" in option1_strategy or (
                    get_translation("concentrated_changes", "answers")
                    in option1_strategy
                )
                is_opt2_decrease = "Concentrated" in option2_strategy or (
                    get_translation("concentrated_changes", "answers")
                    in option2_strategy
                )
                chose_decrease = (user_choice == 1 and is_opt1_decrease) or (
                    user_choice == 2 and is_opt2_decrease
                )

            matrix[target_category][magnitude] = {
                "decrease_chosen": bool(chose_decrease),
                "has_data": True,
            }

        # Build totals
        magnitude_levels = sorted(magnitude_levels_set)

        row_totals: Dict[int, Dict[str, float]] = {}
        col_totals: Dict[int, Dict[str, float]] = {
            m: {"decrease_count": 0, "total_count": 0, "percentage": 0.0}
            for m in magnitude_levels
        }
        grand_decrease = 0
        grand_total = 0

        for target in (0, 1, 2):
            decrease_count = 0
            total_count = 0
            for m in magnitude_levels:
                cell = matrix[target].get(m)
                if cell and cell.get("has_data"):
                    total_count += 1
                    if cell.get("decrease_chosen"):
                        decrease_count += 1
                        col_totals[m]["decrease_count"] += 1
                    col_totals[m]["total_count"] += 1
            row_totals[target] = {
                "decrease_count": decrease_count,
                "total_count": total_count,
                "percentage": (
                    (decrease_count / total_count * 100) if total_count else 0.0
                ),
            }
            grand_decrease += decrease_count
            grand_total += total_count

        for m in magnitude_levels:
            dc = col_totals[m]["decrease_count"]
            tc = col_totals[m]["total_count"]
            col_totals[m]["percentage"] = (dc / tc * 100) if tc else 0.0

        grand = {
            "decrease_count": grand_decrease,
            "total_count": grand_total,
            "percentage": (grand_decrease / grand_total * 100) if grand_total else 0.0,
        }

        return {
            "matrix": matrix,
            "row_totals": row_totals,
            "col_totals": col_totals,
            "grand_total": grand,
            "type_distribution": {"type_a": type_a_count, "type_b": type_b_count},
            "subjects": subjects,
            "ideal_budget": ideal_budget,
            "magnitude_levels": magnitude_levels,
        }
    except Exception as e:
        logger.warning(f"Failed generating asymmetric matrix data: {e}")
        return {}


def _generate_single_user_asymmetric_matrix_table(
    choices: List[Dict], survey_id: int
) -> str:
    """Generate HTML matrix table for single user's asymmetric responses."""
    data = _generate_single_user_asymmetric_matrix_data(choices, survey_id)
    if not data or not data.get("magnitude_levels"):
        return ""

    subjects = data["subjects"]
    magnitude_levels: List[int] = data["magnitude_levels"]
    matrix = data["matrix"]
    row_totals = data["row_totals"]
    col_totals = data["col_totals"]
    grand = data["grand_total"]
    type_dist = data["type_distribution"]

    # Translations
    title = get_translation("asymmetric_matrix_title", "answers")
    target_category_label = get_translation("target_category", "answers")
    magnitude_note = get_translation("magnitude_levels_note", "answers")

    # Build table header
    header_cells = [f"<th>{html.escape(target_category_label)}</th>"]
    for m in magnitude_levels:
        header_cells.append(f"<th>X={m}</th>")
    header_cells.append("<th>%</th>")

    rows_html = []
    for target in (0, 1, 2):
        subject_name = (
            subjects[target] if target < len(subjects) else f"Category {target}"
        )
        cells = [f"<td>{html.escape(subject_name)}</td>"]
        for m in magnitude_levels:
            cell = matrix.get(target, {}).get(m)
            if not cell or not cell.get("has_data"):
                cells.append('<td class="matrix-cell-no-data" title="No data">–</td>')
            else:
                if cell.get("decrease_chosen"):
                    cells.append(
                        '<td class="matrix-cell-decrease" aria-label="Concentrated decrease"><span class="matrix-choice-dot decrease" aria-hidden="true"></span></td>'
                    )
                else:
                    cells.append(
                        '<td class="matrix-cell-increase" aria-label="Distributed decrease"><span class="matrix-choice-dot increase" aria-hidden="true"></span></td>'
                    )
        rt = row_totals.get(target, {"percentage": 0.0})
        cells.append(f"<td><b>{rt['percentage']:.0f}%</b></td>")
        rows_html.append("<tr>" + "".join(cells) + "</tr>")

    # Column totals row
    total_label = get_translation("total", "answers")
    totals_cells = [
        f'<td class="matrix-totals-row"><b>{html.escape(total_label)}</b></td>'
    ]
    for m in magnitude_levels:
        pct = col_totals[m]["percentage"]
        totals_cells.append(f'<td class="matrix-totals-row"><b>{pct:.0f}%</b></td>')
    totals_cells.append(
        f"<td class=\"matrix-totals-row\"><b>{grand['percentage']:.0f}%</b></td>"
    )

    # Legend and data summary
    legend_title = get_translation("legend_title", "answers")
    legend_note = get_translation("legend_note", "answers")

    summary_html = (
        '<div class="asymmetric-matrix-summary">'
        f'<div class="legend-title">{legend_title}</div>'
        '<div class="asymmetric-legend">'
        '<div class="legend-section">'
        '<div class="legend-items">'
        "<div class='legend-item'>"
        "<span class='legend-square decrease'></span>"
        f"<span class='legend-label'>{get_translation('legend_concentrated_desc','answers')}</span>"
        "</div>"
        "<div class='legend-item'>"
        "<span class='legend-square increase'></span>"
        f"<span class='legend-label'>{get_translation('legend_distributed_desc','answers')}</span>"
        "</div>"
        "</div>"
        "</div>"
        '<div class="legend-section legend-note">'
        f'<div class="legend-microcopy">{legend_note}</div>'
        "<div class='legend-badges'>"
        f"<span class='legend-badge'>Type A: {type_dist['type_a']}</span>"
        f"<span class='legend-badge'>Type B: {type_dist['type_b']}</span>"
        "</div>"
        "</div>"
        "</div>"
        "</div>"
    )

    table_html = (
        '<div class="asymmetric-matrix-container">'
        f'<h4 class="asymmetric-matrix-title">{html.escape(title)}</h4>'
        f'<div class="asymmetric-magnitude-note">{html.escape(magnitude_note)}</div>'
        '<table class="asymmetric-matrix-table">'
        + "<thead><tr>"
        + "".join(header_cells)
        + "</tr></thead>"
        + "<tbody>"
        + "".join(rows_html)
        + '<tr class="matrix-totals-row">'
        + "".join(totals_cells)
        + "</tr>"
        + "</tbody>"
        + "</table>"
        + summary_html
        + "</div>"
    )

    return table_html


def _get_transitivity_interpretation(rate: float) -> str:
    """Generate interpretation text for transitivity rate."""
    if rate == 100:
        return get_translation("perfect_logical_consistency", "answers")
    elif rate >= 75:
        return get_translation("high_logical_consistency", "answers")
    elif rate >= 50:
        return get_translation("moderate_consistency", "answers")
    else:
        return get_translation("low_consistency", "answers")


def _get_stability_interpretation(score: float) -> str:
    """Generate interpretation text for order stability."""
    if score >= 75:
        return get_translation("stable_preference_order", "answers")
    elif score >= 50:
        return get_translation("partially_stable_order", "answers")
    elif score >= 25:
        return get_translation("variable_preferences", "answers")
    else:
        return get_translation("highly_variable_preferences", "answers")


def _deduce_rankings(choices: List[Dict]) -> Dict:
    """
    Processes 12 pairwise choices into a structured format of 4 ranked questions.

    Args:
        choices: A list of 12 choice dictionaries from a preference ranking survey.

    Returns:
        A dictionary containing deduced pairwise preferences, full rankings,
        and magnitude values.
    """
    # Extract metadata from strategy strings and choice data
    magnitudes_set = set()
    parsed_choices = []

    for choice in choices:
        # Extract magnitude, vector_type, and pair_type from the data structure
        # Since the preference ranking strategy encodes this information
        parsed_choice = _parse_preference_ranking_choice(choice)
        if parsed_choice:
            parsed_choices.append(parsed_choice)
            magnitudes_set.add(parsed_choice["magnitude"])

    if len(magnitudes_set) != 2 or not parsed_choices:
        return None  # Invalid data

    magnitudes = sorted(list(magnitudes_set))
    x1_mag, x2_mag = magnitudes

    pairwise_preferences = {"A vs B": {}, "A vs C": {}, "B vs C": {}}
    for pair_type in pairwise_preferences:
        pairwise_preferences[pair_type] = {x1_mag: {}, x2_mag: {}}

    for parsed_choice in parsed_choices:
        pair_type = parsed_choice["pair_type"]
        magnitude = parsed_choice["magnitude"]
        vector_type = parsed_choice["vector_type"]
        user_choice = parsed_choice["user_choice"]

        op1, op2 = pair_type.split(" vs ")
        preference = f"{op1} > {op2}" if user_choice == 1 else f"{op2} > {op1}"

        # For negative questions, swap the preference direction
        if vector_type == "negative":
            # Swap the preference: "A > B" becomes "B > A"
            if " > " in preference:
                winner, loser = preference.split(" > ")
                preference = f"{loser} > {winner}"

        v_type_symbol = "+" if vector_type == "positive" else "–"

        pairwise_preferences[pair_type][magnitude][v_type_symbol] = preference

    rankings = {x1_mag: {}, x2_mag: {}}
    for mag in [x1_mag, x2_mag]:
        for v_type in ["+", "–"]:
            try:
                prefs = {
                    pt: pairwise_preferences[pt][mag][v_type]
                    for pt in ["A vs B", "A vs C", "B vs C"]
                }
                wins = {"A": 0, "B": 0, "C": 0}
                for p_str in prefs.values():
                    winner = p_str.split(" > ")[0]
                    wins[winner] += 1

                sorted_ranking = sorted(
                    wins.keys(), key=lambda k: wins[k], reverse=True
                )
                rankings[mag][v_type] = " > ".join(sorted_ranking)
            except KeyError:
                rankings[mag][v_type] = "Error"

    return {
        "magnitudes": (x1_mag, x2_mag),
        "pairwise": pairwise_preferences,
        "rankings": rankings,
    }


def _parse_preference_ranking_choice(choice: Dict) -> Optional[Dict]:
    """
    Parse a preference ranking choice to extract metadata.

    Args:
        choice: Choice dictionary from database

    Returns:
        Dictionary with parsed metadata or None if parsing fails
    """
    try:
        # Get pair number - this tells us which question and pair type
        pair_number = choice.get("pair_number")
        if not isinstance(pair_number, int) or pair_number < 1 or pair_number > 12:
            return None

        # Get user choice
        user_choice = choice.get("user_choice")
        if user_choice not in (1, 2):
            return None

        # Load the ideal allocation
        try:
            ideal_allocation = (
                json.loads(choice["optimal_allocation"])
                if isinstance(choice["optimal_allocation"], str)
                else choice["optimal_allocation"]
            )
        except (json.JSONDecodeError, KeyError):
            return None

        # Determine question number (1-4) and pair type within question
        # Questions are organized as: Q1 (pairs 1-3), Q2 (pairs 4-6), Q3 (pairs 7-9), Q4 (pairs 10-12)
        question_number = ((pair_number - 1) // 3) + 1
        pair_index_in_question = ((pair_number - 1) % 3) + 1

        # Determine pair type based on position in question
        if pair_index_in_question == 1:
            pair_type = "A vs B"
        elif pair_index_in_question == 2:
            pair_type = "A vs C"
        else:  # pair_index_in_question == 3
            pair_type = "B vs C"

        # Determine magnitude and vector type from question number
        # Q1: X1 positive, Q2: X1 negative, Q3: X2 positive, Q4: X2 negative
        min_value = min(ideal_allocation)
        x1 = max(1, round(0.2 * min_value))
        x2 = max(1, round(0.4 * min_value))

        if question_number == 1:
            magnitude = x1
            vector_type = "positive"
        elif question_number == 2:
            magnitude = x1
            vector_type = "negative"
        elif question_number == 3:
            magnitude = x2
            vector_type = "positive"
        else:  # question_number == 4
            magnitude = x2
            vector_type = "negative"

        return {
            "pair_type": pair_type,
            "magnitude": magnitude,
            "vector_type": vector_type,
            "user_choice": user_choice,
            "question_number": question_number,
        }

    except Exception as e:
        logger.warning(f"Failed to parse preference ranking choice: {e}")
        return None


def _generate_preference_ranking_pairwise_table(
    title: str, pairwise_data: Dict, magnitudes: Tuple[int, int]
) -> str:
    """Generates an HTML table for a single pairwise consistency analysis."""
    x1_mag, x2_mag = magnitudes

    def get_cons_score(p1, p2):
        return "2/2" if p1 == p2 else "0/2"

    def get_consistency_class(cons_score):
        """Get CSS class for consistency styling."""
        return "consistency-perfect" if cons_score == "2/2" else "consistency-failed"

    def get_consistency_icon(cons_score):
        """Get icon for consistency visualization."""
        return "✓" if cons_score == "2/2" else "✗"

    x1_row_cons = get_cons_score(pairwise_data[x1_mag]["+"], pairwise_data[x1_mag]["–"])
    x2_row_cons = get_cons_score(pairwise_data[x2_mag]["+"], pairwise_data[x2_mag]["–"])
    pos_col_cons = get_cons_score(
        pairwise_data[x1_mag]["+"], pairwise_data[x2_mag]["+"]
    )
    neg_col_cons = get_cons_score(
        pairwise_data[x1_mag]["–"], pairwise_data[x2_mag]["–"]
    )

    all_cons = [x1_row_cons, x2_row_cons, pos_col_cons, neg_col_cons]
    final_score = 1 if all(c == "2/2" for c in all_cons) else 0

    # Get translations for tooltips
    consistency_tooltip = get_translation("consistency_tooltip", "answers")
    final_score_tooltip = get_translation("final_score_tooltip", "answers")

    return f"""
    <h5>{title}</h5>
    <table>
        <thead>
            <tr>
                <th></th>
                <th>{get_translation('positive_question', 'answers')}</th>
                <th>{get_translation('negative_question', 'answers')}</th>
                <th>{get_translation('row_consistency', 'answers')}</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><strong>{get_translation('magnitude_0_2', 'answers')}</strong></td>
                <td>{pairwise_data[x1_mag]['+']}</td>
                <td>{pairwise_data[x1_mag]['–']}</td>
                <td class="consistency-score {get_consistency_class(x1_row_cons)}" 
                    title="{consistency_tooltip}">
                    <span class="consistency-icon">{get_consistency_icon(x1_row_cons)}</span>
                </td>
            </tr>
            <tr>
                <td><strong>{get_translation('magnitude_0_4', 'answers')}</strong></td>
                <td>{pairwise_data[x2_mag]['+']}</td>
                <td>{pairwise_data[x2_mag]['–']}</td>
                <td class="consistency-score {get_consistency_class(x2_row_cons)}"
                    title="{consistency_tooltip}">
                    <span class="consistency-icon">{get_consistency_icon(x2_row_cons)}</span>
                </td>
            </tr>
            <tr>
                <td><strong>{get_translation('column_consistency', 'answers')}</strong></td>
                <td class="consistency-score {get_consistency_class(pos_col_cons)}"
                    title="{consistency_tooltip}">
                    <span class="consistency-icon">{get_consistency_icon(pos_col_cons)}</span>
                </td>
                <td class="consistency-score {get_consistency_class(neg_col_cons)}"
                    title="{consistency_tooltip}">
                    <span class="consistency-icon">{get_consistency_icon(neg_col_cons)}</span>
                </td>
                <td class="final-score {get_consistency_class('2/2' if final_score == 1 else '0/2')}"
                    title="{final_score_tooltip}">
                    {get_translation('final_score', 'answers')}: {final_score} <span class="consistency-icon">{get_consistency_icon('2/2' if final_score == 1 else '0/2')}</span>
                </td>
            </tr>
        </tbody>
    </table>
    """


def _generate_final_ranking_summary_table(
    deduced_data: Dict,
) -> str:
    """Generates the final ranking summary table."""
    magnitudes = deduced_data["magnitudes"]
    x1_mag, x2_mag = magnitudes
    pairwise_prefs = deduced_data["pairwise"]
    rankings = deduced_data["rankings"]

    # Row Consistency
    x1_row_cons_score = sum(
        1
        for pt in pairwise_prefs
        if pairwise_prefs[pt][x1_mag]["+"] == pairwise_prefs[pt][x1_mag]["–"]
    )
    x2_row_cons_score = sum(
        1
        for pt in pairwise_prefs
        if pairwise_prefs[pt][x2_mag]["+"] == pairwise_prefs[pt][x2_mag]["–"]
    )

    # Column Consistency
    pos_col_cons_score = sum(
        1
        for pt in pairwise_prefs
        if pairwise_prefs[pt][x1_mag]["+"] == pairwise_prefs[pt][x2_mag]["+"]
    )
    neg_col_cons_score = sum(
        1
        for pt in pairwise_prefs
        if pairwise_prefs[pt][x1_mag]["–"] == pairwise_prefs[pt][x2_mag]["–"]
    )

    # Final Consistency Rate
    final_cons_score = _calculate_final_consistency_score(deduced_data)

    # Helper functions for consistency display
    def get_consistency_class(score, total):
        """Get CSS class for consistency styling."""
        if score == total:
            return "consistency-perfect"
        elif score >= 1:  # 1/3 or better
            return "consistency-partial"
        else:
            return "consistency-failed"

    def get_consistency_icon(score, total):
        """Get icon for consistency visualization."""
        if score == total:
            return "✓"
        elif score >= 1:
            return "◐"
        else:
            return "✗"

    # Get translations for tooltips
    consistency_tooltip = get_translation("consistency_tooltip", "answers")
    final_score_tooltip = get_translation("final_score_tooltip", "answers")

    return f"""
    <h5>{get_translation('final_ranking_summary_table', 'answers')}</h5>
    <table>
        <thead>
            <tr>
                <th></th>
                <th>{get_translation('positive_question', 'answers')}</th>
                <th>{get_translation('negative_question', 'answers')}</th>
                <th>{get_translation('row_consistency', 'answers')}</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><strong>{get_translation('magnitude', 'answers')} X<sub>1</sub>={x1_mag}</strong></td>
                <td>{rankings[x1_mag]['+']}</td>
                <td>{rankings[x1_mag]['–']}</td>
                <td class="consistency-score {get_consistency_class(x1_row_cons_score, 3)}"
                    title="{consistency_tooltip}">
                    <span class="consistency-icon">{get_consistency_icon(x1_row_cons_score, 3)}</span>
                    {x1_row_cons_score}/3
                </td>
            </tr>
            <tr>
                <td><strong>{get_translation('magnitude', 'answers')} X<sub>2</sub>={x2_mag}</strong></td>
                <td>{rankings[x2_mag]['+']}</td>
                <td>{rankings[x2_mag]['–']}</td>
                <td class="consistency-score {get_consistency_class(x2_row_cons_score, 3)}"
                    title="{consistency_tooltip}">
                    <span class="consistency-icon">{get_consistency_icon(x2_row_cons_score, 3)}</span>
                    {x2_row_cons_score}/3
                </td>
            </tr>
            <tr>
                <td><strong>{get_translation('column_consistency', 'answers')}</strong></td>
                <td class="consistency-score {get_consistency_class(pos_col_cons_score, 3)}"
                    title="{consistency_tooltip}">
                    <span class="consistency-icon">{get_consistency_icon(pos_col_cons_score, 3)}</span>
                    {pos_col_cons_score}/3
                </td>
                <td class="consistency-score {get_consistency_class(neg_col_cons_score, 3)}"
                    title="{consistency_tooltip}">
                    <span class="consistency-icon">{get_consistency_icon(neg_col_cons_score, 3)}</span>
                    {neg_col_cons_score}/3
                </td>
                <td class="final-score {get_consistency_class(final_cons_score, 3)}"
                    title="{final_score_tooltip}">
                    <span class="consistency-icon">{get_consistency_icon(final_cons_score, 3)}</span>
                    {final_cons_score}/3
                </td>
            </tr>
        </tbody>
    </table>
    """


def generate_preference_ranking_consistency_tables(choices: List[Dict]) -> str:
    """
    Generate consistency analysis tables for preference ranking survey strategy.

    This strategy generates 4 tables:
    1. Preference A vs B consistency table
    2. Preference A vs C consistency table
    3. Preference B vs C consistency table
    4. Final Ranking Summary table with overall consistency rate

    Args:
        choices: List of user choices from preference ranking survey

    Returns:
        str: HTML containing all 4 consistency analysis tables
    """
    logger.debug("Generating preference ranking consistency tables")

    if not choices or len(choices) != 12:
        return "<p>Preference ranking analysis requires exactly 12 choices.</p>"

    deduced_data = _deduce_rankings(choices)
    if not deduced_data:
        return "<p>Could not analyze preference ranking data due to invalid input.</p>"

    html = '<div class="preference-ranking-consistency-container">'
    html += (
        f"<h4>{get_translation('user_preference_consistency_analysis', 'answers')}</h4>"
    )

    # Tables 1-3: Pairwise Consistency
    table_translations = {
        "A vs B": "table_preference_a_vs_b",
        "A vs C": "table_preference_a_vs_c",
        "B vs C": "table_preference_b_vs_c",
    }

    for pair_type in ["A vs B", "A vs C", "B vs C"]:
        html += '<div class="pairwise-table-section">'
        html += _generate_preference_ranking_pairwise_table(
            title=get_translation(table_translations[pair_type], "answers"),
            pairwise_data=deduced_data["pairwise"][pair_type],
            magnitudes=deduced_data["magnitudes"],
        )
        html += "</div>"

    # Table 4: Final Ranking Summary
    html += '<div class="final-ranking-table-section">'
    html += _generate_final_ranking_summary_table(deduced_data)
    html += "</div>"

    # Add explanation section
    explanation_html = _generate_consistency_explanation()
    html += explanation_html

    html += "</div>"

    return html


def generate_transitivity_analysis_table(choices: List[Dict]) -> str:
    """
    Generate HTML table showing transitivity analysis for all percentile
    groups.
    """

    try:
        from analysis.transitivity_analyzer import TransitivityAnalyzer

        analyzer = TransitivityAnalyzer()
        report = analyzer.get_full_transitivity_report(choices)

        # Get translations
        title = get_translation("transitivity_analysis_title", "answers")
        group_label = get_translation("group", "answers")
        order_label = get_translation("preference_order", "answers")
        status_label = get_translation("transitivity_status", "answers")
        trans_transitive = get_translation("transitive", "answers")
        trans_intransitive = get_translation("intransitive", "answers")
        trans_transitivity_rate = get_translation(
            "overall_transitivity_rate", "answers"
        )
        trans_order_stability = get_translation("order_stability", "answers")

        # Generate enhanced rows with visual indicators
        rows_html = []
        for group_key, group_name in [
            ("core", "Core"),
            ("25", "25%"),
            ("50", "50%"),
            ("75", "75%"),
        ]:
            if group_key in report:
                data = report[group_key]

                # Enhanced status badge with SVG icon
                if data["is_transitive"]:
                    status_html = f"""
                        <span class="transitivity-status status-transitive">
                            <svg class="status-icon check" width="16"
                                height="16" viewBox="0 0 16 16"
                                fill="currentColor">
                                <path d="M13.485 1.929a1 1 0 011.414 1.414l-8
                                8a1 1 0 01-1.414 0l-3-3a1 1 0
                                011.414-1.414L6.5 9.525l7.485-7.596z"/>
                            </svg>
                            {trans_transitive}
                        </span>
                    """
                else:
                    status_html = f"""
                        <span class="transitivity-status status-intransitive">
                            <svg class="status-icon cross" width="16"
                                height="16" viewBox="0 0 16 16"
                                fill="currentColor">
                                <path d="M4.646 4.646a.5.5 0 01.708 0L8
                                7.293l2.646-2.647a.5.5 0 01.708.708L8.707
                                8l2.647 2.646a.5.5 0 01-.708.708L8
                                8.707l-2.646 2.647a.5.5 0
                                01-.708-.708L7.293 8 4.646
                                5.354a.5.5 0 010-.708z"/>
                            </svg>
                            {trans_intransitive}
                        </span>
                    """

                # Enhanced preference order display
                order_html = f'<span class="preference-order">{data["order"]}</span>'

                # Group badge with color coding
                group_badge = (
                    '<span class="group-badge group-'
                    f'{group_key}">{group_name}</span>'
                )

                rows_html.append(
                    f"""
                    <tr class="transitivity-row" data-group="{group_key}">
                        <td>{group_badge}</td>
                        <td>{order_html}</td>
                        <td>{status_html}</td>
                    </tr>
                """
                )

        # Calculate metric classes based on performance
        rate = report.get("transitivity_rate", 0.0)
        stability = report.get("order_stability_score", 0.0)

        # Format stability score for display
        if isinstance(stability, str):
            stability_score_str = stability
        else:
            stability_score_str = f"{stability:.1f}%"

        # Interpretations
        transitivity_interpretation = _get_transitivity_interpretation(rate)
        stability_interpretation = _get_stability_interpretation(stability)

        # Generate pairwise consistency table
        pairwise_consistency = report.get("pairwise_consistency", {})
        pairwise_table = _generate_pairwise_consistency_table(pairwise_consistency)

        # Construct the full table with metrics panel
        html = f"""
        <div class="transitivity-analysis-container">
            <h4 class="custom-header">{title}</h4>
            <div class="transitivity-grid">
                <div class="transitivity-table-wrapper">
                    <table id="transitivity-table">
                        <thead>
                            <tr>
                                <th>{group_label}</th>
                                <th>{order_label}</th>
                                <th>{status_label}</th>
                            </tr>
                        </thead>
                        <tbody>
                            {''.join(rows_html)}
                        </tbody>
                    </table>
                </div>

                <div class="transitivity-metrics-panel">
                    <div class="metric-group">
                        <div class="metric-item">
                            <div class="metric-value">{rate:.1f}%</div>
                            <div class="metric-label">
                                {trans_transitivity_rate}
                            </div>
                            <div class="metric-description">
                                {transitivity_interpretation}
                            </div>
                        </div>
                        <div class="metric-item">
                            <div class="metric-value">{stability_score_str}</div>
                            <div class="metric-label">{trans_order_stability}</div>
                            <div class="metric-description">
                                {stability_interpretation}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            {pairwise_table}
        </div>
        """
        return html
    except Exception as e:
        logger.error(f"Error generating transitivity table: {e}", exc_info=True)
        return ""


def _extract_extreme_vector_preferences(
    choices: List[Dict],
) -> Tuple[
    List[List[int]],
    int,
    int,
    List[Tuple[int, int, Optional[str]]],
    Dict[int, Dict[str, List[int]]],
]:
    """
    Extract extreme vector preferences from user choices, and calculate
    consistency for weighted pairs.

    Args:
        choices: List of choice dictionaries

    Returns:
        Tuple containing:
        - counts_matrix: 3x3 grid of preference counts
        - processed_pairs: number of successfully processed pairs
        - expected_pairs: expected number of pairs
        - consistency_info: list of (matches, total, core_preference)
          for each group (A vs B, ...)
        - percentile_data: Dict mapping percentiles to group consistency data
    """
    # Extract the basic preference data
    (
        counts,
        core_preferences,
        weighted_answers,
        processed_pairs,
        percentile_data,
    ) = _extract_preference_counts(choices)

    # Calculate consistency metrics between core preferences and weighted answers
    consistency_info = _calculate_consistency_metrics(
        core_preferences, weighted_answers
    )

    return (
        counts,
        processed_pairs,
        EXTREME_VECTOR_EXPECTED_PAIRS,
        consistency_info,
        percentile_data,
    )


def _extract_preference_counts(
    choices: List[Dict],
) -> Tuple[
    List[List[int]],
    List[Optional[str]],
    List[List[str]],
    int,
    Dict[int, Dict[str, List[int]]],
]:
    """
    Extract core preference counts and organize data for consistency analysis.

    Args:
        choices: List of choice dictionaries

    Returns:
        Tuple containing:
        - counts_matrix: 3x3 grid of preference counts
        - core_preferences: List of core preferences (A/B/C) for each group
        - weighted_answers: List of lists containing weighted pair preferences
          for each group
        - processed_pairs: Number of successfully processed pairs
        - percentile_data: Dict mapping percentiles to group consistency data
    """
    index_to_name = {0: "A", 1: "B", 2: "C"}
    name_to_index = {"A": 0, "B": 1, "C": 2}
    group_names = [("A", "B"), ("A", "C"), ("B", "C")]

    # Initialize counts for the 3x3 grid
    counts = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
    processed_pairs = 0

    # Store for each group: core_preference, list of weighted answers
    core_preferences = [None, None, None]  # 0: A vs B, 1: A vs C, 2: B vs C
    weighted_answers = [
        [],
        [],
        [],
    ]  # Each is a list of user choices for weighted pairs

    # Initialize percentile tracking
    percentile_data = {
        25: {"A_vs_B": [0, 0], "A_vs_C": [0, 0], "B_vs_C": [0, 0]},
        50: {"A_vs_B": [0, 0], "A_vs_C": [0, 0], "B_vs_C": [0, 0]},
        75: {"A_vs_B": [0, 0], "A_vs_C": [0, 0], "B_vs_C": [0, 0]},
    }

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
            (
                comparison_type,
                preferred_name,
            ) = _determine_comparison_and_preference(name1, name2, user_choice)
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
                # Weighted pair: store user's answer (A/B/C) for this group
                weighted_answers[group_idx].append(preferred_name)

                # Extract percentile from strategy string
                percentile = None
                if "25%" in opt1_str or "25%" in opt2_str:
                    percentile = 25
                elif "50%" in opt1_str or "50%" in opt2_str:
                    percentile = 50
                elif "75%" in opt1_str or "75%" in opt2_str:
                    percentile = 75

                if percentile is not None:
                    group_key = (
                        f"{group_names[group_idx][0]}_vs_"
                        f"{group_names[group_idx][1]}"
                    )
                    # matches[0] is total, matches[1] is matches
                    if core_preferences[group_idx] is not None:
                        percentile_data[percentile][group_key][0] += 1
                        if preferred_name == core_preferences[group_idx]:
                            percentile_data[percentile][group_key][1] += 1

        except Exception as e:
            logger.error(f"Error processing extreme choice: {e}", exc_info=True)
            continue

    return (
        counts,
        core_preferences,
        weighted_answers,
        processed_pairs,
        percentile_data,
    )


def _calculate_consistency_metrics(
    core_preferences: List[Optional[str]],
    weighted_answers: List[List[str]],
) -> List[Tuple[int, int, Optional[str]]]:
    """
    Calculate consistency metrics between core and weighted preferences.

    Args:

        core_preferences: List of core preferences (A/B/C) for each group
        weighted_answers: List of lists containing weighted pair preferences
          for each group

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


def _generate_percentile_breakdown_table(
    percentile_data: Dict[int, Dict[str, List[int]]], include_title: bool = True
) -> str:
    """
    Generate HTML table showing consistency metrics for different percentiles.

    Args:
        percentile_data: Dict mapping percentiles to group consistency data
        include_title: Whether to include the h4 title (default: True)

    Returns:
        str: HTML table showing percentile breakdown
    """
    # Get translations
    title = get_translation("percentile_breakdown_title", "answers")
    th_percentile = get_translation("percentile", "answers")
    th_a_vs_b = get_translation("a_vs_b", "answers")
    th_a_vs_c = get_translation("a_vs_c", "answers")
    th_b_vs_c = get_translation("b_vs_c", "answers")
    th_average = get_translation("average_percentage", "answers")
    all_percentiles = get_translation("all_percentiles", "answers")

    # Generate rows for each percentile
    rows = []
    total_matches = {"A_vs_B": 0, "A_vs_C": 0, "B_vs_C": 0}
    total_pairs = {"A_vs_B": 0, "A_vs_C": 0, "B_vs_C": 0}

    for percentile in sorted(percentile_data.keys()):
        group_matches = []
        totals = []
        for group in ["A_vs_B", "A_vs_C", "B_vs_C"]:
            total, match = percentile_data[percentile][group]
            group_matches.append(match)
            totals.append(total)
            total_matches[group] += match
            total_pairs[group] += total

        # Calculate row average
        row_total = sum(totals)
        row_matches = sum(group_matches)
        row_avg = (row_matches / row_total * 100) if row_total > 0 else 0

        # Generate consistency percentage and count for individual percentiles
        row_cells = []
        for i in range(3):
            current_total = totals[i]
            current_matches = group_matches[i]
            if current_total > 0:
                percentage = int(round(current_matches / current_total * 100))
                value = f"{percentage}% ({current_matches}/{current_total})"
            else:
                value = "-"
            row_cells.append(f"<td>{value}</td>")

        row = f"""
        <tr>
            <td>{percentile}%</td>
            {"".join(row_cells)}
            <td>{row_avg:.0f}% ({row_matches}/{row_total})</td>
        </tr>
        """
        rows.append(row)

    # Generate "All Percentiles" summary row
    all_cells = []
    all_total_matches = 0
    all_total_pairs = 0
    for group in ["A_vs_B", "A_vs_C", "B_vs_C"]:
        matches = total_matches[group]
        total = total_pairs[group]
        all_total_matches += matches
        all_total_pairs += total
        percentage = (matches / total * 100) if total > 0 else 0
        all_cells.append(f"<td>{percentage:.0f}% ({matches}/{total})</td>")

    # Calculate overall average
    overall_percentage = (
        (all_total_matches / all_total_pairs * 100) if all_total_pairs > 0 else 0
    )
    all_row = f"""
    <tr class="all-percentiles-row">
        <td>{all_percentiles}</td>
        {"".join(all_cells)}
        <td>{overall_percentage:.0f}% ({all_total_matches}/{all_total_pairs})</td>
    </tr>
    """
    rows.append(all_row)

    # Construct the complete table
    table_html = f"""
    <div class="percentile-breakdown-container">
        {f'<h4>{title}</h4>' if include_title else ''}
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>{th_percentile}</th>
                        <th>{th_a_vs_b}</th>
                        <th>{th_a_vs_c}</th>
                        <th>{th_b_vs_c}</th>
                        <th>{th_average}</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(rows)}
                </tbody>
            </table>
        </div>
    </div>
    """

    return table_html


def generate_aggregated_percentile_breakdown(
    user_choices: List[Dict], strategy_name: str = None
) -> str:
    """
    Generate an aggregated percentile breakdown table for all responses to an extreme vector survey.

    Args:
        user_choices: List of dictionaries containing user choices data
        strategy_name: Name of the pair generation strategy used

    Returns:
        str: HTML for the aggregated percentile breakdown table, or empty string if not applicable
    """
    # Only generate for extreme vector strategy
    if strategy_name != "peak_linearity_test":
        logger.info(
            f"Skipping percentile breakdown - strategy is {strategy_name} not peak_linearity_test"
        )
        return ""

    logger.info(
        f"Generating aggregated percentile breakdown table for extreme vector survey with {len(user_choices)} choices"
    )

    # Group choices by user
    choices_by_user = {}
    for choice in user_choices:
        user_id = choice["user_id"]
        if user_id not in choices_by_user:
            choices_by_user[user_id] = []
        choices_by_user[user_id].append(choice)

    logger.info(f"Grouped choices for {len(choices_by_user)} unique users")

    # Initialize aggregated data structure
    aggregated_data = {
        25: {"A_vs_B": [0, 0], "A_vs_C": [0, 0], "B_vs_C": [0, 0]},
        50: {"A_vs_B": [0, 0], "A_vs_C": [0, 0], "B_vs_C": [0, 0]},
        75: {"A_vs_B": [0, 0], "A_vs_C": [0, 0], "B_vs_C": [0, 0]},
    }

    user_count = 0
    # Process each user's choices to extract and aggregate percentile data
    for user_id, choices in choices_by_user.items():
        # Skip if no choices
        if not choices:
            continue

        user_count += 1
        logger.debug(f"Processing percentile data for user {user_id}")

        # Extract percentile data for this user
        _, _, _, _, percentile_data = _extract_extreme_vector_preferences(choices)

        # Add to aggregated totals
        for percentile in [25, 50, 75]:
            for group in ["A_vs_B", "A_vs_C", "B_vs_C"]:
                # percentile_data from _extract_extreme_vector_preferences is [total, match]
                # _generate_percentile_breakdown_table also expects [total, match]
                user_total_for_pg, user_matches_for_pg = percentile_data[percentile][
                    group
                ]

                # Aggregate: aggregated_data stores [total, match]
                aggregated_data[percentile][group][
                    0
                ] += user_total_for_pg  # Index 0 is total
                aggregated_data[percentile][group][
                    1
                ] += user_matches_for_pg  # Index 1 is match

    logger.debug(
        f"Aggregated percentile data from {user_count} users: {aggregated_data}"
    )

    if user_count == 0:
        logger.info("No users with valid percentile data found")
        return ""

    main_title = get_translation("percentile_breakdown_title", "answers")
    table_html = _generate_percentile_breakdown_table(
        aggregated_data, include_title=False
    )

    if not table_html:
        logger.info("No table HTML generated from percentile data for aggregation")
        return ""

    final_html = f"""
    <div class="summary-table-container survey-percentile-breakdown-container">
        <h2>{main_title}</h2>
        {table_html}
    </div>
    """
    logger.info(
        f"Generated aggregated percentile breakdown HTML, length: {len(final_html)}"
    )
    return final_html


def generate_detailed_user_choices(
    user_choices: List[Dict],
    option_labels: Tuple[str, str],
    strategy_name: str = None,
    show_tables_only: bool = False,
    show_detailed_breakdown_table: bool = True,
    show_overall_survey_table=True,
    sort_by: str = None,
    sort_order: str = "asc",
) -> Dict[str, str]:
    """Generate detailed analysis of each user's choices for each survey.

    Args:
        user_choices: List of dictionaries containing user choices data.
        option_labels: Tuple of labels for the two options.
        strategy_name: Name of the pair generation strategy used.
        show_tables_only: If True, only show summary tables.
        show_detailed_breakdown_table: If True, include detailed breakdown table.
        show_overall_survey_table: If True, include overall survey table.
        sort_by: Current sort field for table headers ('user_id', 'created_at').
        sort_order: Current sort order for table headers ('asc', 'desc').

    Returns:
        Dict[str, str]: Dictionary containing HTML components:
            - overall_stats_html: HTML for overall statistics table
            - breakdown_html: HTML for detailed breakdown table
            - user_details_html: HTML for user-specific details
            - combined_html: All components combined (for backwards compatibility)
    """
    if not user_choices:
        no_data_msg = get_translation("no_answers", "answers")
        empty_html = f'<div class="no-data">{no_data_msg}</div>'
        return {
            "overall_stats_html": empty_html,
            "breakdown_html": "",
            "user_details_html": "",
            "combined_html": empty_html,
        }

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

            # For temporal preference, calculate specific metrics
            if (
                choices
                and "strategy_name" in choices[0]
                and choices[0]["strategy_name"] == "biennial_budget_preference"
            ):
                temporal_metrics = _calculate_temporal_preference_metrics(choices)
                stats.update(temporal_metrics)
            # For dynamic temporal preference, calculate specific metrics
            if (
                choices
                and "strategy_name" in choices[0]
                and choices[0]["strategy_name"] == "biennial_budget_preference"
            ):
                dynamic_temporal_metrics = _calculate_dynamic_temporal_metrics(choices)
                stats.update(dynamic_temporal_metrics)

            # Add triangle inequality metrics if applicable
            if (
                choices
                and "strategy_name" in choices[0]
                and choices[0]["strategy_name"] == "triangle_inequality_test"
            ):
                triangle_metrics = _calculate_triangle_inequality_metrics(choices)
                stats.update(triangle_metrics)
            if (
                choices
                and "strategy_name" in choices[0]
                and choices[0]["strategy_name"] == "l1_vs_leontief_rank_comparison"
            ):
                rank_metrics = _calculate_rank_consistency_metrics(choices)
                stats.update(rank_metrics)

            if (
                choices
                and "strategy_name" in choices[0]
                and choices[0]["strategy_name"]
                == "multi_dimensional_single_peaked_test"
            ):
                single_peaked_metrics = _calculate_single_peaked_metrics(choices)
                stats.update(single_peaked_metrics)

            # Get strategy-specific metrics for enhanced stats
            try:
                from database.queries import get_user_survey_performance_data

                performance_data = get_user_survey_performance_data([user_id])
                user_survey_perf = None
                for perf in performance_data:
                    if perf["user_id"] == user_id and perf["survey_id"] == survey_id:
                        user_survey_perf = perf
                        break

                if user_survey_perf and user_survey_perf.get("strategy_metrics"):
                    # Merge strategy-specific metrics into basic stats
                    stats.update(user_survey_perf["strategy_metrics"])
            except Exception as e:
                logger.warning(
                    f"Failed to get strategy metrics for user {user_id}, survey {survey_id}: {e}"
                )

            # Add timestamp from the first choice (should be same for response)
            response_created_at = choices[0].get("response_created_at")
            summary = {
                "user_id": user_id,
                "survey_id": survey_id,
                "stats": stats,
                "response_created_at": response_created_at,
                "choices": choices,  # Store choices for all strategies
            }
            # Add strategy labels from the first choice (same for survey)
            if choices and "strategy_labels" in choices[0]:
                summary["strategy_labels"] = choices[0]["strategy_labels"]

            # Add strategy name from the first choice (same for survey)
            if choices and "strategy_name" in choices[0]:
                summary["strategy_name"] = choices[0]["strategy_name"]

            all_summaries.append(summary)

    # Initialize component HTML strings
    overall_stats_html = ""
    breakdown_html = ""
    user_details_html = ""
    all_components = []

    # 1. Overall statistics table (if requested)
    if show_overall_survey_table:
        overall_stats_html = generate_overall_statistics_table(
            all_summaries, option_labels, strategy_name
        )
        all_components.append(overall_stats_html)

    # 2. Detailed breakdown table (if requested)
    if show_detailed_breakdown_table:
        breakdown_html = generate_detailed_breakdown_table(
            all_summaries, option_labels, strategy_name, sort_by, sort_order
        )
        all_components.append(breakdown_html)

    # 3. User-specific details (only if not in tables-only mode)
    if not show_tables_only:
        user_details = []

        for user_id, surveys in grouped_choices.items():
            user_details.append(f'<section id="user-{user_id}" class="user-choices">')
            user_details.append(
                f"<h3>{get_translation('user_id', 'answers')}: {user_id}</h3>"
            )

            for survey_id, choices in surveys.items():
                # Get survey-specific strategy name if available
                survey_strategy_name = strategy_name
                if choices and "strategy_name" in choices[0]:
                    survey_strategy_name = choices[0]["strategy_name"]

                # Check if this is the extreme vectors strategy
                if survey_strategy_name == "peak_linearity_test":
                    # Generate the specific summary table for this user/survey
                    extreme_table_html = _generate_extreme_vector_analysis_table(
                        choices
                    )
                    if extreme_table_html:
                        user_details.append(extreme_table_html)

                # Check if this is the preference ranking survey strategy
                if survey_strategy_name == "preference_ranking_survey":
                    # Generate the specific consistency analysis for this user/survey
                    ranking_table_html = generate_preference_ranking_consistency_tables(
                        choices
                    )
                    if ranking_table_html:
                        user_details.append(ranking_table_html)

                # Generate the standard survey choices HTML
                # Pass the strategy_name to _generate_survey_choices_html for specialized summary
                user_details.append(
                    _generate_survey_choices_html(
                        survey_id, choices, option_labels, survey_strategy_name
                    )
                )

            user_details.append("</section>")

        user_details_html = "\n".join(user_details)
        all_components.append(user_details_html)

    # Return structured content components for flexible positioning
    return {
        "overall_stats_html": overall_stats_html,
        "breakdown_html": breakdown_html,
        "user_details_html": user_details_html,
        "combined_html": "\n".join(all_components),
    }


def generate_detailed_breakdown_table(
    summaries: List[Dict],
    option_labels: Tuple[str, str],
    strategy_name: str = None,
    sort_by: str = None,
    sort_order: str = "asc",
) -> str:
    """
    Generate detailed breakdown tables grouped by survey.

    Args:
        summaries: List of dictionaries containing survey summaries.
        option_labels: Default labels (fallback if survey-specific not found).
        strategy_name: Name of the strategy used for the survey.
        sort_by: Current sort field for table headers ('user_id', 'created_at').
        sort_order: Current sort order for table headers ('asc', 'desc').

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

        # Sort summaries within the survey group based on user preferences
        if sort_by and sort_order:
            reverse_order = sort_order.lower() == "desc"
            if sort_by == "user_id":
                sorted_summaries = sorted(
                    survey_summaries, key=lambda x: x["user_id"], reverse=reverse_order
                )
            elif sort_by == "created_at":
                sorted_summaries = sorted(
                    survey_summaries,
                    key=lambda x: x.get("response_created_at", ""),
                    reverse=reverse_order,
                )
            else:
                # Default fallback (current behavior)
                sorted_summaries = sorted(
                    survey_summaries,
                    key=lambda x: x.get("response_created_at", ""),
                    reverse=True,  # Most recent first
                )
        else:
            # No sorting specified, use default (current behavior)
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

            # Extract ideal budget if choices are available
            ideal_budget = "N/A"
            if "choices" in summary:
                ideal_budget = _format_ideal_budget(summary["choices"])

            # Generate data cells based on strategy columns
            data_cells = []

            # If we have strategy-specific columns
            if strategy_columns:
                if (
                    "consistency" in strategy_columns
                    and summary.get("strategy_name") == "preference_ranking_survey"
                ) and "choices" in summary:
                    # Handle preference_ranking_survey strategy with consistency (final score) column
                    choices = summary["choices"]
                    if len(choices) == 12:
                        deduced_data = _deduce_rankings(choices)
                        if deduced_data:
                            final_score = _calculate_final_consistency_score(
                                deduced_data
                            )
                            final_score_percent = (final_score / 3) * 100
                        else:
                            final_score_percent = 0
                    else:
                        final_score_percent = 0

                    # Highlight if consistency is high (>= 67%, which means 2/3 or 3/3)
                    highlight = "highlight-row" if final_score_percent >= 67 else ""

                    data_cells.append(
                        f'<td class="{highlight}">{final_score_percent:.1f}%</td>'
                    )
                elif (
                    "consistency" in strategy_columns
                    or "transitivity_rate" in strategy_columns
                    or "order_consistency" in strategy_columns
                ) and "choices" in summary:
                    # Handle peak_linearity_test strategy with consistency and transitivity columns
                    choices = summary["choices"]
                    _, processed_pairs, _, consistency_info, _ = (
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

                    # Get transitivity metrics
                    analyzer = TransitivityAnalyzer()
                    transitivity_report = analyzer.get_full_transitivity_report(choices)
                    transitivity_rate = transitivity_report.get(
                        "transitivity_rate", 0.0
                    )
                    order_stability = transitivity_report.get(
                        "order_stability_score", 0.0
                    )

                    # Handle string case for order_stability
                    if isinstance(order_stability, str):
                        order_stability = 0.0

                    # Generate cells with highlighting
                    highlight_consistency = (
                        "highlight-row" if overall_consistency >= 70 else ""
                    )
                    highlight_transitivity = (
                        "highlight-row" if transitivity_rate >= 75 else ""
                    )
                    highlight_order = "highlight-row" if order_stability >= 75 else ""

                    # Add consistency column if requested
                    if "consistency" in strategy_columns:
                        data_cells.append(
                            f'<td class="{highlight_consistency}">{overall_consistency}%</td>'
                        )

                    # Add transitivity rate column if requested
                    if "transitivity_rate" in strategy_columns:
                        data_cells.append(
                            f'<td class="{highlight_transitivity}">{transitivity_rate:.1f}%</td>'
                        )

                    # Add order consistency column if requested
                    if "order_consistency" in strategy_columns:
                        data_cells.append(
                            f'<td class="{highlight_order}">{order_stability:.1f}%</td>'
                        )
                elif "group_consistency" in strategy_columns and "choices" in summary:
                    # Handle component_symmetry_test strategy with group consistency
                    choices = summary["choices"]
                    if summary.get("strategy_name") == "component_symmetry_test":
                        consistencies = _calculate_cyclic_shift_group_consistency(
                            choices
                        )
                    elif summary.get("strategy_name") == "sign_symmetry_test":
                        consistencies = _calculate_linear_symmetry_group_consistency(
                            choices
                        )
                    else:
                        consistencies = {"overall": 0.0}

                    overall_consistency = consistencies.get("overall", 0.0)

                    # Highlight row if consistency is high
                    highlight = "highlight-row" if overall_consistency >= 80 else ""

                    data_cells.append(
                        f'<td class="{highlight}">{overall_consistency}%</td>'
                    )
                elif "linear_consistency" in strategy_columns and "choices" in summary:
                    # Handle sign_symmetry_test strategy with linear consistency
                    choices = summary["choices"]
                    consistencies = _calculate_linear_symmetry_group_consistency(
                        choices
                    )
                    overall_consistency = consistencies.get("overall", 0.0)

                    # Highlight row if consistency is high
                    highlight = "highlight-row" if overall_consistency >= 80 else ""

                    data_cells.append(
                        f'<td class="{highlight}">{overall_consistency}%</td>'
                    )
                elif "sum" in strategy_columns and "ratio" in strategy_columns:
                    # Handle l1_vs_leontief_comparison strategy with sum/ratio columns
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
                    # Handle l1_vs_l2_comparison strategy with rss/sum columns
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
                    # Handle l2_vs_leontief_comparison strategy with rss/ratio columns
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
                elif (
                    "concentrated_changes" in strategy_columns
                    and "distributed_changes" in strategy_columns
                ):
                    # Handle asymmetric_loss_distribution strategy
                    concentrated_percent = summary["stats"][
                        "concentrated_changes_percent"
                    ]
                    distributed_percent = summary["stats"][
                        "distributed_changes_percent"
                    ]

                    highlight_concentrated = (
                        "highlight-row"
                        if concentrated_percent > distributed_percent
                        else ""
                    )
                    highlight_distributed = (
                        "highlight-row"
                        if distributed_percent > concentrated_percent
                        else ""
                    )

                    data_cells.append(
                        f'<td class="{highlight_concentrated}">'
                        f'{format(concentrated_percent, ".1f")}%</td>'
                    )
                    data_cells.append(
                        f'<td class="{highlight_distributed}">'
                        f'{format(distributed_percent, ".1f")}%</td>'
                    )
                elif (
                    "ideal_this_year" in strategy_columns
                    and "ideal_next_year" in strategy_columns
                ):
                    # Use pre-calculated metrics from summary
                    ideal_this_year_percent = summary["stats"].get(
                        "ideal_this_year_percent", 0
                    )
                    ideal_next_year_percent = summary["stats"].get(
                        "ideal_next_year_percent", 0
                    )

                    highlight_this_year = (
                        "highlight-row"
                        if ideal_this_year_percent > ideal_next_year_percent
                        else ""
                    )
                    highlight_next_year = (
                        "highlight-row"
                        if ideal_next_year_percent > ideal_this_year_percent
                        else ""
                    )

                    data_cells.append(
                        f'<td class="{highlight_this_year}">{ideal_this_year_percent:.0f}%</td>'
                    )
                    data_cells.append(
                        f'<td class="{highlight_next_year}">{ideal_next_year_percent:.0f}%</td>'
                    )
                elif (
                    "sub1_ideal_y1" in strategy_columns
                    and "sub2_ideal_y2" in strategy_columns
                    and "sub3_ideal_y1" in strategy_columns
                ):
                    # Handle biennial_budget_preference strategy with three sub-survey columns
                    sub1_percent = summary["stats"].get("sub1_ideal_y1_percent", 0)
                    sub2_percent = summary["stats"].get("sub2_ideal_y2_percent", 0)
                    sub3_percent = summary["stats"].get("sub3_ideal_y1_percent", 0)

                    # Highlight if > 50% (preferring ideal option)
                    highlight_sub1 = "highlight-row" if sub1_percent > 50 else ""
                    highlight_sub2 = "highlight-row" if sub2_percent > 50 else ""
                    highlight_sub3 = "highlight-row" if sub3_percent > 50 else ""

                    data_cells.append(
                        f'<td class="{highlight_sub1}">{sub1_percent:.0f}%</td>'
                    )
                    data_cells.append(
                        f'<td class="{highlight_sub2}">{sub2_percent:.0f}%</td>'
                    )
                    data_cells.append(
                        f'<td class="{highlight_sub3}">{sub3_percent:.0f}%</td>'
                    )
                elif (
                    "concentrated_preference" in strategy_columns
                    and "distributed_preference" in strategy_columns
                    and "triangle_consistency" in strategy_columns
                ):
                    # Handle triangle_inequality_test strategy
                    concentrated_percent = summary["stats"].get(
                        "concentrated_percent", 0
                    )
                    distributed_percent = summary["stats"].get("distributed_percent", 0)
                    consistency_percent = summary["stats"].get("consistency_percent", 0)

                    # Highlight dominant preference
                    highlight_concentrated = (
                        "highlight-row"
                        if concentrated_percent > distributed_percent
                        else ""
                    )
                    highlight_distributed = (
                        "highlight-row"
                        if distributed_percent > concentrated_percent
                        else ""
                    )
                    # Highlight high consistency (>= 75%)
                    highlight_consistency = (
                        "highlight-row" if consistency_percent >= 75 else ""
                    )

                    data_cells.append(
                        f'<td class="{highlight_concentrated}">'
                        f"{concentrated_percent:.1f}%</td>"
                    )
                    data_cells.append(
                        f'<td class="{highlight_distributed}">'
                        f"{distributed_percent:.1f}%</td>"
                    )
                    data_cells.append(
                        f'<td class="{highlight_consistency}">'
                        f"{consistency_percent:.1f}%</td>"
                    )
                elif "option_a" in strategy_columns and "option_b" in strategy_columns:
                    # Handle preference_ranking_survey strategy with option_a/option_b columns
                    # Map to the standard option1_percent/option2_percent statistics
                    option_a_percent = summary["stats"]["option1_percent"]
                    option_b_percent = summary["stats"]["option2_percent"]

                    highlight_a = (
                        "highlight-row" if option_a_percent > option_b_percent else ""
                    )
                    highlight_b = (
                        "highlight-row" if option_b_percent > option_a_percent else ""
                    )

                    data_cells.append(
                        f'<td class="{highlight_a}">{format(option_a_percent, ".1f")}%</td>'
                    )
                    data_cells.append(
                        f'<td class="{highlight_b}">{format(option_b_percent, ".1f")}%</td>'
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
                <td class="ideal-budget-cell">{ideal_budget}</td>
                {"".join(data_cells)}
                {view_cell}
            </tr>
            """
            rows.append(row)

        # Translations for table header
        breakdown_title = get_translation("survey_response_breakdown", "answers")
        user_id_th = get_translation("user_id", "answers")
        resp_time_th = get_translation("response_time", "answers")
        ideal_budget_th = get_translation("ideal_budget", "answers")
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

        # Generate sortable headers with proper data-order attributes
        # Each header needs a data-order attribute that specifies the next sort order
        if sort_by == "user_id":
            # Currently sorting by user_id, so toggle the order
            user_id_data_order = (
                f' data-order="{"desc" if sort_order == "asc" else "asc"}"'
            )
            # Other column defaults to desc when first clicked
            created_at_data_order = ' data-order="desc"'
        elif sort_by == "created_at":
            # Currently sorting by created_at, so toggle the order
            created_at_data_order = (
                f' data-order="{"desc" if sort_order == "asc" else "asc"}"'
            )
            # Other column defaults to desc when first clicked
            user_id_data_order = ' data-order="desc"'
        else:
            # No current sort, both default to desc when first clicked
            user_id_data_order = ' data-order="desc"'
            created_at_data_order = ' data-order="desc"'

        # Generate the complete table
        table = f"""
        <div class="summary-table-container">
            <h2>{breakdown_title} - Survey {survey_id}</h2>
            <div class="table-container detailed-breakdown">
                <table>
                    <thead>
                        <tr>
                            <th class="sortable" data-sort="user_id"{user_id_data_order}>{user_id_th}</th>
                            <th class="sortable" data-sort="created_at"{created_at_data_order}>{resp_time_th}</th>
                            <th>{ideal_budget_th}</th>
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

    # Simplified table for component_symmetry_test and sign_symmetry_test strategies
    if strategy_name in ["component_symmetry_test", "sign_symmetry_test"]:
        # Calculate average consistency rate across all users
        total_consistency = 0
        valid_summaries = 0

        for summary in summaries:
            if "choices" in summary:
                choices = summary["choices"]

                if strategy_name == "component_symmetry_test":
                    consistencies = _calculate_cyclic_shift_group_consistency(choices)
                elif strategy_name == "sign_symmetry_test":
                    consistencies = _calculate_linear_symmetry_group_consistency(
                        choices
                    )
                else:
                    continue

                overall_consistency = consistencies.get("overall", 0.0)
                total_consistency += overall_consistency
                valid_summaries += 1

        # Calculate average consistency
        avg_consistency = (
            total_consistency / valid_summaries if valid_summaries > 0 else 0
        )

        # Get translation for consistency rate label
        consistency_rate_label = "Average Consistency Rate"

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
                            <td>{consistency_rate_label}</td>
                            <td>{avg_consistency:.1f}%</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <p class="summary-note">{note}</p>
        </div>
        """
        return overall_table

    # Different table for extreme vectors strategy
    elif strategy_name == "peak_linearity_test":
        # Initialize counters for all three metrics
        total_consistency = 0
        total_transitivity_rate = 0
        total_order_consistency = 0
        valid_summaries = 0

        analyzer = TransitivityAnalyzer()

        for summary in summaries:
            if "choices" in summary:
                choices = summary["choices"]

                # Calculate existing consistency metric
                _, processed_pairs, _, consistency_info, _ = (
                    _extract_extreme_vector_preferences(choices)
                )

                if processed_pairs > 0 and consistency_info:
                    # Overall consistency calculation
                    total_matches = sum(
                        matches for matches, total, _ in consistency_info
                    )
                    total_pairs = sum(total for _, total, _ in consistency_info)

                    if total_pairs > 0:
                        consistency = (total_matches / total_pairs) * 100
                        total_consistency += consistency

                        # Calculate transitivity metrics
                        transitivity_report = analyzer.get_full_transitivity_report(
                            choices
                        )
                        transitivity_rate = transitivity_report.get(
                            "transitivity_rate", 0.0
                        )
                        order_stability = transitivity_report.get(
                            "order_stability_score", 0.0
                        )

                        # Handle string case for order stability
                        if isinstance(order_stability, str):
                            order_stability = 0.0

                        total_transitivity_rate += transitivity_rate
                        total_order_consistency += order_stability
                        valid_summaries += 1

        # Calculate averages for all three metrics
        avg_consistency = (
            total_consistency / valid_summaries if valid_summaries > 0 else 0
        )
        avg_transitivity_rate = (
            total_transitivity_rate / valid_summaries if valid_summaries > 0 else 0
        )
        avg_order_consistency = (
            total_order_consistency / valid_summaries if valid_summaries > 0 else 0
        )

        # Get translation for consistency
        overall_consistency_label = get_translation("overall_consistency", "answers")

        # Get translations for all three labels
        overall_consistency_label = get_translation("overall_consistency", "answers")
        avg_transitivity_label = get_translation("transitivity_rate", "answers")
        avg_order_label = get_translation("order_consistency", "answers")

        # Generate three-row table
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
                        <tr class="highlight-row">
                            <td>{avg_transitivity_label}</td>
                            <td>{avg_transitivity_rate:.1f}%</td>
                        </tr>
                        <tr class="highlight-row">
                            <td>{avg_order_label}</td>
                            <td>{avg_order_consistency:.1f}%</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <p class="summary-note">{note}</p>
        </div>
        """
    elif strategy_name == "multi_dimensional_single_peaked_test":
        overall_table = _generate_single_peaked_overall_consistency_table(
            summaries, title, note
        )
    elif strategy_name == "triangle_inequality_test":
        overall_table = _generate_triangle_overall_consistency_table(
            summaries, title, note
        )
    elif strategy_name == "l1_vs_leontief_rank_comparison":
        overall_table = _generate_rank_overall_consistency_table(
            summaries, title, note, option_labels
        )
    elif strategy_name == "biennial_budget_preference":
        # Handle dynamic temporal preference strategy using three consistency breakdown tables
        # Extract all user choices from summaries
        all_user_choices = []
        for summary in summaries:
            if "choices" in summary:
                all_user_choices.extend(summary["choices"])

        # Use the three-table consistency breakdown for distribution by consistency level
        if all_user_choices:
            overall_table = generate_dynamic_temporal_consistency_breakdown_tables(
                all_user_choices
            )
        else:
            # Fallback if no choices available
            overall_table = f"""
            <div class="summary-table-container">
                <h2>{title}</h2>
                <p class="summary-note">No data available for consistency analysis.</p>
            </div>
            """
    elif strategy_name == "preference_ranking_survey":
        # Handle preference ranking survey strategy
        # Calculate average final-score across all users
        total_final_scores = 0
        valid_summaries = 0

        for summary in summaries:
            if "choices" in summary:
                choices = summary["choices"]
                # Only process if we have exactly 12 choices for preference ranking
                if len(choices) == 12:
                    deduced_data = _deduce_rankings(choices)
                    if deduced_data:
                        final_score = _calculate_final_consistency_score(deduced_data)
                        total_final_scores += final_score
                        valid_summaries += 1

        # Calculate average final score as percentage
        avg_final_score = (
            total_final_scores / valid_summaries if valid_summaries > 0 else 0
        )
        avg_final_score_percent = (avg_final_score / 3) * 100

        # Get translation for final score label
        final_score_label = get_translation("final_score", "answers")

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
                            <td>{final_score_label}</td>
                            <td>{avg_final_score_percent:.1f}%</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <p class="summary-note">{note}</p>
        </div>
        """
    elif strategy_name in ["l1_vs_l2_comparison", "l2_vs_leontief_comparison"]:
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
            if strategy_name == "l1_vs_l2_comparison"
            else get_translation("ratio", "answers")
        )

        # For these strategies, we need to adjust the percentages
        # sum_percent is actually the sum% for l1_vs_l2_comparison and rss% for l2_vs_leontief_comparison
        # ratio_percent is actually rss% for l1_vs_l2_comparison and ratio% for l2_vs_leontief_comparison
        if strategy_name == "root_sul1_vs_l2_comparisonm_squared_sum":
            avg_rss = 100 - avg_sum  # RSS is the complement of sum
            avg_col1 = avg_rss
            avg_col2 = avg_sum
        else:  # l2_vs_leontief_comparison
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


def _generate_matrix_header_cell(survey_id: int, strategy_columns: Dict) -> str:
    """Helper to generate a single header cell for the matrix."""
    survey_label = get_translation("survey_label", "answers")

    # Build the sub-header label using translations
    sub_header = ""
    if "consistency" in strategy_columns:
        sub_header = get_translation("consistency", "answers")
    elif (
        "group_consistency" in strategy_columns
        or "linear_consistency" in strategy_columns
    ):
        sub_header = get_translation("group_consistency", "answers")
    elif "sum" in strategy_columns and "ratio" in strategy_columns:
        sum_label = get_translation("sum", "answers")
        ratio_label = get_translation("ratio", "answers")
        sub_header = f"{sum_label} / {ratio_label}"
    elif "rss" in strategy_columns:
        rss_label = get_translation("root_sum_squared", "answers")
        if "sum" in strategy_columns:
            sum_label = get_translation("sum", "answers")
            sub_header = f"{rss_label} / {sum_label}"
        elif "ratio" in strategy_columns:
            ratio_label = get_translation("ratio", "answers")
            sub_header = f"{rss_label} / {ratio_label}"
    elif (
        "concentrated_changes" in strategy_columns
        and "distributed_changes" in strategy_columns
    ):
        # Handle asymmetric_loss_distribution strategy
        concentrated_name = strategy_columns["concentrated_changes"]["name"]
        distributed_name = strategy_columns["distributed_changes"]["name"]
        sub_header = f"{concentrated_name} / {distributed_name}"
    elif "option1" in strategy_columns and "option2" in strategy_columns:
        option1_name = strategy_columns["option1"]["name"]
        option2_name = strategy_columns["option2"]["name"]
        sub_header = f"{option1_name} / {option2_name}"
    else:
        sub_header = "Opt1 / Opt2"

    return f'<th class="matrix-survey-header" data-survey="{survey_id}">{survey_label} {survey_id}<br><small>{sub_header}</small></th>'


def _generate_matrix_data_cell(record: Dict) -> str:
    """Helper to generate a single data cell for the matrix."""
    metrics = record["strategy_metrics"]
    strategy_columns = record["strategy_columns"]
    survey_id = record["survey_id"]

    cell_content = ""
    # Generate cell content based on strategy
    if "consistency" in strategy_columns:
        consistency = metrics.get("consistency", 0)
        cell_content = f'<span class="metric-value">{consistency}%</span>'
    elif (
        "group_consistency" in strategy_columns
        or "linear_consistency" in strategy_columns
    ):
        consistency = metrics.get("group_consistency", 0.0)
        cell_content = f'<span class="metric-value">{consistency:.0f}%</span>'
    elif "sum" in strategy_columns and "ratio" in strategy_columns:
        sum_percent = metrics.get("sum_percent", 0)
        ratio_percent = metrics.get("ratio_percent", 0)
        # cell_content = f'<span class="metric-pair">{sum_percent:.0f}% / {ratio_percent:.0f}%</span>'
        cell_content = f'<span class="metric-pair">{sum_percent:.0f}%&nbsp;/&nbsp;{ratio_percent:.0f}%</span>'
    elif "rss" in strategy_columns:
        rss_percent = metrics.get("rss_percent", 0)
        if "sum" in strategy_columns:
            sum_percent = metrics.get("sum_percent", 0)
            cell_content = f'<span class="metric-pair">{rss_percent:.0f}% / {sum_percent:.0f}%</span>'
        elif "ratio" in strategy_columns:
            ratio_percent = metrics.get("ratio_percent", 0)
            cell_content = f'<span class="metric-pair">{rss_percent:.0f}% / {ratio_percent:.0f}%</span>'
        else:
            cell_content = f'<span class="metric-value">{rss_percent:.0f}%</span>'
    elif (
        "concentrated_changes" in strategy_columns
        and "distributed_changes" in strategy_columns
    ):
        # Handle asymmetric_loss_distribution strategy
        concentrated_percent = metrics.get("concentrated_changes_percent", 0)
        distributed_percent = metrics.get("distributed_changes_percent", 0)
        cell_content = (
            f'<span class="metric-pair">{concentrated_percent:.0f}% / '
            f"{distributed_percent:.0f}%</span>"
        )
    elif "option1" in strategy_columns and "option2" in strategy_columns:
        opt1_percent = metrics.get("option1_percent", 0)
        opt2_percent = metrics.get("option2_percent", 0)
        cell_content = f'<span class="metric-pair">{opt1_percent:.0f}% / {opt2_percent:.0f}%</span>'
    else:
        opt1_percent = metrics.get("option1_percent", 0)
        opt2_percent = metrics.get("option2_percent", 0)
        cell_content = f'<span class="metric-pair">{opt1_percent:.0f}% / {opt2_percent:.0f}%</span>'

    return f'<td class="matrix-data-cell" data-survey="{survey_id}">{cell_content}</td>'


def generate_user_survey_matrix_html(performance_data: List[Dict]) -> str:
    """
    Generate HTML matrix table showing user performance across all surveys.

    Args:
        performance_data: List of user-survey performance records from get_user_survey_performance_data()

    Returns:
        str: HTML string containing the responsive matrix table
    """
    if not performance_data:
        no_data_msg = get_translation("no_answers", "answers")
        return f'<div class="no-data">{no_data_msg}</div>'

    # 1. Organize data
    users = {}
    survey_info = {}
    all_surveys = set()

    for record in performance_data:
        user_id = record["user_id"]
        survey_id = record["survey_id"]
        all_surveys.add(survey_id)
        if user_id not in users:
            users[user_id] = {}
        users[user_id][survey_id] = record
        if survey_id not in survey_info:
            survey_info[survey_id] = {"strategy_columns": record["strategy_columns"]}

    sorted_users = sorted(users.keys())
    sorted_surveys = sorted(list(all_surveys))

    # 2. Get Translations
    user_id_label = get_translation("user_id", "answers")
    matrix_title = get_translation("user_survey_matrix", "answers")
    matrix_description = get_translation("matrix_description", "answers")
    users_summary_label = get_translation("matrix_summary_users", "answers")
    surveys_summary_label = get_translation("matrix_summary_surveys", "answers")
    responses_summary_label = get_translation(
        "matrix_summary_total_responses", "answers"
    )

    # 3. Generate Headers
    header_cells = [f'<th class="matrix-user-header">{user_id_label}</th>']
    for survey_id in sorted_surveys:
        header_cells.append(
            _generate_matrix_header_cell(
                survey_id, survey_info[survey_id]["strategy_columns"]
            )
        )

    # 4. Generate Rows
    rows = []
    for user_id in sorted_users:
        display_id, is_truncated = _format_user_id(user_id)
        tooltip = (
            f'<span class="user-id-tooltip">{user_id}</span>' if is_truncated else ""
        )
        row_cells = [
            f"""<td class="matrix-user-cell{' truncated' if is_truncated else ''}">
                   <a href="/surveys/users/{user_id}/responses" class="user-link" target="_blank">{display_id}</a>
                   {tooltip}
               </td>"""
        ]

        for survey_id in sorted_surveys:
            if survey_id in users[user_id]:
                record = users[user_id][survey_id]
                row_cells.append(_generate_matrix_data_cell(record))
            else:
                row_cells.append(
                    f'<td class="matrix-data-cell no-participation" data-survey="{survey_id}"><span class="no-data-indicator">-</span></td>'
                )

        rows.append(
            f'<tr class="matrix-row" data-user="{user_id}">{"".join(row_cells)}</tr>'
        )

    # 5. Assemble Final HTML
    # Add note about current page data if this appears to be paginated data
    page_note = ""
    if len(sorted_users) <= 20:  # Likely paginated if showing 20 or fewer users
        page_note_text = get_translation(
            "current_page_summary", "pagination", users_count=len(sorted_users)
        )
        page_note = (
            f'<br><small style="color: #7f8c8d; font-style: italic;">'
            f"{page_note_text}</small>"
        )

    matrix_html = f"""
    <div class="matrix-container">
        <h2 class="matrix-title">{matrix_title}</h2>
        <div class="matrix-description"><p>{matrix_description}</p></div>
        <div class="matrix-table-wrapper">
            <table class="matrix-table">
                <thead><tr class="matrix-header-row">{"".join(header_cells)}</tr></thead>
                <tbody>{"".join(rows)}</tbody>
            </table>
        </div>
        <div class="matrix-summary">
            <p><strong>{users_summary_label}:</strong> {len(sorted_users)} | <strong>{surveys_summary_label}:</strong> {len(sorted_surveys)} | <strong>{responses_summary_label}:</strong> {len(performance_data)}{page_note}</p>
        </div>
    </div>
    """
    return matrix_html


def _calculate_cyclic_shift_group_consistency(choices: List[Dict]) -> Dict[str, float]:
    """
    Calculate group-level consistency for cyclic shift strategy using binary
    metric.

    Binary consistency: A group is 100% consistent only if all 3 choices match,
    otherwise 0% consistent.

    Args:
        choices: List of choices for a single user's survey response using the
                component_symmetry_test strategy.

    Returns:
        Dict containing binary consistency (0% or 100%) for each group (1-4)
        and overall percentage of consistent groups.
        Format: {"group_1": 100.0, "group_2": 0.0, "group_3": 100.0,
                 "group_4": 0.0, "overall": 50.0}
    """
    # Initialize group data - each group should have 3 pairs
    groups = {1: [], 2: [], 3: [], 4: []}

    # Analyze each choice and assign to appropriate group
    for choice in choices:
        option1_strategy = choice.get("option1_strategy", "")
        option2_strategy = choice.get("option2_strategy", "")
        user_choice = choice["user_choice"]

        # Extract shift information from strategy names
        # Expected format: "Cyclic Pattern A (shift X)" or
        # "Cyclic Pattern B (shift X)"
        shift_amount = None
        chosen_pattern = None

        if "shift" in option1_strategy:
            try:
                shift_part = option1_strategy.split("shift ")[1].split(")")[0]
                shift_amount = int(shift_part)
                chosen_pattern = "A" if user_choice == 1 else "B"
            except (IndexError, ValueError):
                continue
        elif "shift" in option2_strategy:
            try:
                shift_part = option2_strategy.split("shift ")[1].split(")")[0]
                shift_amount = int(shift_part)
                chosen_pattern = "B" if user_choice == 2 else "A"
            except (IndexError, ValueError):
                continue

        if shift_amount is not None and chosen_pattern:
            # Determine group based on pair index (0-11 maps to groups 1-4)
            # Each group has 3 pairs: Group 1: pairs 0-2, Group 2: pairs 3-5
            pair_number = choice.get("pair_number", 0)
            if pair_number > 0:  # pair_number is 1-indexed
                group_number = ((pair_number - 1) // 3) + 1
                if 1 <= group_number <= 4:
                    groups[group_number].append(chosen_pattern)

    # Calculate binary consistency for each group
    group_consistencies = {}
    consistent_groups = 0
    total_groups_with_data = 0

    for group_num, patterns in groups.items():
        if len(patterns) != 3:
            # Incomplete group - mark as 0% consistent
            group_consistencies[f"group_{group_num}"] = 0.0
            if len(patterns) > 0:
                total_groups_with_data += 1
            continue

        total_groups_with_data += 1

        # Binary consistency: all 3 must match
        if len(set(patterns)) == 1:  # All patterns are identical
            group_consistencies[f"group_{group_num}"] = 100.0
            consistent_groups += 1
        else:
            group_consistencies[f"group_{group_num}"] = 0.0

    # Calculate overall consistency as percentage of consistent groups
    if total_groups_with_data > 0:
        overall_consistency = (consistent_groups / total_groups_with_data) * 100
        group_consistencies["overall"] = round(overall_consistency, 1)
    else:
        group_consistencies["overall"] = 0.0

    return group_consistencies


def _calculate_linear_symmetry_group_consistency(
    choices: List[Dict],
) -> Dict[str, float]:
    """
    Calculate group-level consistency for linear symmetry strategy.

    Linear symmetry means making the same relative choice between vectors v1
    and v2 regardless of whether they're applied as positive or negative
    distances.

    For each group:
    - Pair A (positive): (ideal + v1) vs (ideal + v2)
    - Pair B (negative): (ideal - v1) vs (ideal - v2)
    - Consistency = 100% if user chooses same vector in both pairs, 0%
      otherwise

    Args:
        choices: List of choices for a single user's survey response using the
                sign_symmetry_test strategy.

    Returns:
        Dict containing consistency percentages for each group (1-6) and
        overall average.
        Example: {"group_1": 100.0, "group_2": 0.0, ..., "overall": 66.7}
    """
    # Initialize group data - each group should have 2 pairs (+ and -)
    groups = {1: {}, 2: {}, 3: {}, 4: {}, 5: {}, 6: {}}

    # Parse each choice and extract group, sign, and vector choice
    for choice in choices:
        option1_strategy = choice.get("option1_strategy", "")
        option2_strategy = choice.get("option2_strategy", "")
        user_choice = choice["user_choice"]  # 1 or 2

        # Extract group number, sign (+/-), and which vector user chose
        group_num, sign, vector_choice = _parse_linear_pattern_strategy(
            option1_strategy, option2_strategy, user_choice
        )

        if group_num is not None and sign is not None and vector_choice is not None:
            if 1 <= group_num <= 6:
                # Store which vector (1 for v, 2 for w) user chose for
                # this sign
                groups[group_num][sign] = vector_choice

    # Calculate consistency for each group
    group_consistencies = {}
    for group_num in range(1, 7):
        group_data = groups[group_num]

        if len(group_data) == 2 and "+" in group_data and "-" in group_data:
            # We have both positive and negative pairs for this group
            positive_choice = group_data["+"]  # 1 (v) or 2 (w)
            negative_choice = group_data["-"]  # 1 (v) or 2 (w)

            # Linear symmetry: same relative choice regardless of sign
            is_consistent = positive_choice == negative_choice
            consistency_percentage = 100.0 if is_consistent else 0.0

            group_consistencies[f"group_{group_num}"] = consistency_percentage
        else:
            # Incomplete data for this group (missing + or - pair)
            group_consistencies[f"group_{group_num}"] = 0.0

    # Calculate overall consistency as average of valid group consistencies
    # Only consider groups that have complete data (both + and - pairs)
    valid_consistencies = [
        group_consistencies[f"group_{i}"] for i in range(1, 7) if len(groups[i]) == 2
    ]

    if valid_consistencies:
        overall_consistency = sum(valid_consistencies) / len(valid_consistencies)
        group_consistencies["overall"] = round(overall_consistency, 1)
    else:
        group_consistencies["overall"] = 0.0

    return group_consistencies


def _parse_linear_pattern_strategy(
    option1_strategy: str, option2_strategy: str, user_choice: int
) -> Tuple[Optional[int], Optional[str], Optional[int]]:
    """
    Parse linear pattern strategy strings to extract group, sign, and vector choice.

    Expected format: "Linear Pattern + (v1)" or "Linear Pattern - (w2)"

    Args:
        option1_strategy: Strategy description for option 1
        option2_strategy: Strategy description for option 2
        user_choice: User's choice (1 or 2)

    Returns:
        Tuple of (group_number, sign, vector_choice) where:
        - group_number: 1-6 (extracted from strategy)
        - sign: '+' or '-' (extracted from strategy)
        - vector_choice: 1 if user chose v vector, 2 if user chose w vector
    """
    import re

    # Regex pattern to match: "Linear Pattern [+/-] ([v/w][group_number])"
    pattern = r"Linear Pattern ([+-]) \(([vw])(\d+)\)"

    match1 = re.search(pattern, option1_strategy)
    match2 = re.search(pattern, option2_strategy)

    if not match1 or not match2:
        logger.debug(
            f"Failed to parse linear pattern: '{option1_strategy}' vs "
            f"'{option2_strategy}'"
        )
        return None, None, None

    sign1, vector1, group1 = match1.groups()
    sign2, vector2, group2 = match2.groups()

    # Validate that both options are from the same group and sign
    if group1 != group2 or sign1 != sign2:
        logger.debug(
            f"Mismatched group/sign: group1={group1}, group2={group2}, "
            f"sign1={sign1}, sign2={sign2}"
        )
        return None, None, None

    group_num = int(group1)
    sign = sign1

    # Determine which vector the user chose
    if user_choice == 1:
        chosen_vector = vector1  # 'v' or 'w'
    elif user_choice == 2:
        chosen_vector = vector2  # 'v' or 'w'
    else:
        logger.debug(f"Invalid user_choice: {user_choice}")
        return None, None, None

    # Convert to numeric: v=1, w=2
    vector_choice = 1 if chosen_vector == "v" else 2

    return group_num, sign, vector_choice


def _generate_cyclic_shift_consistency_table(choices: List[Dict]) -> str:
    """
    Generate HTML table showing binary group-level consistency for cyclic
    shift strategy.

    Updated to clearly indicate binary nature of consistency (100% or 0%).

    Args:
        choices: List of choices for a single user's survey response using the
                component_symmetry_test strategy.

    Returns:
        str: HTML table string showing binary group consistency.
    """
    try:
        consistency_data = _calculate_cyclic_shift_group_consistency(choices)

        if not consistency_data:
            return ""

        # Get translations
        group_label = get_translation("group", "answers")
        consistency_label = get_translation("consistency", "answers")
        overall_label = get_translation("overall", "answers")
        table_title = get_translation("group_consistency", "answers")

        # Helper function for binary consistency styling
        def get_consistency_class(percentage):
            return "consistency-high" if percentage == 100 else "consistency-low"

        # Build table rows
        rows = []
        for i in range(1, 5):
            group_key = f"group_{i}"
            if group_key in consistency_data:
                percentage = consistency_data[group_key]
                consistency_class = get_consistency_class(percentage)
                # Show checkmark for consistent, X for inconsistent
                icon = "✓" if percentage == 100 else "✗"
                rows.append(
                    f"""
                    <tr data-group="{i}">
                        <td>{group_label} {i}</td>
                        <td class="{consistency_class}" data-percentage="{percentage}">
                            <span class="consistency-icon">{icon}</span>
                            {percentage:.0f}%
                        </td>
                    </tr>
                """
                )

        # Overall summary row
        overall_percentage = consistency_data.get("overall", 0)
        # For overall, show as fraction of consistent groups
        consistent_count = sum(
            1 for i in range(1, 5) if consistency_data.get(f"group_{i}", 0) == 100
        )

        # Get translation for "groups"
        groups_label = get_translation("groups", "answers")

        table_html = f"""
        <div class="cyclic-shift-consistency-container">
            <h4 class="consistency-table-title">{table_title}</h4>
            <div class="consistency-table-wrapper">
                <table class="consistency-table">
                    <thead>
                        <tr>
                            <th>{group_label}</th>
                            <th>{consistency_label}</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(rows)}
                        <tr class="overall-consistency" data-group="overall">
                            <td>{overall_label}</td>
                            <td data-percentage="{overall_percentage}">
                                {consistent_count}/4 {groups_label} ({overall_percentage:.0f}%)
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <div class="consistency-legend">
                <small class="consistency-note">
                    Binary consistency: A group is consistent (100%) only if all 3 
                    choices match the same pattern, otherwise inconsistent (0%).
                </small>
            </div>
        </div>
        """

        return table_html

    except Exception as e:
        logger.error(f"Error generating cyclic shift consistency table: {str(e)}")
        return ""


def _generate_linear_symmetry_consistency_table(choices: List[Dict]) -> str:
    """
    Generate HTML table showing group-level consistency for linear symmetry strategy.

    Args:
        choices: List of choices for a single user's survey response using the
                sign_symmetry_test strategy.

    Returns:
        str: HTML table string showing group consistency percentages.
    """
    try:
        consistency_data = _calculate_linear_symmetry_group_consistency(choices)

        if not consistency_data:
            return ""

        # Get translations
        group_label = get_translation("group", "answers")
        consistency_label = get_translation("consistency_percent", "answers")
        overall_label = get_translation("overall", "answers")
        table_title = get_translation("group_consistency", "answers")

        # Helper function to determine consistency level for styling
        def get_consistency_class(percentage):
            if percentage >= 80:
                return "consistency-high"
            elif percentage >= 60:
                return "consistency-medium"
            else:
                return "consistency-low"

        # Build table rows for 6 groups (linear symmetry has 6 groups)
        rows = []
        for i in range(1, 7):
            group_key = f"group_{i}"
            if group_key in consistency_data:
                percentage = consistency_data[group_key]
                consistency_class = get_consistency_class(percentage)
                rows.append(
                    f"""
                    <tr data-group="{i}">
                        <td>{group_label} {i}</td>
                        <td class="{consistency_class}" data-percentage="{percentage}">
                            {percentage:.1f}%
                            <div class="consistency-bar" style="width: {percentage}%"></div>
                        </td>
                    </tr>
                """
                )

        # Overall summary row
        overall_percentage = consistency_data.get("overall", 0)
        overall_class = get_consistency_class(overall_percentage)

        table_html = f"""
        <div class="cyclic-shift-consistency-container">
            <h4 class="consistency-table-title">{table_title}</h4>
            <div class="consistency-table-wrapper">
                <table class="consistency-table">
                    <thead>
                        <tr>
                            <th>{group_label}</th>
                            <th>{consistency_label}</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(rows)}
                        <tr class="overall-consistency" data-group="overall">
                            <td>{overall_label}</td>
                            <td class="{overall_class}" data-percentage="{overall_percentage}">
                                {overall_percentage:.1f}%
                                <div class="consistency-bar" style="width: {overall_percentage}%"></div>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <div class="consistency-legend">
                <small class="consistency-note">
                    {get_translation("consistency_explanation", "answers")}
                </small>
            </div>
        </div>
        """

        return table_html

    except Exception as e:
        logger.error(f"Error generating linear symmetry consistency table: {str(e)}")
        return ""


def _format_ideal_budget(choices: List[Dict]) -> str:
    """
    Extract and format the ideal budget allocation from user choices.

    Args:
        choices: List of choices for the user (should all have same
                optimal_allocation)

    Returns:
        str: Formatted ideal budget string like "[60, 25, 15]"
    """
    if not choices:
        return "N/A"

    try:
        # Get optimal allocation from first choice (all should be same)
        optimal_allocation = json.loads(choices[0]["optimal_allocation"])
        return str(optimal_allocation)
    except (json.JSONDecodeError, KeyError, IndexError):
        return "N/A"


def _generate_consistency_explanation() -> str:
    """Generate explanation section for preference ranking consistency."""
    explanation_title = get_translation("consistency_explanation_title", "answers")
    explanation_text = get_translation("consistency_explanation_text", "answers")

    return f"""
    <div class="consistency-explanation">
        <h5>{explanation_title}</h5>
        <p>{explanation_text}</p>
        <div class="consistency-legend">
            <div class="legend-item">
                <span class="legend-icon consistency-perfect">✓</span>
                <span class="legend-text">{get_translation('perfect_consistency_label', 'answers', fallback='Perfect Consistency')}</span>
            </div>
            <div class="legend-item">
                <span class="legend-icon consistency-partial">◐</span>
                <span class="legend-text">{get_translation('partial_consistency_label', 'answers', fallback='Partial Consistency')}</span>
            </div>
            <div class="legend-item">
                <span class="legend-icon consistency-failed">✗</span>
                <span class="legend-text">{get_translation('failed_consistency_label', 'answers', fallback='Failed Consistency')}</span>
            </div>
        </div>
    </div>
    """


def _generate_pairwise_consistency_table(
    pairwise_consistency: Dict,
) -> str:
    """Generate HTML table for pairwise consistency analysis."""
    if not pairwise_consistency:
        return ""

    headers = [
        get_translation("comparison_pair", "headers"),
        get_translation("dominant_preference", "headers"),
        get_translation("consistent_groups", "headers"),
    ]

    rows = []
    for pair, data in pairwise_consistency.items():
        pair_str = pair.replace("_", " ").replace("vs", "vs.")
        dominant_pref = data.get("dominant_preference", "N/A")
        consistent_groups = data.get("consistent_groups", "N/A")
        total_groups = data.get("total_groups", "N/A")
        rows.append(
            f"""
            <tr>
                <td>{pair_str}</td>
                <td>{dominant_pref}</td>
                <td>{consistent_groups}/{total_groups}</td>
            </tr>
            """
        )

    caption = get_translation("pairwise_consistency_caption", "tables")
    table_title = get_translation("pairwise_consistency_title", "tables")

    return f"""
    <div class="pairwise-consistency-container">
        <h5 class="custom-header">{table_title}</h5>
        <p class="caption">{caption}</p>
        <table class="dataframe">
            <thead>
                <tr>
                    {''.join(f'<th>{h}</th>' for h in headers)}
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
    </div>
    """


def _calculate_temporal_preference_metrics(choices: List[Dict]) -> Dict[str, float]:
    """
    Calculate temporal preference metrics for a single user's response.

    Args:
        choices: List of choices for a single user's temporal preference survey

    Returns:
        Dict containing calculated metrics:
        - ideal_this_year_percent: Percentage choosing "Ideal This Year" (Option 1)
        - ideal_next_year_percent: Percentage choosing "Ideal Next Year" (Option 2)
        - consistency_percent: Max(ideal_this_year_count, ideal_next_year_count) * 10
    """
    if not choices:
        return {
            "ideal_this_year_percent": 0.0,
            "ideal_next_year_percent": 0.0,
            "consistency_percent": 0.0,
        }

    total_choices = len(choices)
    ideal_this_year_count = 0

    for choice in choices:
        user_choice = choice.get("user_choice")
        if user_choice == 1:  # Option 1 is "Ideal This Year"
            ideal_this_year_count += 1

    ideal_next_year_count = total_choices - ideal_this_year_count

    # Calculate percentages
    ideal_this_year_percent = (ideal_this_year_count / total_choices) * 100
    ideal_next_year_percent = (ideal_next_year_count / total_choices) * 100

    # Consistency is max(X, Y) * 10 where X+Y=10
    consistency_percent = max(ideal_this_year_count, ideal_next_year_count) * 10

    return {
        "ideal_this_year_percent": ideal_this_year_percent,
        "ideal_next_year_percent": ideal_next_year_percent,
        "consistency_percent": consistency_percent,
    }


def _calculate_dynamic_temporal_metrics(choices: List[Dict]) -> Dict[str, float]:
    """
    Calculate dynamic temporal preference metrics for a single user's response.

    Args:
        choices: List of choices for a single user's dynamic temporal survey (12 choices)

    Returns:
        Dict containing calculated metrics for each sub-survey:
        - sub1_ideal_y1_percent: % choosing Ideal Year 1 in Sub-Survey 1 (Simple Discounting)
        - sub2_ideal_y2_percent: % choosing Ideal Year 2 in Sub-Survey 2 (Second-Year Choice)
        - sub3_ideal_y1_percent: % choosing Ideal Year 1 in Sub-Survey 3 (First-Year Choice)
    """
    if not choices or len(choices) != 12:
        return {
            "sub1_ideal_y1_percent": 0.0,
            "sub2_ideal_y2_percent": 0.0,
            "sub3_ideal_y1_percent": 0.0,
        }

    # Initialize counters for each sub-survey
    sub1_ideal_count = 0  # Sub-Survey 1: Simple Discounting (pairs 1-4)
    sub2_ideal_count = 0  # Sub-Survey 2: Second-Year Choice (pairs 5-8)
    sub3_ideal_count = 0  # Sub-Survey 3: First-Year Choice (pairs 9-12)

    for choice in choices:
        pair_number = choice.get("pair_number", 0)
        user_choice = choice.get("user_choice")

        if 1 <= pair_number <= 4:
            # Sub-Survey 1: Simple Discounting
            # Option 1 = (Ideal, Random), Option 2 = (Random, Ideal)
            # Choosing Option 1 means preferring Ideal Year 1
            if user_choice == 1:
                sub1_ideal_count += 1
        elif 5 <= pair_number <= 8:
            # Sub-Survey 2: Second-Year Choice
            # Option 1 = (B, Ideal), Option 2 = (B, C)
            # Choosing Option 1 means preferring Ideal Year 2
            if user_choice == 1:
                sub2_ideal_count += 1
        elif 9 <= pair_number <= 12:
            # Sub-Survey 3: First-Year Choice
            # Option 1 = (Ideal, B), Option 2 = (C, B)
            # Choosing Option 1 means preferring Ideal Year 1
            if user_choice == 1:
                sub3_ideal_count += 1

    # Calculate percentages (4 questions per sub-survey)
    sub1_ideal_y1_percent = (sub1_ideal_count / 4) * 100
    sub2_ideal_y2_percent = (sub2_ideal_count / 4) * 100
    sub3_ideal_y1_percent = (sub3_ideal_count / 4) * 100

    return {
        "sub1_ideal_y1_percent": sub1_ideal_y1_percent,
        "sub2_ideal_y2_percent": sub2_ideal_y2_percent,
        "sub3_ideal_y1_percent": sub3_ideal_y1_percent,
    }


def _calculate_sub_survey_consistency_metrics(
    choices: List[Dict], sub_survey_num: int
) -> Dict[str, float]:
    """
    Calculate consistency metrics for a specific sub-survey of the dynamic temporal preference test.

    Args:
        choices: List of choices for a single user's dynamic temporal survey (12 choices)
        sub_survey_num: Sub-survey number (1, 2, or 3)

    Returns:
        Dict containing calculated metrics for the specific sub-survey:
        - ideal_percent: Percentage choosing the ideal option
        - alternative_percent: Percentage choosing the alternative option
        - consistency_percent: Max(ideal_count, alternative_count) * 25 (since 4 questions per sub-survey)
    """
    if not choices or len(choices) != 12:
        return {
            "ideal_percent": 0.0,
            "alternative_percent": 0.0,
            "consistency_percent": 0.0,
        }

    # Filter choices for the specific sub-survey
    if sub_survey_num == 1:
        # Sub-Survey 1: Simple Discounting (pairs 1-4)
        sub_choices = [c for c in choices if 1 <= c.get("pair_number", 0) <= 4]
    elif sub_survey_num == 2:
        # Sub-Survey 2: Second-Year Choice (pairs 5-8)
        sub_choices = [c for c in choices if 5 <= c.get("pair_number", 0) <= 8]
    elif sub_survey_num == 3:
        # Sub-Survey 3: First-Year Choice (pairs 9-12)
        sub_choices = [c for c in choices if 9 <= c.get("pair_number", 0) <= 12]
    else:
        return {
            "ideal_percent": 0.0,
            "alternative_percent": 0.0,
            "consistency_percent": 0.0,
        }

    if len(sub_choices) != 4:
        return {
            "ideal_percent": 0.0,
            "alternative_percent": 0.0,
            "consistency_percent": 0.0,
        }

    # Count ideal choices (Option 1 in all sub-surveys represents the ideal choice)
    ideal_count = sum(1 for choice in sub_choices if choice.get("user_choice") == 1)
    alternative_count = 4 - ideal_count

    # Calculate percentages
    ideal_percent = (ideal_count / 4) * 100
    alternative_percent = (alternative_count / 4) * 100

    # Consistency is max(ideal_count, alternative_count) * 25 (since max is 4, and 4*25=100)
    consistency_percent = max(ideal_count, alternative_count) * 25

    return {
        "ideal_percent": ideal_percent,
        "alternative_percent": alternative_percent,
        "consistency_percent": consistency_percent,
    }


def _generate_temporal_preference_table(choices: List[Dict]) -> str:
    """
    Generate HTML table for individual user's temporal preference results.

    Args:
        choices: List of choices for a single user's temporal preference survey

    Returns:
        str: HTML table showing user's temporal preference summary
    """
    if not choices:
        return ""

    metrics = _calculate_temporal_preference_metrics(choices)

    # Get translations
    title = get_translation("temporal_preference_summary", "answers")
    ideal_this_year_label = get_translation("ideal_this_year", "answers")
    ideal_next_year_label = get_translation("ideal_next_year", "answers")
    choice_label = get_translation("choice", "answers")
    percentage_label = get_translation("percentage", "answers")

    # Determine which choice is dominant for highlighting
    ideal_this_year_percent = metrics["ideal_this_year_percent"]
    ideal_next_year_percent = metrics["ideal_next_year_percent"]

    highlight_this_year = (
        "highlight-row" if ideal_this_year_percent > ideal_next_year_percent else ""
    )
    highlight_next_year = (
        "highlight-row" if ideal_next_year_percent > ideal_this_year_percent else ""
    )

    return f"""
    <div class="temporal-preference-summary">
        <h4 class="temporal-summary-title">{title}</h4>
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>{choice_label}</th>
                        <th>{percentage_label}</th>
                    </tr>
                </thead>
                <tbody>
                    <tr class="{highlight_this_year}">
                        <td>{ideal_this_year_label}</td>
                        <td>{ideal_this_year_percent:.1f}%</td>
                    </tr>
                    <tr class="{highlight_next_year}">
                        <td>{ideal_next_year_label}</td>
                        <td>{ideal_next_year_percent:.1f}%</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
    """


def _generate_dynamic_temporal_preference_table(choices: List[Dict]) -> str:
    """
    Generate HTML table for individual user's dynamic temporal preference results.

    Args:
        choices: List of choices for a single user's dynamic temporal survey (12 choices)

    Returns:
        str: HTML table showing user's dynamic temporal preference summary
    """
    if not choices:
        return ""

    metrics = _calculate_dynamic_temporal_metrics(choices)

    # Get translations
    title = get_translation(
        "dynamic_temporal_preference_summary",
        "answers",
        default="Dynamic Temporal Preference Summary",
    )
    choice_label = get_translation("choice", "answers")
    percentage_label = get_translation("percentage", "answers")

    # Sub-survey labels
    sub1_label = "S1: Simple Discounting - Ideal Year 1"
    sub2_label = "S2: Second-Year Choice - Ideal Year 2"
    sub3_label = "S3: First-Year Choice - Ideal Year 1"

    # Get percentages for highlighting
    sub1_percent = metrics["sub1_ideal_y1_percent"]
    sub2_percent = metrics["sub2_ideal_y2_percent"]
    sub3_percent = metrics["sub3_ideal_y1_percent"]

    # Determine highlighting (highlight if > 50%)
    highlight_sub1 = "highlight-row" if sub1_percent > 50 else ""
    highlight_sub2 = "highlight-row" if sub2_percent > 50 else ""
    highlight_sub3 = "highlight-row" if sub3_percent > 50 else ""

    return f"""
    <div class="dynamic-temporal-preference-summary">
        <h4 class="dynamic-temporal-summary-title">{title}</h4>
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>{choice_label}</th>
                        <th>{percentage_label}</th>
                    </tr>
                </thead>
                <tbody>
                    <tr class="{highlight_sub1}">
                        <td>{sub1_label}</td>
                        <td>{sub1_percent:.1f}%</td>
                    </tr>
                    <tr class="{highlight_sub2}">
                        <td>{sub2_label}</td>
                        <td>{sub2_percent:.1f}%</td>
                    </tr>
                    <tr class="{highlight_sub3}">
                        <td>{sub3_label}</td>
                        <td>{sub3_percent:.1f}%</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
    """


def _generate_temporal_sub_survey_tables(choices: List[Dict]) -> str:
    """
    Generate three separate styled HTML tables showing vote percentages for each
    temporal preference sub-survey.

    Args:
        choices: List of choices for a single user's temporal survey (12 choices)

    Returns:
        str: HTML containing three properly styled tables for each sub-survey
    """
    if not choices:
        return ""

    # Get translations
    sub1_title = get_translation("sub_survey_1_title", "answers")
    sub2_title = get_translation("sub_survey_2_title", "answers")
    sub3_title = get_translation("sub_survey_3_title", "answers")

    ideal_year_1_label = get_translation("ideal_year_1", "answers")
    ideal_year_2_label = get_translation("ideal_year_2", "answers")
    balanced_year_1_label = get_translation("balanced_year_1", "answers")
    balanced_year_2_label = get_translation("balanced_year_2", "answers")

    choice_label = get_translation("choice", "answers")
    percentage_label = get_translation("percentage", "answers")

    # Filter choices by sub-survey and count votes
    sub1_choices = [c for c in choices if 1 <= c.get("pair_number", 0) <= 4]
    sub2_choices = [c for c in choices if 5 <= c.get("pair_number", 0) <= 8]
    sub3_choices = [c for c in choices if 9 <= c.get("pair_number", 0) <= 12]

    html_parts = []

    # Sub-Survey 1: Simple Discounting
    if sub1_choices:
        total = len(sub1_choices)
        ideal_this_year_count = sum(
            1 for c in sub1_choices if c.get("user_choice") == 1
        )
        ideal_next_year_count = total - ideal_this_year_count

        ideal_this_year_pct = (ideal_this_year_count / total) * 100 if total > 0 else 0
        ideal_next_year_pct = (ideal_next_year_count / total) * 100 if total > 0 else 0

        html_parts.append(
            f"""
        <div class="summary-table-container">
            <h5>{sub1_title}</h5>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>{choice_label}</th>
                            <th>{percentage_label}</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>{ideal_year_1_label}</td>
                            <td>{ideal_this_year_pct:.1f}%</td>
                        </tr>
                        <tr>
                            <td>{ideal_year_2_label}</td>
                            <td>{ideal_next_year_pct:.1f}%</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>"""
        )

    # Sub-Survey 2: Second-Year Choice
    if sub2_choices:
        total = len(sub2_choices)
        ideal_year2_count = sum(1 for c in sub2_choices if c.get("user_choice") == 1)
        balanced_year2_count = total - ideal_year2_count

        ideal_year2_pct = (ideal_year2_count / total) * 100 if total > 0 else 0
        balanced_year2_pct = (balanced_year2_count / total) * 100 if total > 0 else 0

        html_parts.append(
            f"""
        <div class="summary-table-container">
            <h5>{sub2_title}</h5>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>{choice_label}</th>
                            <th>{percentage_label}</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>{ideal_year_2_label}</td>
                            <td>{ideal_year2_pct:.1f}%</td>
                        </tr>
                        <tr>
                            <td>{balanced_year_2_label}</td>
                            <td>{balanced_year2_pct:.1f}%</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>"""
        )

    # Sub-Survey 3: First-Year Choice
    if sub3_choices:
        total = len(sub3_choices)
        ideal_year1_count = sum(1 for c in sub3_choices if c.get("user_choice") == 1)
        balanced_year1_count = total - ideal_year1_count

        ideal_year1_pct = (ideal_year1_count / total) * 100 if total > 0 else 0
        balanced_year1_pct = (balanced_year1_count / total) * 100 if total > 0 else 0

        html_parts.append(
            f"""
        <div class="summary-table-container">
            <h5>{sub3_title}</h5>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>{choice_label}</th>
                            <th>{percentage_label}</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>{ideal_year_1_label}</td>
                            <td>{ideal_year1_pct:.1f}%</td>
                        </tr>
                        <tr>
                            <td>{balanced_year_1_label}</td>
                            <td>{balanced_year1_pct:.1f}%</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>"""
        )

    return "\n".join(html_parts)


def generate_consistency_breakdown_table(user_choices: List[Dict]) -> str:
    """
    Generate consistency breakdown table for temporal preference survey.

    Groups users by consistency level and shows the distribution of choices
    (Ideal This Year vs Ideal Next Year) for each consistency level.

    Args:
        user_choices: List of all user choices for the temporal preference survey

    Returns:
        str: HTML table showing choice distribution by consistency level
    """
    if not user_choices:
        no_data_msg = get_translation("no_answers", "answers")
        return f'<div class="no-data">{no_data_msg}</div>'

    # Group choices by user
    choices_by_user = {}
    for choice in user_choices:
        user_id = choice["user_id"]
        if user_id not in choices_by_user:
            choices_by_user[user_id] = []
        choices_by_user[user_id].append(choice)

    # Calculate metrics for each user and group by consistency level
    consistency_groups = {50: [], 60: [], 70: [], 80: [], 90: [], 100: []}

    for user_id, choices in choices_by_user.items():
        metrics = _calculate_temporal_preference_metrics(choices)
        consistency = metrics["consistency_percent"]

        # Round down to nearest 10 to get consistency level
        consistency_level = max(50, int(consistency // 10) * 10)
        if consistency_level in consistency_groups:
            # Store both metrics and user's actual choice percentages
            user_data = {
                "metrics": metrics,
                "ideal_this_year_percent": metrics["ideal_this_year_percent"],
                "ideal_next_year_percent": metrics["ideal_next_year_percent"],
            }
            consistency_groups[consistency_level].append(user_data)

    # Get translations
    title = get_translation("consistency_breakdown_title", "answers")
    consistency_level_label = get_translation("consistency_level", "answers")
    num_users_label = get_translation("num_of_users", "answers")
    ideal_this_year_label = get_translation("ideal_this_year", "answers")
    ideal_next_year_label = get_translation("ideal_next_year", "answers")

    # Generate table rows
    rows = []
    total_users = 0
    total_this_year_count = 0
    total_next_year_count = 0

    for consistency_level in sorted(consistency_groups.keys()):
        user_data_list = consistency_groups[consistency_level]
        num_users = len(user_data_list)

        if num_users == 0:
            continue

        total_users += num_users

        # Calculate average percentages across users at this consistency level
        this_year_percent = (
            sum(user_data["ideal_this_year_percent"] for user_data in user_data_list)
            / num_users
        )
        next_year_percent = (
            sum(user_data["ideal_next_year_percent"] for user_data in user_data_list)
            / num_users
        )

        # Update totals for overall calculation
        total_this_year_count += this_year_percent * num_users
        total_next_year_count += next_year_percent * num_users

        rows.append(
            f"""
            <tr>
                <td>{consistency_level}%</td>
                <td>{num_users}</td>
                <td>{this_year_percent:.1f}%</td>
                <td>{next_year_percent:.1f}%</td>
            </tr>
            """
        )

    if not rows:
        no_data_msg = get_translation("no_answers", "answers")
        return f'<div class="no-data">{no_data_msg}</div>'

    # Add total row
    if total_users > 0:
        overall_this_year_percent = total_this_year_count / total_users
        overall_next_year_percent = total_next_year_count / total_users

        total_label = get_translation("total", "answers")
        rows.append(
            f"""
            <tr class="total-row">
                <td><strong>{total_label}</strong></td>
                <td><strong>{total_users}</strong></td>
                <td><strong>{overall_this_year_percent:.1f}%</strong></td>
                <td><strong>{overall_next_year_percent:.1f}%</strong></td>
            </tr>
            """
        )

    return f"""
    <div class="summary-table-container consistency-breakdown-container">
        <h2>{title}</h2>
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>{consistency_level_label}</th>
                        <th>{num_users_label}</th>
                        <th>{ideal_this_year_label}</th>
                        <th>{ideal_next_year_label}</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </div>
    </div>
    """


def _generate_single_peaked_overall_consistency_table(
    summaries: List[Dict], title: str, note: str
) -> str:
    """
    Generate consistency breakdown table for multi-dimensional single-peaked surveys.
    """
    if not summaries:
        no_data_msg = get_translation("no_answers", "answers")
        return f"""
        <div class="summary-table-container">
            <h2>{title}</h2>
            <p class="summary-note">{no_data_msg}</p>
        </div>
        """

    bucket_stats: Dict[float, Dict[str, float]] = {}
    total_users = 0
    total_near_count = 0
    total_far_count = 0

    for summary in summaries:
        stats = summary.get("stats", {})
        near_count = stats.get("near_vector_count")
        far_count = stats.get("far_vector_count")
        near_percent = stats.get("near_vector_percent")
        far_percent = stats.get("far_vector_percent")
        consistency = stats.get("consistency_percent")

        if (
            near_count is None
            or far_count is None
            or near_percent is None
            or far_percent is None
            or consistency is None
        ):
            continue

        total_pairs = near_count + far_count
        if total_pairs <= 0:
            continue

        total_users += 1
        total_near_count += near_count
        total_far_count += far_count

        level = round(float(consistency), 1)
        level_bucket = bucket_stats.setdefault(
            level, {"users": 0, "near_sum": 0.0, "far_sum": 0.0}
        )
        level_bucket["users"] += 1
        level_bucket["near_sum"] += float(near_percent)
        level_bucket["far_sum"] += float(far_percent)

    if total_users == 0:
        no_data_msg = get_translation("no_answers", "answers")
        return f"""
        <div class="summary-table-container">
            <h2>{title}</h2>
            <p class="summary-note">{no_data_msg}</p>
        </div>
        """

    consistency_level_label = get_translation("consistency_level", "answers")
    num_users_label = get_translation("num_of_users", "answers")
    far_label = get_translation("far_vector", "answers")
    near_label = get_translation("near_vector", "answers")

    rows: List[str] = []
    for level in sorted(bucket_stats.keys()):
        level_data = bucket_stats[level]
        users = level_data["users"]
        avg_near = level_data["near_sum"] / users if users else 0.0
        avg_far = level_data["far_sum"] / users if users else 0.0

        far_class = ' class="highlight-cell"' if avg_far > avg_near else ""
        near_class = ' class="highlight-cell"' if avg_near > avg_far else ""

        rows.append(
            f"""
            <tr>
                <td>{level:.1f}%</td>
                <td>{users}</td>
                <td{far_class}>{avg_far:.1f}%</td>
                <td{near_class}>{avg_near:.1f}%</td>
            </tr>
            """
        )

    total_label = get_translation("total", "answers")
    all_pairs = total_near_count + total_far_count
    overall_far = (total_far_count / all_pairs) * 100 if all_pairs else 0.0
    overall_near = (total_near_count / all_pairs) * 100 if all_pairs else 0.0

    far_total_class = ' class="highlight-cell"' if overall_far > overall_near else ""
    near_total_class = ' class="highlight-cell"' if overall_near > overall_far else ""

    rows.append(
        f"""
        <tr class="total-row">
            <td><strong>{total_label}</strong></td>
            <td><strong>{total_users}</strong></td>
            <td{far_total_class}><strong>{overall_far:.1f}%</strong></td>
            <td{near_total_class}><strong>{overall_near:.1f}%</strong></td>
        </tr>
        """
    )

    return f"""
    <div class="summary-table-container consistency-breakdown-container">
        <h2>{title}</h2>
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>{consistency_level_label}</th>
                        <th>{num_users_label}</th>
                        <th>{far_label}</th>
                        <th>{near_label}</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </div>
        <p class="summary-note">{note}</p>
    </div>
    """


def _generate_triangle_overall_consistency_table(
    summaries: List[Dict], title: str, note: str
) -> str:
    """Generate consistency breakdown table for triangle inequality surveys."""
    if not summaries:
        no_data_msg = get_translation("no_answers", "answers")
        return f"""
        <div class="summary-table-container">
            <h2>{title}</h2>
            <p class="summary-note">{no_data_msg}</p>
        </div>
        """

    # Define the possible consistency levels based on 12 binary choices
    level_percentages = [50.0, 58.3, 66.7, 75.0, 83.3, 91.7, 100.0]
    bucket_data = {level: [] for level in level_percentages}

    for summary in summaries:
        stats = summary.get("stats", {})
        concentrated_count = stats.get("concentrated_count")
        distributed_count = stats.get("distributed_count")
        concentrated_percent = stats.get("concentrated_percent")
        distributed_percent = stats.get("distributed_percent")
        consistency_percent = stats.get("consistency_percent")

        if (
            concentrated_count is None
            or distributed_count is None
            or concentrated_percent is None
            or distributed_percent is None
            or consistency_percent is None
        ):
            continue

        total_choices = concentrated_count + distributed_count
        if total_choices <= 0:
            continue

        consistency_percent = float(consistency_percent)
        if consistency_percent <= 0:
            continue

        target_level = min(
            level_percentages, key=lambda level: abs(level - consistency_percent)
        )

        # Skip obviously mismatched data (e.g., users without enough answers)
        if abs(target_level - consistency_percent) > 12:
            continue

        bucket_data[target_level].append(
            {
                "concentrated_percent": float(concentrated_percent),
                "distributed_percent": float(distributed_percent),
            }
        )

    rows = []
    total_users = 0
    total_concentrated_weighted = 0.0
    total_distributed_weighted = 0.0

    for level in level_percentages:
        user_stats = bucket_data[level]
        if not user_stats:
            continue

        num_users = len(user_stats)
        total_users += num_users

        avg_concentrated = (
            sum(item["concentrated_percent"] for item in user_stats) / num_users
        )
        avg_distributed = (
            sum(item["distributed_percent"] for item in user_stats) / num_users
        )

        total_concentrated_weighted += avg_concentrated * num_users
        total_distributed_weighted += avg_distributed * num_users

        concentrated_class_attr = (
            ' class="highlight-cell"' if avg_concentrated > avg_distributed else ""
        )
        distributed_class_attr = (
            ' class="highlight-cell"' if avg_distributed > avg_concentrated else ""
        )

        rows.append(
            f"""
            <tr>
                <td>{level:.1f}%</td>
                <td>{num_users}</td>
                <td{concentrated_class_attr}>{avg_concentrated:.1f}%</td>
                <td{distributed_class_attr}>{avg_distributed:.1f}%</td>
            </tr>
            """
        )

    if not rows:
        no_data_msg = get_translation("no_answers", "answers")
        return f"""
        <div class="summary-table-container">
            <h2>{title}</h2>
            <p class="summary-note">{no_data_msg}</p>
        </div>
        """

    consistency_level_label = get_translation("consistency_level", "answers")
    num_users_label = get_translation("num_of_users", "answers")
    concentrated_label = get_translation(
        "triangle_concentrated", "answers", default="Concentrated Change"
    )
    distributed_label = get_translation(
        "triangle_distributed", "answers", default="Distributed Change"
    )

    # Append total row with weighted averages
    if total_users > 0:
        overall_concentrated = total_concentrated_weighted / total_users
        overall_distributed = total_distributed_weighted / total_users
        total_label = get_translation("total", "answers")

        concentrated_total_class = (
            ' class="highlight-cell"'
            if overall_concentrated > overall_distributed
            else ""
        )
        distributed_total_class = (
            ' class="highlight-cell"'
            if overall_distributed > overall_concentrated
            else ""
        )

        rows.append(
            f"""
            <tr class="total-row">
                <td><strong>{total_label}</strong></td>
                <td><strong>{total_users}</strong></td>
                <td{concentrated_total_class}><strong>{overall_concentrated:.1f}%</strong></td>
                <td{distributed_total_class}><strong>{overall_distributed:.1f}%</strong></td>
            </tr>
            """
        )

    return f"""
    <div class="summary-table-container consistency-breakdown-container">
        <h2>{title}</h2>
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>{consistency_level_label}</th>
                        <th>{num_users_label}</th>
                        <th>{concentrated_label}</th>
                        <th>{distributed_label}</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </div>
        <p class="summary-note">{note}</p>
    </div>
    """


def _generate_rank_overall_consistency_table(
    summaries: List[Dict],
    title: str,
    note: str,
    option_labels: Tuple[str, str],
) -> str:
    """Generate consistency breakdown table for rank-based L1 vs Leontief strategy."""
    if not summaries:
        no_data_msg = get_translation("no_answers", "answers")
        return f"""
        <div class="summary-table-container">
            <h2>{title}</h2>
            <p class="summary-note">{no_data_msg}</p>
        </div>
        """

    # Bucket by observed consistency percentages (rounded to 1 decimal)
    bucket_data: Dict[float, List[Dict[str, float]]] = {}

    for summary in summaries:
        stats = summary.get("stats", {})
        sum_count = stats.get("sum_count")
        ratio_count = stats.get("ratio_count")
        sum_percent = stats.get("sum_percent")
        ratio_percent = stats.get("ratio_percent")
        consistency_percent = stats.get("consistency_percent")

        if (
            sum_count is None
            or ratio_count is None
            or sum_percent is None
            or ratio_percent is None
            or consistency_percent is None
        ):
            continue

        total_choices = sum_count + ratio_count
        if total_choices <= 0:
            continue

        level = round(float(consistency_percent), 1)
        bucket_data.setdefault(level, []).append(
            {"sum_percent": float(sum_percent), "ratio_percent": float(ratio_percent)}
        )

    if not bucket_data:
        no_data_msg = get_translation("no_answers", "answers")
        return f"""
        <div class="summary-table-container">
            <h2>{title}</h2>
            <p class="summary-note">{no_data_msg}</p>
        </div>
        """

    rows = []
    total_users = 0
    total_sum_weighted = 0.0
    total_ratio_weighted = 0.0

    for level in sorted(bucket_data.keys()):
        user_stats = bucket_data[level]
        num_users = len(user_stats)
        total_users += num_users

        avg_sum = sum(item["sum_percent"] for item in user_stats) / num_users
        avg_ratio = sum(item["ratio_percent"] for item in user_stats) / num_users

        total_sum_weighted += avg_sum * num_users
        total_ratio_weighted += avg_ratio * num_users

        sum_class_attr = ' class="highlight-cell"' if avg_sum > avg_ratio else ""
        ratio_class_attr = ' class="highlight-cell"' if avg_ratio > avg_sum else ""

        rows.append(
            f"""
            <tr>
                <td>{level:.1f}%</td>
                <td>{num_users}</td>
                <td{sum_class_attr}>{avg_sum:.1f}%</td>
                <td{ratio_class_attr}>{avg_ratio:.1f}%</td>
            </tr>
            """
        )

    if total_users > 0:
        overall_sum = total_sum_weighted / total_users
        overall_ratio = total_ratio_weighted / total_users
        total_label = get_translation("total", "answers")

        sum_total_class = (
            ' class="highlight-cell"' if overall_sum > overall_ratio else ""
        )
        ratio_total_class = (
            ' class="highlight-cell"' if overall_ratio > overall_sum else ""
        )

        rows.append(
            f"""
            <tr class="total-row">
                <td><strong>{total_label}</strong></td>
                <td><strong>{total_users}</strong></td>
                <td{sum_total_class}><strong>{overall_sum:.1f}%</strong></td>
                <td{ratio_total_class}><strong>{overall_ratio:.1f}%</strong></td>
            </tr>
            """
        )

    consistency_level_label = get_translation("consistency_level", "answers")
    num_users_label = get_translation("num_of_users", "answers")
    sum_label = option_labels[0] if option_labels else get_translation("sum", "answers")
    ratio_label = (
        option_labels[1] if option_labels else get_translation("ratio", "answers")
    )

    return f"""
    <div class="summary-table-container consistency-breakdown-container">
        <h2>{title}</h2>
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>{consistency_level_label}</th>
                        <th>{num_users_label}</th>
                        <th>{sum_label}</th>
                        <th>{ratio_label}</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </div>
        <p class="summary-note">{note}</p>
    </div>
    """


def _generate_sub_survey_consistency_breakdown_table(
    user_choices: List[Dict],
    sub_survey_num: int,
    title: str,
    ideal_label: str,
    alternative_label: str,
) -> str:
    """
    Generate consistency breakdown table for a specific sub-survey of the dynamic temporal preference test.

    Args:
        user_choices: List of all user choices for the dynamic temporal preference survey
        sub_survey_num: Sub-survey number (1, 2, or 3)
        title: Title for the table
        ideal_label: Label for the ideal choice column
        alternative_label: Label for the alternative choice column

    Returns:
        str: HTML table showing choice distribution by consistency level for the sub-survey
    """
    if not user_choices:
        no_data_msg = get_translation("no_answers", "answers")
        return f'<div class="no-data">{no_data_msg}</div>'

    # Group choices by user
    choices_by_user = {}
    for choice in user_choices:
        user_id = choice["user_id"]
        if user_id not in choices_by_user:
            choices_by_user[user_id] = []
        choices_by_user[user_id].append(choice)

    # Calculate metrics for each user and group by consistency level
    consistency_groups = {50: [], 75: [], 100: []}

    for user_id, choices in choices_by_user.items():
        if len(choices) != 12:  # Skip users without complete responses
            continue

        metrics = _calculate_sub_survey_consistency_metrics(choices, sub_survey_num)
        consistency = metrics["consistency_percent"]

        # Round down to nearest 25 to get consistency level (since we have 4 questions: 25%, 50%, 75%, 100%)
        if consistency >= 100:
            consistency_level = 100
        elif consistency >= 75:
            consistency_level = 75
        else:
            consistency_level = 50

        if consistency_level in consistency_groups:
            # Store both metrics and user's actual choice percentages
            user_data = {
                "metrics": metrics,
                "ideal_percent": metrics["ideal_percent"],
                "alternative_percent": metrics["alternative_percent"],
            }
            consistency_groups[consistency_level].append(user_data)

    # Get translations
    consistency_level_label = get_translation("consistency_level", "answers")
    num_users_label = get_translation("num_of_users", "answers")

    # Generate table rows
    rows = []
    total_users = 0
    total_ideal_count = 0
    total_alternative_count = 0

    for consistency_level in sorted(consistency_groups.keys()):
        user_data_list = consistency_groups[consistency_level]
        num_users = len(user_data_list)

        if num_users == 0:
            continue

        total_users += num_users

        # Calculate average percentages across users at this consistency level
        ideal_percent = (
            sum(user_data["ideal_percent"] for user_data in user_data_list) / num_users
        )
        alternative_percent = (
            sum(user_data["alternative_percent"] for user_data in user_data_list)
            / num_users
        )

        # Update totals for overall calculation
        total_ideal_count += ideal_percent * num_users
        total_alternative_count += alternative_percent * num_users

        rows.append(
            f"""
            <tr>
                <td>{consistency_level}%</td>
                <td>{num_users}</td>
                <td>{ideal_percent:.1f}%</td>
                <td>{alternative_percent:.1f}%</td>
            </tr>
            """
        )

    if not rows:
        no_data_msg = get_translation("no_answers", "answers")
        return f'<div class="no-data">{no_data_msg}</div>'

    # Add total row
    if total_users > 0:
        overall_ideal_percent = total_ideal_count / total_users
        overall_alternative_percent = total_alternative_count / total_users

        total_label = get_translation("total", "answers")
        rows.append(
            f"""
            <tr class="total-row">
                <td><strong>{total_label}</strong></td>
                <td><strong>{total_users}</strong></td>
                <td><strong>{overall_ideal_percent:.1f}%</strong></td>
                <td><strong>{overall_alternative_percent:.1f}%</strong></td>
            </tr>
            """
        )

    return f"""
    <div class="summary-table-container consistency-breakdown-container">
        <h2>{title}</h2>
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>{consistency_level_label}</th>
                        <th>{num_users_label}</th>
                        <th>{ideal_label}</th>
                        <th>{alternative_label}</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </div>
    </div>
    """


def generate_dynamic_temporal_consistency_breakdown_tables(
    user_choices: List[Dict],
) -> str:
    """
    Generate three consistency breakdown tables for the dynamic temporal preference survey.

    Args:
        user_choices: List of all user choices for the dynamic temporal preference survey

    Returns:
        str: HTML containing three consistency breakdown tables for each sub-survey
    """
    if not user_choices:
        no_data_msg = get_translation("no_answers", "answers")
        return f'<div class="no-data">{no_data_msg}</div>'

    # Get translations for sub-survey titles and labels
    sub1_title = get_translation("sub_survey_1_title", "answers")
    sub2_title = get_translation("sub_survey_2_title", "answers")
    sub3_title = get_translation("sub_survey_3_title", "answers")

    # Labels for each sub-survey
    ideal_year_1_label = get_translation("ideal_year_1", "answers")
    ideal_year_2_label = get_translation("ideal_year_2", "answers")
    balanced_year_1_label = get_translation("balanced_year_1", "answers")
    balanced_year_2_label = get_translation("balanced_year_2", "answers")
    random_label = get_translation("random", "answers")

    # Generate the three tables
    sub1_table = _generate_sub_survey_consistency_breakdown_table(
        user_choices, 1, sub1_title, ideal_year_1_label, random_label
    )

    sub2_table = _generate_sub_survey_consistency_breakdown_table(
        user_choices, 2, sub2_title, ideal_year_2_label, balanced_year_2_label
    )

    sub3_table = _generate_sub_survey_consistency_breakdown_table(
        user_choices, 3, sub3_title, ideal_year_1_label, balanced_year_1_label
    )

    return f"""
    <div class="dynamic-temporal-consistency-breakdown">
        {sub1_table}
        {sub2_table}
        {sub3_table}
    </div>
    """


def _calculate_final_consistency_score(deduced_data: Dict) -> int:
    """Calculates the final consistency score from deduced ranking data."""
    if not deduced_data or "pairwise" not in deduced_data:
        return 0

    magnitudes = deduced_data["magnitudes"]
    x1_mag, x2_mag = magnitudes
    pairwise_prefs = deduced_data["pairwise"]
    final_cons_score = 0
    for pt in pairwise_prefs:
        prefs = [
            pairwise_prefs[pt][x1_mag]["+"],
            pairwise_prefs[pt][x1_mag]["–"],
            pairwise_prefs[pt][x2_mag]["+"],
            pairwise_prefs[pt][x2_mag]["–"],
        ]
        if len(set(prefs)) == 1:
            final_cons_score += 1
    return final_cons_score


def _calculate_single_peaked_metrics(choices: List[Dict]) -> Dict[str, float]:
    """
    Calculate multi-dimensional single-peaked metrics for a user's responses.

    Determines how often respondents selected the vector closer to their peak
    (near vector) versus the further vector, and derives consistency levels.
    """
    if not choices:
        return {
            "near_vector_count": 0,
            "far_vector_count": 0,
            "near_vector_percent": 0.0,
            "far_vector_percent": 0.0,
            "consistency_percent": 0.0,
            "total_pairs": 0,
        }

    near_count = 0
    far_count = 0

    for choice in choices:
        try:
            optimal_raw = choice.get("optimal_allocation")
            option1_raw = choice.get("option_1")
            option2_raw = choice.get("option_2")
            user_choice = choice.get("user_choice")

            if user_choice not in (1, 2):
                continue

            if isinstance(optimal_raw, (list, tuple)):
                optimal = [int(v) for v in optimal_raw]
            else:
                optimal = list(json.loads(optimal_raw))

            if isinstance(option1_raw, (list, tuple)):
                option_1 = [int(v) for v in option1_raw]
            else:
                option_1 = list(json.loads(option1_raw))

            if isinstance(option2_raw, (list, tuple)):
                option_2 = [int(v) for v in option2_raw]
            else:
                option_2 = list(json.loads(option2_raw))

            if not (optimal and option_1 and option_2):
                continue
            if len(optimal) != len(option_1) or len(optimal) != len(option_2):
                continue

            dist_1 = sum(abs(o1 - opt) for o1, opt in zip(option_1, optimal))
            dist_2 = sum(abs(o2 - opt) for o2, opt in zip(option_2, optimal))

            if dist_1 == dist_2:
                # Ambiguous pair; skip to avoid misclassification
                continue

            near_option = 1 if dist_1 < dist_2 else 2

            if user_choice == near_option:
                near_count += 1
            else:
                far_count += 1
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            logger.debug("Failed to process MDSP choice for metrics: %s", exc)
            continue

    total_pairs = near_count + far_count
    if total_pairs == 0:
        return {
            "near_vector_count": 0,
            "far_vector_count": 0,
            "near_vector_percent": 0.0,
            "far_vector_percent": 0.0,
            "consistency_percent": 0.0,
            "total_pairs": 0,
        }

    near_percent = (near_count / total_pairs) * 100
    far_percent = (far_count / total_pairs) * 100

    return {
        "near_vector_count": near_count,
        "far_vector_count": far_count,
        "near_vector_percent": round(near_percent, 1),
        "far_vector_percent": round(far_percent, 1),
        "consistency_percent": round(max(near_percent, far_percent), 1),
        "total_pairs": total_pairs,
    }


def _calculate_triangle_inequality_metrics(choices: List[Dict]) -> Dict[str, float]:
    """
    Calculate triangle inequality test metrics for a single user's response.

    Analyzes whether users prefer concentrated changes (entire deviation in one year)
    or distributed changes (deviation split across two years).

    Args:
        choices: List of 12 choices for triangle inequality survey

    Returns:
        Dict with:
            - concentrated_count: Number of times user chose concentrated
            - distributed_count: Number of times user chose distributed
            - concentrated_percent: Percentage choosing concentrated
            - distributed_percent: Percentage choosing distributed
            - consistency_percent: Consistency score (how often user made same choice type)
    """
    if not choices or len(choices) != 12:
        return {
            "concentrated_count": 0,
            "distributed_count": 0,
            "concentrated_percent": 0.0,
            "distributed_percent": 0.0,
            "consistency_percent": 0.0,
        }

    concentrated_count = 0
    distributed_count = 0

    for choice in choices:
        chosen_option = choice.get("user_choice")
        option1_strategy = choice.get("option1_strategy", "")
        option2_strategy = choice.get("option2_strategy", "")

        # Determine what type was chosen
        if chosen_option == 1:
            chosen_strategy = option1_strategy
        else:
            chosen_strategy = option2_strategy

        if "Concentrated" in chosen_strategy:
            concentrated_count += 1
        elif "Distributed" in chosen_strategy:
            distributed_count += 1

    total = concentrated_count + distributed_count
    if total == 0:
        concentrated_percent = 0.0
        distributed_percent = 0.0
        consistency_percent = 0.0
    else:
        concentrated_percent = (concentrated_count / total) * 100
        distributed_percent = (distributed_count / total) * 100

        # Consistency: percentage of most frequent choice
        consistency_percent = max(concentrated_percent, distributed_percent)

    return {
        "concentrated_count": concentrated_count,
        "distributed_count": distributed_count,
        "concentrated_percent": round(concentrated_percent, 1),
        "distributed_percent": round(distributed_percent, 1),
        "consistency_percent": round(consistency_percent, 1),
    }


def _calculate_rank_consistency_metrics(choices: List[Dict]) -> Dict[str, float]:
    """
    Calculate per-user consistency for rank-based L1 vs Leontief strategy.

    Consistency is defined as the percentage of the dominant choice type
    (Sum vs Ratio) across all answered pairs.
    """
    if not choices:
        return {
            "sum_count": 0,
            "ratio_count": 0,
            "sum_percent": 0.0,
            "ratio_percent": 0.0,
            "consistency_percent": 0.0,
        }

    sum_count = 0
    ratio_count = 0

    for choice in choices:
        chosen_option = choice.get("user_choice")
        option1_strategy = choice.get("option1_strategy", "") or ""
        option2_strategy = choice.get("option2_strategy", "") or ""

        chosen_strategy = option1_strategy if chosen_option == 1 else option2_strategy
        chosen_lower = chosen_strategy.lower()

        if "sum" in chosen_lower:
            sum_count += 1
        elif "ratio" in chosen_lower:
            ratio_count += 1

    total = sum_count + ratio_count
    if total == 0:
        return {
            "sum_count": 0,
            "ratio_count": 0,
            "sum_percent": 0.0,
            "ratio_percent": 0.0,
            "consistency_percent": 0.0,
        }

    sum_percent = (sum_count / total) * 100
    ratio_percent = (ratio_count / total) * 100

    return {
        "sum_count": sum_count,
        "ratio_count": ratio_count,
        "sum_percent": round(sum_percent, 1),
        "ratio_percent": round(ratio_percent, 1),
        "consistency_percent": round(max(sum_percent, ratio_percent), 1),
    }


def _generate_triangle_inequality_table(choices: List[Dict]) -> str:
    """
    Generate HTML table for triangle inequality test results.

    Args:
        choices: List of choices for a single user's triangle inequality survey

    Returns:
        str: HTML table showing user's preference pattern
    """
    if not choices:
        return ""

    metrics = _calculate_triangle_inequality_metrics(choices)

    # Get translations
    title = get_translation(
        "triangle_analysis_title",
        "answers",
        default="Triangle Inequality Analysis",
    )
    concentrated_label = get_translation(
        "triangle_concentrated",
        "answers",
        default="Concentrated Change",
    )
    distributed_label = get_translation(
        "triangle_distributed",
        "answers",
        default="Distributed Change",
    )
    consistency_label = get_translation(
        "triangle_consistency",
        "answers",
        default="Consistency",
    )

    concentrated_pct = metrics["concentrated_percent"]
    distributed_pct = metrics["distributed_percent"]
    consistency_pct = metrics["consistency_percent"]

    # Determine dominant preference for highlighting
    if concentrated_pct > distributed_pct:
        concentrated_class = "highlight-cell"
        distributed_class = ""
        preference_text = get_translation(
            "prefers_concentrated",
            "answers",
            default="Prefers Concentrated",
        )
    else:
        concentrated_class = ""
        distributed_class = "highlight-cell"
        preference_text = get_translation(
            "prefers_distributed",
            "answers",
            default="Prefers Distributed",
        )

    # Consistency highlighting
    consistency_class = "highlight-cell" if consistency_pct >= 75 else ""

    # Get explanation text
    explanation = get_translation(
        "triangle_explanation",
        "answers",
        default="This table shows your preferences between concentrated changes (all change in one year) versus distributed changes (changes across both years).",
    )

    table_html = f"""
    <div class="analysis-table-container triangle-inequality-analysis">
        <h4>{title}</h4>
        <p class="analysis-explanation">{explanation}</p>
        <div class="preference-summary-badge {concentrated_class if concentrated_pct > distributed_pct else distributed_class}">
            {preference_text}
        </div>
        <table class="analysis-table">
            <thead>
                <tr>
                    <th>{concentrated_label}</th>
                    <th>{distributed_label}</th>
                    <th>{consistency_label}</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td class="{concentrated_class}">{concentrated_pct}%</td>
                    <td class="{distributed_class}">{distributed_pct}%</td>
                    <td class="{consistency_class}">{consistency_pct}%</td>
                </tr>
            </tbody>
        </table>
    </div>
    """

    return table_html


if __name__ == "__main__":
    # Basic usage example - requires actual data loading for full test
    print("Report content generator module.")
    # Example: Load data into DataFrames (summary_stats, optimization_stats, responses_df)
    # then call functions like generate_executive_summary(summary_stats, optimization_stats, responses_df)
    # and generate_detailed_user_choices(user_choices_list)
