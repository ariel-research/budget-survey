import logging
from typing import Any, Dict, List

from database.queries import (
    get_blacklisted_users,
    get_surveys_for_dashboard,
    get_user_participation_overview,
    retrieve_completed_survey_responses,
)

logger = logging.getLogger(__name__)


def process_survey_data(surveys: List[Dict]) -> List[Dict]:
    """
    Process raw survey data to include strategy information while preserving
    rich metadata needed by the dashboard parser.

    Args:
        surveys: List of survey records from database

    Returns:
        List of processed survey data including strategy details
    """
    survey_data = []

    for survey in surveys:
        try:
            pair_config = survey.get("pair_generation_config") or {}
            strategy_name = (
                pair_config.get("strategy") if isinstance(pair_config, dict) else None
            )
            survey_data.append(
                {
                    # Legacy fields currently used by template
                    "id": survey["id"],
                    "name": survey.get("title", {}),
                    "description": survey.get("description") or None,
                    "strategy_name": strategy_name,
                    "story_code": survey.get("story_code"),
                    # New fields for Researcher's Console parser
                    "active": survey.get("active", False),
                    "created_at": survey.get("created_at"),
                    "pair_generation_config": pair_config,
                    "title": survey.get("title", {}),
                    "subjects": survey.get("subjects", []),
                    "participant_count": int(survey.get("participant_count") or 0),
                }
            )
        except Exception as e:
            logger.error(
                "Error processing survey %s: %s",
                survey.get("id", "unknown"),
                str(e),
            )
            continue

    return survey_data


def get_dashboard_metrics() -> Dict[str, Any]:
    """Calculate basic metrics for the dashboard."""
    try:
        # Get and process all surveys for dashboard visibility.
        dashboard_surveys = get_surveys_for_dashboard()
        processed_surveys = process_survey_data(dashboard_surveys)

        # Get completed responses
        completed_responses = retrieve_completed_survey_responses()
        unique_participants = len(set(r["user_id"] for r in completed_responses))

        # Get unaware users count (blacklisted users)
        unaware_users = get_blacklisted_users()
        unaware_users_count = len(unaware_users)

        # Get users with surveys count
        user_participation_data = get_user_participation_overview()
        users_with_surveys_count = len(user_participation_data)

        return {
            "total_surveys": len(processed_surveys),
            "total_participants": unique_participants,
            "unaware_users_count": unaware_users_count,
            "users_with_surveys": users_with_surveys_count,
            "surveys": processed_surveys,
        }

    except Exception as e:
        logger.error(f"Error calculating dashboard metrics: {str(e)}")
        return {
            "total_surveys": 0,
            "total_participants": 0,
            "unaware_users_count": 0,
            "users_with_surveys": 0,
            "surveys": [],
        }
