import logging
from typing import Dict, Optional

from flask import Blueprint, abort, render_template

from analysis.report_content_generators import (
    generate_detailed_user_choices,
)
from application.translations import get_translation
from database.queries import retrieve_user_survey_choices

logger = logging.getLogger(__name__)
answers_routes = Blueprint("answers", __name__)


def get_user_answers(survey_id: Optional[int] = None) -> Dict[str, str]:
    """
    Fetch and format user survey answers with optional survey filtering.

    Args:
        survey_id: Optional ID to filter results for a specific survey.

    Returns:
        Dict containing formatted HTML content of user answers.
        Empty dict if no answers found.

    Raises:
        Exception: On database or processing errors.
    """
    try:
        # Get raw data from database
        choices = retrieve_user_survey_choices()

        # Filter by survey_id if provided
        if survey_id is not None:
            choices = [c for c in choices if c["survey_id"] == survey_id]

        if not choices:
            return {}

        # Generate detailed HTML
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
                    message=get_translation(
                        "survey_not_found_or_empty", "messages", survey_id=survey_id
                    ),
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
                message=get_translation("survey_retrieval_error", "messages"),
            ),
            500,
        )
