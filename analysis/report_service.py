"""
This is the main service layer for the new web-based report system.
It orchestrates data fetching, calculation, and rendering for the survey response endpoints.
"""

import logging
from typing import Dict, List, Tuple

from analysis.presentation.html_renderers import (
    generate_aggregated_percentile_breakdown as _generate_aggregated_percentile_breakdown,
)
from analysis.presentation.html_renderers import (
    generate_user_survey_matrix_html as _generate_user_survey_matrix_html,
)
from analysis.presentation.html_renderers import (
    render_detailed_user_choices,
)
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

    # 3. Call renderer with fetched data
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
    )
