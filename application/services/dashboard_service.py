import json
import logging
from typing import Any, Dict, List

from database.queries import (
    get_active_surveys,
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
            config = json.loads(survey["pair_generation_config"])
            strategy_name = config.get("strategy")

            survey_data.append(
                {
                    "id": survey["id"],
                    "name": json.loads(survey["name"]),
                    "description": (
                        json.loads(survey["description"])
                        if survey["description"]
                        else None
                    ),
                    "strategy_name": strategy_name,
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
        active_surveys = get_active_surveys()
        processed_surveys = process_survey_data(active_surveys)

        # Get completed responses
        completed_responses = retrieve_completed_survey_responses()
        unique_participants = len(set(r["user_id"] for r in completed_responses))

        return {
            "total_surveys": len(processed_surveys),
            "total_participants": unique_participants,
            "surveys": processed_surveys,
        }

    except Exception as e:
        logger.error(f"Error calculating dashboard metrics: {str(e)}")
        return {"total_surveys": 0, "total_participants": 0, "surveys": []}
