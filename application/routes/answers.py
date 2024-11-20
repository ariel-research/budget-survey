import logging
from typing import Dict, Optional

from flask import Blueprint, abort, render_template

from analysis.report_content_generators import (
    generate_detailed_user_choices,
)
from database.queries import retrieve_user_survey_choices

logger = logging.getLogger(__name__)
answers_routes = Blueprint("answers", __name__)


def get_user_answers(survey_id: Optional[int] = None) -> Dict:
    """Retrieve and format user answers data"""
    try:
        # Get raw data from database
        choices = retrieve_user_survey_choices()

        # Filter by survey_id if provided
        if survey_id is not None:
            choices = [c for c in choices if c["survey_id"] == survey_id]

        if not choices:
            return {}

        # Use existing function to generate detailed HTML
        formatted_data = generate_detailed_user_choices(choices)
        return {"content": formatted_data}

    except Exception as e:
        logger.error(f"Error retrieving user answers: {str(e)}")
        raise


@answers_routes.route("/")
def list_answers():
    """Display answers for all surveys"""
    try:
        data = get_user_answers()
        return render_template("answers/answers_list.html", data=data)
    except Exception as e:
        logger.error(f"Error displaying answers list: {str(e)}")
        abort(500)


@answers_routes.route("/<int:survey_id>")
def show_survey_answers(survey_id: int):
    """Display answers for a specific survey"""
    try:
        data = get_user_answers(survey_id)
        if not data:
            logger.warning(f"Survey ID {survey_id} not found or has no answers")
            return (
                render_template(
                    "error.html",
                    message=f"Survey {survey_id} was not found or has no answers. Please verify the survey ID and try again.",
                ),
                404,
            )
        return render_template(
            "answers/answers_detail.html", data=data, survey_id=survey_id
        )
    except Exception as e:
        logger.error(f"Error displaying survey {survey_id} answers: {str(e)}")
        return (
            render_template(
                "error.html",
                message="An error occurred while retrieving the survey data. Please try again later.",
            ),
            500,
        )
