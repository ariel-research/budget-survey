"""
This module handles HTML rendering for the web-based report system.
It accepts survey data (raw choices or pre-calculated statistics) and returns formatted HTML strings.
"""

import html
import json
import logging
from typing import Dict, List, Optional, Tuple

from analysis.logic.stats_calculators import (
    calculate_choice_statistics,
    calculate_cyclic_shift_group_consistency,
    calculate_dynamic_temporal_metrics,
    calculate_final_consistency_score,
    calculate_linear_symmetry_group_consistency,
    calculate_sub_survey_consistency_metrics,
    calculate_temporal_preference_metrics,
    calculate_triangle_inequality_metrics,
    deduce_rankings,
    extract_extreme_vector_preferences,
    generate_single_user_asymmetric_matrix_data,
)
from analysis.transitivity_analyzer import TransitivityAnalyzer
from analysis.utils import is_sum_optimized
from application.translations import get_translation

logger = logging.getLogger(__name__)


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

    # Generate metadata section for rank comparison strategies
    metadata_html = ""
    if (
        strategy_name
        and strategy_name.endswith("_rank_comparison")
        and choice.get("generation_metadata")
        and isinstance(choice.get("generation_metadata"), dict)
        and "score" in choice.get("generation_metadata", {})
    ):
        score = choice["generation_metadata"]["score"]
        score_label = get_translation("pair_score", "answers")

        # Extract model names for the explanation if possible
        model_a, model_b = "Model A", "Model B"
        parts = strategy_name.replace("_rank_comparison", "").split("_vs_")
        if len(parts) == 2:

            def format_model_name(name: str) -> str:
                if len(name) <= 2:
                    return name.upper()
                return name.replace("_", " ").title()

            model_a = format_model_name(parts[0])
            model_b = format_model_name(parts[1])

        score_explanation = get_translation(
            "pair_score_explanation", "answers", model_a=model_a, model_b=model_b
        )
        metadata_html = f"""
        <div class="pair-metadata">
            <div class="pair-metadata-content">
                <span class="pair-metadata-label">{score_label}:</span>
                <span class="pair-metadata-value">{score:.2f}</span>
            </div>
            <div class="pair-metadata-explanation">{score_explanation}</div>
        </div>
        """

    return f"""
    <div class="choice-pair">
        <div class="pair-header">
            <h5>{header_content}</h5>
        </div>
        <div class="raw-choice-info">
            {raw_choice_html}
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
    ) = extract_extreme_vector_preferences(choices)

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


def generate_survey_choices_html(
    survey_id: int,
    choices: List[Dict],
    option_labels: Tuple[str, str],
    strategy_name: str = None,
    subjects: List[str] = None,
) -> str:
    """Generate HTML for choices made in a single survey.
    Args:
        survey_id: ID of the survey
        choices: List of choices for a single survey
        option_labels: Labels for the two options
        strategy_name: Name of the strategy used for the survey
        subjects: List of subjects for this survey (optional).
    Returns:
        str: HTML for the survey choices
    """
    if not choices:
        return ""

    # Get survey-specific option labels if available
    survey_labels = choices[0].get("strategy_labels", option_labels)

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
        matrix_html = _generate_single_user_asymmetric_matrix_table(
            choices, survey_id, subjects
        )
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


def generate_extreme_vector_analysis_table(choices: List[Dict]) -> str:
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
    ) = extract_extreme_vector_preferences(choices)

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


def _generate_single_user_asymmetric_matrix_table(
    choices: List[Dict], survey_id: int, subjects: List[str] = None
) -> str:
    """Generate HTML matrix table for single user's asymmetric responses."""
    data = generate_single_user_asymmetric_matrix_data(choices, survey_id, subjects)
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
    final_cons_score = calculate_final_consistency_score(deduced_data)

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

    deduced_data = deduce_rankings(choices)
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
        _, _, _, _, percentile_data = extract_extreme_vector_preferences(choices)

        # Add to aggregated totals
        for percentile in [25, 50, 75]:
            for group in ["A_vs_B", "A_vs_C", "B_vs_C"]:
                # percentile_data from extract_extreme_vector_preferences is [total, match]
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


def generate_detailed_breakdown_table(
    summaries: List[Dict],
    option_labels: Tuple[str, str],
    strategy_name: str = None,
    sort_by: str = None,
    sort_order: str = "asc",
) -> str:
    """
    Generate detailed breakdown tables grouped by survey.
    Refactored to be generic and data-driven.
    """
    if not summaries:
        return ""

    from application.services.pair_generation.base import StrategyRegistry

    # 1. Group summaries by survey
    survey_groups = {}
    for summary in summaries:
        survey_groups.setdefault(summary["survey_id"], []).append(summary)

    tables = []

    for survey_id in sorted(survey_groups.keys()):
        survey_summaries = survey_groups[survey_id]

        # 2. Determine Strategy and Columns
        current_strategy_name = strategy_name
        if survey_summaries and "strategy_name" in survey_summaries[0]:
            current_strategy_name = survey_summaries[0]["strategy_name"]

        strategy_columns = {}
        if current_strategy_name:
            try:
                strategy = StrategyRegistry.get_strategy(current_strategy_name)
                strategy_columns = strategy.get_table_columns()
            except (ValueError, AttributeError) as e:
                logger.warning(f"Error getting strategy columns: {e}")

        # Fallback columns if strategy didn't provide them
        if not strategy_columns:
            # Use option labels or defaults
            l1 = option_labels[0] if option_labels else "Option 1"
            l2 = option_labels[1] if len(option_labels) > 1 else "Option 2"
            strategy_columns = {
                "option1": {"name": l1, "type": "percentage"},
                "option2": {"name": l2, "type": "percentage"},
            }

        # 3. Sort Logic
        key_map = {"user_id": "user_id", "created_at": "response_created_at"}
        sort_key = key_map.get(sort_by, "response_created_at")
        reverse = (sort_order.lower() == "desc") if sort_by else True

        sorted_summaries = sorted(
            survey_summaries, key=lambda x: x.get(sort_key, "") or "", reverse=reverse
        )

        # 4. Generate Rows
        rows = []
        for summary in sorted_summaries:
            user_id = summary["user_id"]
            display_id, is_truncated = _format_user_id(user_id)

            # Links & Metadata
            links = {
                "all": f"/surveys/users/{user_id}/responses",
                "survey": f"/surveys/{survey_id}/users/{user_id}/responses",
            }

            timestamp = _format_timestamp(summary.get("response_created_at"))
            ideal_budget = _format_ideal_budget(summary.get("choices", []))

            # Generic Cell Generation
            data_cells = _generate_strategy_data_cells(summary, strategy_columns)

            # View Response Button
            view_cell = f"""
                <td>
                    <a href="{links['survey']}" class="survey-response-link" target="_blank">
                        {get_translation('view_response', 'answers')}
                    </a>
                </td>
            """

            # Construct Row
            tooltip = (
                f'<span class="user-id-tooltip">{user_id}</span>'
                if is_truncated
                else ""
            )
            rows.append(
                f"""
            <tr>
                <td class="user-id-cell{' truncated' if is_truncated else ''}">
                    <a href="{links['all']}" class="user-link" target="_blank">{display_id}</a>
                    {tooltip}
                </td>
                <td>{timestamp}</td>
                <td class="ideal-budget-cell">{ideal_budget}</td>
                {"".join(data_cells)}
                {view_cell}
            </tr>
            """
            )

        # 5. Generate Table Header
        header_cells = [f'<th>{col["name"]}</th>' for col in strategy_columns.values()]

        # Sorting attributes
        def get_sort_attr(col_name):
            if sort_by == col_name:
                return f' data-order="{"desc" if sort_order == "asc" else "asc"}"'
            return ' data-order="desc"'

        # Translations
        trans = {
            "title": get_translation("survey_response_breakdown", "answers"),
            "user": get_translation("user_id", "answers"),
            "time": get_translation("response_time", "answers"),
            "budget": get_translation("ideal_budget", "answers"),
            "view": get_translation("view_response", "answers"),
        }

        table = f"""
        <div class="summary-table-container">
            <h2>{trans['title']} - Survey {survey_id}</h2>
            <div class="table-container detailed-breakdown">
                <table>
                    <thead>
                        <tr>
                            <th class="sortable" data-sort="user_id"{get_sort_attr('user_id')}>{trans['user']}</th>
                            <th class="sortable" data-sort="created_at"{get_sort_attr('created_at')}>{trans['time']}</th>
                            <th>{trans['budget']}</th>
                            {"".join(header_cells)}
                            <th>{trans['view']}</th>
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


def _generate_strategy_data_cells(summary: Dict, columns: Dict) -> List[str]:
    """
    Helper to generate HTML cells for strategy metrics.
    Handles value extraction, calculation, and highlighting logic.
    """
    stats = summary.get("stats", {})
    col_keys = list(columns.keys())
    values = {}

    # 1. Extract Values
    for index, col_key in enumerate(col_keys):
        val = 0.0

        # Special Case: RSS Calculation (Legacy)
        if col_key == "rss":
            if "sum_percent" in stats:
                val = 100.0 - stats["sum_percent"]
            elif "ratio_percent" in stats:
                val = 100.0 - stats["ratio_percent"]

        # Special Case: Triangle Inequality Key Mapping
        # Strategy uses 'concentrated_preference', calculator uses 'concentrated_percent'
        elif col_key == "concentrated_preference":
            val = stats.get("concentrated_percent", 0.0)
        elif col_key == "distributed_preference":
            val = stats.get("distributed_percent", 0.0)
        elif col_key == "triangle_consistency":
            val = stats.get("consistency_percent", 0.0)

        # Special Case: Generic Rank Fallback (The Bug Fix)
        elif (
            f"{col_key}_percent" not in stats
            and f"metric_{chr(97+index)}_percent" in stats
        ):
            # metric_a is index 0, metric_b is index 1
            val = stats.get(f"metric_{chr(97+index)}_percent", 0.0)

        # Special Case: Identity Asymmetry Preferred Subject
        elif col_key == "preferred_subject_idx":
            idx = stats.get("preferred_subject_idx")
            subjects = []
            if "choices" in summary and summary["choices"]:
                # Try to get subjects from metadata or look them up
                survey_id = summary.get("survey_id")
                # We can't easily import here if it causes circular dependency,
                # but we can try to find subjects in the summary if they were added
                subjects = summary.get("subjects", [])
                if not subjects:
                    try:
                        from database.queries import get_subjects

                        subjects = get_subjects(survey_id)
                    except Exception:
                        pass

            val = subjects[idx] if idx is not None and idx < len(subjects) else "-"
            values[col_key] = val
            continue

        # Standard Case
        else:
            # Try specific key, then key_percent, then key (direct)
            val = stats.get(f"{col_key}_percent", stats.get(col_key, 0.0))

        values[col_key] = val

    # 2. Determine Highlighting
    highlights = set()

    # Logic A: Threshold-based (Consistency, Transitivity)
    threshold_cols = {
        "consistency": 70,
        "identity_consistency": 70,
        "transitivity_rate": 75,
        "order_consistency": 75,
        "group_consistency": 80,
        "linear_consistency": 80,
        "triangle_consistency": 75,
    }

    # Logic B: Max-based (Comparison between columns)
    # If we have multiple percentage columns that aren't threshold-based, highlight the max
    comparison_candidates = {
        k: v
        for k, v in values.items()
        if k not in threshold_cols and columns[k].get("type") == "percentage"
    }

    if len(comparison_candidates) > 1:
        max_val = max(comparison_candidates.values())
        for k, v in comparison_candidates.items():
            if v == max_val and v > 0:  # Only highlight if it's the winner
                highlights.add(k)

    # Apply Threshold Logic
    for k, v in values.items():
        if (
            k in threshold_cols
            and isinstance(v, (int, float))
            and v >= threshold_cols[k]
        ):
            highlights.add(k)

    # Special Case: Preference Ranking (Final Score)
    if (
        "consistency" in columns
        and summary.get("strategy_name") == "preference_ranking_survey"
    ):
        # Recalculate specifically for this complex case if needed, or rely on stats
        pass

    # 3. Render Cells
    cells = []
    for col_key in col_keys:
        val = values[col_key]
        col_config = columns[col_key]
        col_type = col_config.get("type", "percentage")

        is_highlight = col_key in highlights
        css_class = "highlight-row" if is_highlight else ""

        # Formatting
        if col_type == "percentage" and isinstance(val, (int, float)):
            formatted_val = f"{val:.1f}%"
            if isinstance(val, int) or (isinstance(val, float) and val.is_integer()):
                formatted_val = f"{int(val)}%"
        else:
            formatted_val = str(val)

        cells.append(f'<td class="{css_class}">{formatted_val}</td>')

    return cells


def _format_timestamp(created_at) -> str:
    if not created_at:
        return ""
    try:
        if isinstance(created_at, str):
            return created_at[:16]
        return created_at.strftime("%d-%m-%Y %H:%M")
    except (AttributeError, ValueError, TypeError):
        return str(created_at)[:16]


def generate_overall_statistics_table(
    summaries: List[Dict],
    option_labels: Tuple[str, str],
    strategy_name: str = None,
    rank_keywords: Tuple[str, str] = None,
) -> str:
    """
    Generate overall statistics summary table across all survey responses.

    Args:
        summaries: List of dictionaries containing survey summaries.
        option_labels: Labels for the two options.
        strategy_name: Name of the strategy used for the survey.
        rank_keywords: Tuple of (keyword_a, keyword_b) for rank strategies.

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
                    consistencies = calculate_cyclic_shift_group_consistency(choices)
                elif strategy_name == "sign_symmetry_test":
                    consistencies = calculate_linear_symmetry_group_consistency(choices)
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
                    extract_extreme_vector_preferences(choices)
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
    # Generic Rank Comparison Handling (Replaces hardcoded l1_vs_leontief)
    elif strategy_name and strategy_name.endswith("_rank_comparison"):
        # Use option_labels for display (human readable) if available.
        # Fallback to generic labels if not.
        labels = option_labels if option_labels else ("Metric A", "Metric B")

        overall_table = _generate_rank_overall_consistency_table(
            summaries, title, note, labels
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

    # Identity Asymmetry Strategy
    elif strategy_name == "identity_asymmetry":
        total_consistency = 0
        valid_summaries = 0
        for summary in summaries:
            stats = summary.get("stats", {})
            if "identity_consistency" in stats:
                total_consistency += stats["identity_consistency"]
                valid_summaries += 1

        avg_consistency = (
            total_consistency / valid_summaries if valid_summaries > 0 else 0
        )

        identity_consistency_label = get_translation("identity_consistency", "answers")

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
                            <td>{identity_consistency_label}</td>
                            <td>{avg_consistency:.1f}%</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <p class="summary-note">{note}</p>
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
                    deduced_data = deduce_rankings(choices)
                    if deduced_data:
                        final_score = calculate_final_consistency_score(deduced_data)
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
        # Handle root sum squared strategies (Legacy/Specific)
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
        consistency_data = calculate_cyclic_shift_group_consistency(choices)

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
        consistency_data = calculate_linear_symmetry_group_consistency(choices)

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

    metrics = calculate_temporal_preference_metrics(choices)

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

    metrics = calculate_dynamic_temporal_metrics(choices)

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
        metrics = calculate_temporal_preference_metrics(choices)
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
    """Generate consistency breakdown table for any rank-based strategy."""
    if not summaries:
        no_data_msg = get_translation("no_answers", "answers")
        return f"""
        <div class="summary-table-container">
            <h2>{title}</h2>
            <p class="summary-note">{no_data_msg}</p>
        </div>
        """

    # Bucket by observed consistency percentages (rounded to 1 decimal)
    # bucket_data maps consistency level -> { "a": count, "b": count, "neutral": count }
    bucket_data: Dict[float, Dict[str, int]] = {}

    for summary in summaries:
        stats = summary.get("stats", {})

        # Strictly use generic keys (new calculator)
        metric_a_percent = stats.get("metric_a_percent")
        metric_b_percent = stats.get("metric_b_percent")
        consistency_percent = stats.get("consistency_percent")

        if (
            metric_a_percent is None
            or metric_b_percent is None
            or consistency_percent is None
        ):
            continue

        a = float(metric_a_percent)
        b = float(metric_b_percent)

        # Check if we have valid data
        if a + b <= 0:
            continue

        level = round(float(consistency_percent), 1)
        bucket_data.setdefault(level, {"a": 0, "b": 0, "neutral": 0})

        # Classify user based on dominant preference
        # Using a small epsilon for floating point comparison
        if abs(a - b) < 1e-9:
            bucket_data[level]["neutral"] += 1
        elif a > b:
            bucket_data[level]["a"] += 1
        else:
            bucket_data[level]["b"] += 1

    if not bucket_data:
        no_data_msg = get_translation("no_answers", "answers")
        return f"""
        <div class="summary-table-container">
            <h2>{title}</h2>
            <p class="summary-note">{no_data_msg}</p>
        </div>
        """

    def fmt_cell(count: int, total: int) -> str:
        if total == 0:
            return "0 (0.0%)"
        percent = (count / total) * 100
        return f"{count} ({percent:.1f}%)"

    # Pre-calculate grand total for percentages in "# of Users" column
    grand_total_users = sum(
        counts["a"] + counts["b"] + counts["neutral"] for counts in bucket_data.values()
    )

    rows = []
    total_users = 0
    total_a = 0
    total_b = 0
    total_neutral = 0

    for level in sorted(bucket_data.keys()):
        counts = bucket_data[level]
        num_users = counts["a"] + counts["b"] + counts["neutral"]
        total_users += num_users
        total_a += counts["a"]
        total_b += counts["b"]
        total_neutral += counts["neutral"]

        # Highlight whichever category has the most people
        max_count = max(counts["a"], counts["b"], counts["neutral"])
        a_class_attr = (
            ' class="highlight-cell"'
            if counts["a"] == max_count and max_count > 0
            else ""
        )
        b_class_attr = (
            ' class="highlight-cell"'
            if counts["b"] == max_count and max_count > 0
            else ""
        )
        neutral_class_attr = (
            ' class="highlight-cell"'
            if counts["neutral"] == max_count and max_count > 0
            else ""
        )

        rows.append(
            f"""
            <tr>
                <td>{level:.1f}%</td>
                <td>{fmt_cell(num_users, grand_total_users)}</td>
                <td{a_class_attr}>{fmt_cell(counts["a"], num_users)}</td>
                <td{b_class_attr}>{fmt_cell(counts["b"], num_users)}</td>
                <td{neutral_class_attr}>{fmt_cell(counts["neutral"], num_users)}</td>
            </tr>
            """
        )

    if total_users > 0:
        total_label = get_translation("total", "answers")

        # Highlight whichever category has the most people overall
        max_total = max(total_a, total_b, total_neutral)
        a_total_class = (
            ' class="highlight-cell"' if total_a == max_total and max_total > 0 else ""
        )
        b_total_class = (
            ' class="highlight-cell"' if total_b == max_total and max_total > 0 else ""
        )
        neutral_total_class = (
            ' class="highlight-cell"'
            if total_neutral == max_total and max_total > 0
            else ""
        )

        rows.append(
            f"""
            <tr class="total-row">
                <td><strong>{total_label}</strong></td>
                <td><strong>{fmt_cell(total_users, total_users)}</strong></td>
                <td{a_total_class}><strong>{fmt_cell(total_a, total_users)}</strong></td>
                <td{b_total_class}><strong>{fmt_cell(total_b, total_users)}</strong></td>
                <td{neutral_total_class}><strong>{fmt_cell(total_neutral, total_users)}</strong></td>
            </tr>
            """
        )

    consistency_level_label = get_translation("consistency_level", "answers")
    num_users_label = get_translation("num_of_users", "answers")
    neutral_label = get_translation("neutral", "answers")

    # Use passed labels (which are translated keywords)
    label_a = (
        option_labels[0] if option_labels and len(option_labels) > 0 else "Metric A"
    )
    label_b = (
        option_labels[1] if option_labels and len(option_labels) > 1 else "Metric B"
    )

    explanatory_note = get_translation("overall_statistics_note", "answers")

    return f"""
    <div class="summary-table-container consistency-breakdown-container">
        <h2>{title}</h2>
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>{consistency_level_label}</th>
                        <th>{num_users_label}</th>
                        <th>{label_a}</th>
                        <th>{label_b}</th>
                        <th>{neutral_label}</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </div>
        <p class="summary-note">{note}</p>
        <p class="summary-note"><em>{explanatory_note}</em></p>
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

        metrics = calculate_sub_survey_consistency_metrics(choices, sub_survey_num)
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

    metrics = calculate_triangle_inequality_metrics(choices)

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


def generate_identity_asymmetry_analysis(
    choices: List[Dict], subjects: List[str] = None
) -> str:
    """
    Generate identity asymmetry analysis HTML for a single user.
    Includes the Pain Curve table.
    """
    if not choices:
        return ""

    from analysis.logic.stats_calculators import calculate_identity_asymmetry_metrics

    metrics = calculate_identity_asymmetry_metrics(choices)
    if not metrics:
        return ""

    pain_curve = metrics.get("pain_curve", {})
    consistency = metrics.get("identity_consistency", 0.0)
    preferred_idx = metrics.get("preferred_subject_idx")

    # Subjects
    if not subjects:
        subjects = [f"Subject {i}" for i in range(10)]  # Fallback

    preferred_subject_name = (
        subjects[preferred_idx]
        if preferred_idx is not None and preferred_idx < len(subjects)
        else "N/A"
    )

    # Translations
    title = get_translation("identity_asymmetry_summary", "answers")
    consistency_label = get_translation("identity_consistency", "answers")
    bias_strength_label = get_translation("identity_bias_strength", "answers")
    pain_curve_title = get_translation("pain_curve_title", "answers")
    th_step = get_translation("step_number", "answers")
    th_magnitude = get_translation("magnitude", "answers")
    th_favors = get_translation("preferred_subject", "answers")

    # If translations don't exist, use defaults
    if th_step.startswith("["):
        th_step = "Step"
    if th_magnitude.startswith("["):
        th_magnitude = "Magnitude"
    if th_favors.startswith("["):
        th_favors = "Choice (Favors)"

    # Build Pain Curve Rows
    rows = []
    for step in range(1, 11):
        idx = pain_curve.get(step)
        subject_name = subjects[idx] if idx is not None and idx < len(subjects) else "-"

        # Determine magnitude from first matching choice
        magnitude = "-"
        for choice in choices:
            metadata = choice.get("generation_metadata")
            if isinstance(metadata, str):
                try:
                    import json

                    metadata = json.loads(metadata)
                except (ValueError, TypeError, json.JSONDecodeError):
                    metadata = None
            if metadata and metadata.get("step_number") == step:
                magnitude = metadata.get("magnitude", "-")
                break

        rows.append(
            f"""
            <tr>
                <td>{step}</td>
                <td>{magnitude}</td>
                <td class="{'chosen-subject' if idx is not None else ''}">{subject_name}</td>
            </tr>
        """
        )

    html_output = f"""
    <div class="identity-asymmetry-analysis">
        <h4>{title}</h4>
        <div class="metrics-summary">
            <p><strong>{consistency_label}:</strong> {consistency}%</p>
            <p><strong>{bias_strength_label}:</strong> {preferred_subject_name}</p>
        </div>

        <h5>{pain_curve_title}</h5>
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>{th_step}</th>
                        <th>{th_magnitude}</th>
                        <th>{th_favors}</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(rows)}
                </tbody>
            </table>
        </div>
    </div>
    """
    return html_output
