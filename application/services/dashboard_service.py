import logging
from typing import Any, Dict, List

from database.queries import (
    get_active_surveys,
    get_blacklisted_users,
    retrieve_completed_survey_responses,
)

logger = logging.getLogger(__name__)


def process_survey_data(surveys: List[Dict]) -> List[Dict]:
    """
    Process raw survey data to include strategy information.

    Args:
        surveys: List of survey records from database

    Returns:
        List of processed survey data including strategy details
    """
    survey_data = []

    for survey in surveys:
        try:
            survey_data.append(
                {
                    "id": survey["id"],
                    "name": survey["title"],
                    "description": (
                        survey["description"] if survey["description"] else None
                    ),
                    "strategy_name": (
                        survey["pair_generation_config"].get("strategy")
                        if survey["pair_generation_config"]
                        else None
                    ),
                    "story_code": survey["story_code"],
                }
            )
        except Exception as e:
            logger.error(f"Error processing survey {survey['id']}: {str(e)}")
            continue

    return survey_data


def get_dashboard_metrics() -> Dict[str, Any]:
    """Calculate basic metrics for the dashboard."""
    try:
        # Get and process active surveys
        # Note: get_active_surveys now returns pre-processed data with story information
        active_surveys = get_active_surveys()
        logger.info(f"Active surveys retrieved: {active_surveys}")
        processed_surveys = process_survey_data(active_surveys)

        # Get completed responses
        completed_responses = retrieve_completed_survey_responses()
        unique_participants = len(set(r["user_id"] for r in completed_responses))

        # Get unaware users count (blacklisted users)
        unaware_users = get_blacklisted_users()
        unaware_users_count = len(unaware_users)

        return {
            "total_surveys": len(processed_surveys),
            "total_participants": unique_participants,
            "unaware_users_count": unaware_users_count,
            "surveys": processed_surveys,
        }

    except Exception as e:
        logger.error(f"Error calculating dashboard metrics: {str(e)}")
        return {
            "total_surveys": 0,
            "total_participants": 0,
            "unaware_users_count": 0,
            "surveys": [],
        }
