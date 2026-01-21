"""
This is the main service layer for the new web-based report system.
It orchestrates data fetching, calculation, and rendering for the survey response endpoints.
"""

import logging
from typing import Dict, List, Tuple

from analysis.logic.stats_calculators import (
    calculate_choice_statistics,
    calculate_cyclic_shift_group_consistency,
    calculate_dynamic_temporal_metrics,
    calculate_final_consistency_score,
    calculate_linear_symmetry_group_consistency,
    calculate_rank_consistency_metrics,
    calculate_single_peaked_metrics,
    calculate_temporal_preference_metrics,
    calculate_triangle_inequality_metrics,
    deduce_rankings,
    extract_extreme_vector_preferences,
)
from analysis.presentation.html_renderers import (
    generate_aggregated_percentile_breakdown as _generate_aggregated_percentile_breakdown,
)
from analysis.presentation.html_renderers import (
    generate_detailed_breakdown_table,
    generate_extreme_vector_analysis_table,
    generate_overall_statistics_table,
    generate_preference_ranking_consistency_tables,
    generate_survey_choices_html,
)
from analysis.presentation.html_renderers import (
    generate_user_survey_matrix_html as _generate_user_survey_matrix_html,
)
from analysis.transitivity_analyzer import TransitivityAnalyzer
from application.translations import get_translation
from database.queries import (
    get_subjects,
    get_user_survey_performance_data,
)

logger = logging.getLogger(__name__)

# Re-export modern renderers used by the web application
generate_aggregated_percentile_breakdown = _generate_aggregated_percentile_breakdown
generate_user_survey_matrix_html = _generate_user_survey_matrix_html


def generate_detailed_user_choices(
    user_choices: List[Dict],
    option_labels: Tuple[str, str],
    strategy_name: str = None,
    show_tables_only: bool = False,
    show_detailed_breakdown_table: bool = True,
    show_overall_survey_table: bool = True,
    sort_by: str = None,
    sort_order: str = "asc",
) -> Dict[str, str]:
    """
    Generate detailed analysis of each user's choices for each survey.
    Orchestrates data fetching and rendering.

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
        Dict[str, str]: Dictionary containing HTML components.
    """
    # 1. Fetch performance data for users involved
    user_ids = list(set(c["user_id"] for c in user_choices)) if user_choices else []
    performance_data = []
    if user_ids:
        try:
            performance_data = get_user_survey_performance_data(user_ids)
        except Exception as e:
            logger.warning(
                f"Failed to fetch performance data for users {user_ids}: {e}"
            )

    # 2. Fetch subjects for surveys involved (for asymmetric loss distribution)
    survey_ids = list(set(c["survey_id"] for c in user_choices)) if user_choices else []
    subjects_map = {}
    if survey_ids:
        for survey_id in survey_ids:
            try:
                subjects = get_subjects(survey_id)
                if subjects:
                    subjects_map[survey_id] = subjects
            except Exception as e:
                logger.warning(f"Failed to fetch subjects for survey {survey_id}: {e}")

    # 3. Determine Rank Keywords if applicable
    rank_keywords = None
    if strategy_name and strategy_name.endswith("_rank_comparison"):
        try:
            # Strategy name format: "l1_vs_leontief_rank_comparison"
            # We want: "l1", "leontief"
            base = strategy_name.replace("_rank_comparison", "")
            parts = base.split("_vs_")
            if len(parts) == 2:
                rank_keywords = (parts[0], parts[1])
        except Exception as e:
            logger.warning(f"Error parsing strategy name {strategy_name}: {e}")

    # 4. Call renderer with fetched data
    return render_detailed_user_choices(
        user_choices=user_choices,
        option_labels=option_labels,
        strategy_name=strategy_name,
        show_tables_only=show_tables_only,
        show_detailed_breakdown_table=show_detailed_breakdown_table,
        show_overall_survey_table=show_overall_survey_table,
        sort_by=sort_by,
        sort_order=sort_order,
        performance_data=performance_data,
        subjects_map=subjects_map,
        rank_keywords=rank_keywords,
    )


def render_detailed_user_choices(
    user_choices: List[Dict],
    option_labels: Tuple[str, str],
    strategy_name: str = None,
    show_tables_only: bool = False,
    show_detailed_breakdown_table: bool = True,
    show_overall_survey_table: bool = True,
    sort_by: str = None,
    sort_order: str = "asc",
    performance_data: List[Dict] = None,
    subjects_map: Dict[int, List[str]] = None,
    rank_keywords: Tuple[str, str] = None,
) -> Dict[str, str]:
    """
    Generate detailed analysis of each user's choices for each survey.

    Args:
        user_choices: List of dictionaries containing user choices data.
        option_labels: Tuple of labels for the two options.
        strategy_name: Name of the pair generation strategy used.
        show_tables_only: If True, only show summary tables.
        show_detailed_breakdown_table: If True, include detailed breakdown table.
        show_overall_survey_table: If True, include overall survey table.
        sort_by: Current sort field for table headers ('user_id', 'created_at').
        sort_order: Current sort order for table headers ('asc', 'desc').
        performance_data: List of performance data dicts.
        subjects_map: Dict mapping survey_id to list of subjects.
        rank_keywords: Tuple of (keyword_a, keyword_b) for rank comparison strategies.

    Returns:
        Dict[str, str]: Dictionary containing HTML components.
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
    for choice in user_choices:
        user_id = choice["user_id"]
        survey_id = choice["survey_id"]
        if user_id not in grouped_choices:
            grouped_choices[user_id] = {}
        if survey_id not in grouped_choices[user_id]:
            grouped_choices[user_id][survey_id] = []
        grouped_choices[user_id][survey_id].append(choice)

    # Optimize performance data lookup
    perf_map = {}
    if performance_data:
        for perf in performance_data:
            perf_map[(perf["user_id"], perf["survey_id"])] = perf

    all_summaries = []

    # Collect statistics for all surveys
    for user_id, surveys in grouped_choices.items():
        for survey_id, choices in surveys.items():
            # Get strategy for dynamic calculations
            strategy = None
            current_strategy_name = strategy_name

            if choices and "strategy_name" in choices[0]:
                current_strategy_name = choices[0]["strategy_name"]
                try:
                    from application.services.pair_generation import StrategyRegistry

                    strategy = StrategyRegistry.get_strategy(current_strategy_name)
                except Exception:
                    pass

            # 1. Calculate Basic Stats
            stats = calculate_choice_statistics(choices, strategy=strategy)

            # 2. Merge Performance Data (DB Cache) - BEFORE specific calculations
            # This ensures DB data provides defaults, but Live calculations can overwrite them
            perf_key = (user_id, survey_id)
            if perf_key in perf_map and perf_map[perf_key].get("strategy_metrics"):
                stats.update(perf_map[perf_key]["strategy_metrics"])

            # 3. Run Live Strategy-Specific Metric Calculations (The Fix)

            # Temporal Preference
            if current_strategy_name == "biennial_budget_preference":
                temporal_metrics = calculate_temporal_preference_metrics(choices)
                stats.update(temporal_metrics)
                dynamic_temporal_metrics = calculate_dynamic_temporal_metrics(choices)
                stats.update(dynamic_temporal_metrics)

            # Triangle Inequality
            elif current_strategy_name == "triangle_inequality_test":
                triangle_metrics = calculate_triangle_inequality_metrics(choices)
                stats.update(triangle_metrics)

            # Generic Rank Comparison
            elif current_strategy_name and current_strategy_name.endswith(
                "_rank_comparison"
            ):
                kw_a = rank_keywords[0] if rank_keywords else "sum"
                kw_b = rank_keywords[1] if rank_keywords else "ratio"
                rank_metrics = calculate_rank_consistency_metrics(
                    choices, keyword_a=kw_a, keyword_b=kw_b
                )
                stats.update(rank_metrics)

            # Multi-Dimensional Single Peaked
            elif current_strategy_name == "multi_dimensional_single_peaked_test":
                single_peaked_metrics = calculate_single_peaked_metrics(choices)
                stats.update(single_peaked_metrics)

            # Peak Linearity Test (Extreme Vectors)
            elif current_strategy_name == "peak_linearity_test":
                _, processed_pairs, _, consistency_info, _ = (
                    extract_extreme_vector_preferences(choices)
                )
                total_matches = sum(matches for matches, total, _ in consistency_info)
                total_pairs = sum(total for _, total, _ in consistency_info)
                overall_consistency = (
                    int(round(100 * total_matches / total_pairs))
                    if total_pairs > 0
                    else 0
                )

                analyzer = TransitivityAnalyzer()
                transitivity_report = analyzer.get_full_transitivity_report(choices)

                stats.update(
                    {
                        "consistency": overall_consistency,
                        "transitivity_rate": transitivity_report.get(
                            "transitivity_rate", 0.0
                        ),
                        "order_consistency": transitivity_report.get(
                            "order_stability_score", 0.0
                        ),
                    }
                )

            # Sign Symmetry Test (Linear Symmetry)
            elif current_strategy_name == "sign_symmetry_test":
                consistencies = calculate_linear_symmetry_group_consistency(choices)
                stats["linear_consistency"] = consistencies.get("overall", 0.0)

            # Component Symmetry Test (Cyclic Shift)
            elif current_strategy_name == "component_symmetry_test":
                consistencies = calculate_cyclic_shift_group_consistency(choices)
                stats["group_consistency"] = consistencies.get("overall", 0.0)

            # Preference Ranking Survey
            elif current_strategy_name == "preference_ranking_survey":
                if len(choices) == 12:
                    deduced_data = deduce_rankings(choices)
                    if deduced_data:
                        final_score = calculate_final_consistency_score(deduced_data)
                        # Convert 0-3 score to percentage
                        stats["consistency"] = (final_score / 3) * 100
                    else:
                        stats["consistency"] = 0.0
                else:
                    stats["consistency"] = 0.0

            # Add metadata
            response_created_at = choices[0].get("response_created_at")
            summary = {
                "user_id": user_id,
                "survey_id": survey_id,
                "stats": stats,
                "response_created_at": response_created_at,
                "choices": choices,
            }
            if choices and "strategy_labels" in choices[0]:
                summary["strategy_labels"] = choices[0]["strategy_labels"]
            if choices and "strategy_name" in choices[0]:
                summary["strategy_name"] = choices[0]["strategy_name"]

            all_summaries.append(summary)

    # Initialize component HTML strings
    overall_stats_html = ""
    breakdown_html = ""
    user_details_html = ""
    all_components = []

    # 1. Overall statistics table
    if show_overall_survey_table:
        overall_stats_html = generate_overall_statistics_table(
            all_summaries, option_labels, strategy_name, rank_keywords
        )
        all_components.append(overall_stats_html)

    # 2. Detailed breakdown table
    if show_detailed_breakdown_table:
        breakdown_html = generate_detailed_breakdown_table(
            all_summaries, option_labels, strategy_name, sort_by, sort_order
        )
        all_components.append(breakdown_html)

    # 3. User-specific details
    if not show_tables_only:
        user_details = []
        for user_id, surveys in grouped_choices.items():
            user_details.append(f'<section id="user-{user_id}" class="user-choices">')
            user_details.append(
                f"<h3>{get_translation('user_id', 'answers')}: {user_id}</h3>"
            )

            for survey_id, choices in surveys.items():
                survey_strategy_name = strategy_name
                if choices and "strategy_name" in choices[0]:
                    survey_strategy_name = choices[0]["strategy_name"]

                if survey_strategy_name == "peak_linearity_test":
                    extreme_table_html = generate_extreme_vector_analysis_table(choices)
                    if extreme_table_html:
                        user_details.append(extreme_table_html)

                if survey_strategy_name == "preference_ranking_survey":
                    ranking_table_html = generate_preference_ranking_consistency_tables(
                        choices
                    )
                    if ranking_table_html:
                        user_details.append(ranking_table_html)

                user_details.append(
                    generate_survey_choices_html(
                        survey_id, choices, option_labels, survey_strategy_name
                    )
                )
            user_details.append("</section>")

        user_details_html = "\n".join(user_details)
        all_components.append(user_details_html)

    return {
        "overall_stats_html": overall_stats_html,
        "breakdown_html": breakdown_html,
        "user_details_html": user_details_html,
        "combined_html": "\n".join(all_components),
    }
