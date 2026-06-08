"""
This file is part of the legacy PDF generation system.
DEPRECATED: This module is maintained only for backward compatibility.
The new web-based report system uses analysis/report_service.py.
"""

import logging
from typing import Any, Dict, List, Tuple

from analysis import report_service
from analysis.logic import stats_calculators
from analysis.presentation import legacy_html_renderers

logger = logging.getLogger(__name__)


def generate_detailed_user_choices(
    user_choices: List[Dict],
    option_labels: Tuple[str, str],
    strategy_name: str = None,
) -> Dict[str, str]:
    """
    Legacy wrapper for generating detailed user choices analysis.
    Delegates to the modern report service.
    """
    return report_service.generate_detailed_user_choices(
        user_choices=user_choices,
        option_labels=option_labels,
        strategy_name=strategy_name,
    )


def generate_executive_summary(
    summary_stats: Any,
    optimization_stats: Any,
    responses_stats: Any,
) -> str:
    """Legacy wrapper for executive summary generation."""
    return legacy_html_renderers.generate_executive_summary(
        summary_stats, optimization_stats, responses_stats
    )


def generate_overall_stats(summary_stats: Any, optimization_stats: Any) -> str:
    """Legacy wrapper for overall statistics generation."""
    return legacy_html_renderers.generate_overall_stats(
        summary_stats, optimization_stats
    )


def generate_survey_analysis(summary_stats: Any) -> str:
    """Legacy wrapper for survey analysis generation."""
    return legacy_html_renderers.generate_survey_analysis(summary_stats)


def generate_individual_analysis(optimization_stats: Any) -> str:
    """Legacy wrapper for individual analysis generation."""
    return legacy_html_renderers.generate_individual_analysis(optimization_stats)


def generate_key_findings(summary_stats: Any, optimization_stats: Any) -> str:
    """Legacy wrapper for key findings generation."""
    return legacy_html_renderers.generate_key_findings(
        summary_stats, optimization_stats
    )


def generate_user_comments_section(responses_df: Any) -> str:
    """Legacy wrapper for user comments section generation."""
    return legacy_html_renderers.generate_user_comments_section(responses_df)


def generate_methodology_description() -> str:
    """Legacy wrapper for methodology description generation."""
    return legacy_html_renderers.generate_methodology_description()


def generate_aggregated_percentile_breakdown(user_choices: List[Dict]) -> str:
    """Legacy wrapper for aggregated percentile breakdown."""
    return report_service.generate_aggregated_percentile_breakdown(user_choices)


def generate_user_survey_matrix_html(user_choices: List[Dict]) -> str:
    """Legacy wrapper for user survey matrix generation."""
    return report_service.generate_user_survey_matrix_html(user_choices)


# Re-export stats calculators needed by legacy generator
get_summary_value = stats_calculators.get_summary_value
calculate_user_consistency = stats_calculators.calculate_user_consistency
calculate_choice_statistics = stats_calculators.calculate_choice_statistics
