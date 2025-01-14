import json
import logging
from typing import Dict, List

from flask import Blueprint, abort, render_template

from application.translations import get_translation
from database.queries import get_active_surveys

logger = logging.getLogger(__name__)
dashboard_routes = Blueprint("dashboard", __name__)


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


@dashboard_routes.route("/dashboard")
def dashboard():
    """Display overview of all active surveys with their strategies."""
    try:
        # Fetch all active surveys
        surveys = get_active_surveys()

        # Process surveys to include strategy information
        survey_data = process_survey_data(surveys)

        return render_template("dashboard/surveys_overview.html", surveys=survey_data)

    except Exception as e:
        logger.error(f"Error loading dashboard: {str(e)}")
        abort(500, description=get_translation("dashboard_error", "messages"))
