import logging
from typing import Dict, Optional

from flask import Blueprint, abort, render_template

from analysis.report_content_generators import (
    generate_detailed_user_choices,
)
from application.services.pair_generation.base import StrategyRegistry
from application.translations import get_translation
from database.queries import (
    get_survey_pair_generation_config,
    retrieve_completed_survey_responses,
    retrieve_user_survey_choices,
)

logger = logging.getLogger(__name__)
answers_routes = Blueprint("answers", __name__)


def format_comments_data(responses):
    """Format survey responses for comments display."""
    comments_data = []
    for response in responses:
        if response.get("user_comment") and response["user_comment"].strip():
            comments_data.append(
                {
                    "survey_id": response["survey_id"],
                    "user_id": response["user_id"],
                    "comment": response["user_comment"],
                    "created_at": response["response_created_at"],
                }
            )
    return comments_data


@answers_routes.route("/comments")
def show_comments():
    """Display user comments from all surveys."""
    try:
        # Get all completed survey responses
        responses = retrieve_completed_survey_responses()

        # Format comments data
        comments = format_comments_data(responses)

        # Group comments by survey
        grouped_comments = {}
        for comment in comments:
            survey_id = comment["survey_id"]
            if survey_id not in grouped_comments:
                grouped_comments[survey_id] = []
            grouped_comments[survey_id].append(comment)

        return render_template(
            "answers/answers_comments.html",
            data={"content": grouped_comments} if grouped_comments else {},
            show_comments=True,
        )

    except Exception as e:
        logger.error(f"Error retrieving survey comments: {str(e)}")
        return render_template(
            "error.html", message=get_translation("survey_retrieval_error", "messages")
        )


def get_user_answers(survey_id: Optional[int] = None) -> Dict[str, str]:
    """
    Fetch and format user survey answers with strategy-based display.

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

            # Get strategy configuration for this survey
            config = get_survey_pair_generation_config(survey_id)
            if config:
                strategy = StrategyRegistry.get_strategy(config["strategy"])
                option_labels = strategy.get_option_labels()
            else:
                option_labels = ("Option 1", "Option 2")
        else:
            option_labels = ("Option 1", "Option 2")

        if not choices:
            return {}

        # Generate detailed HTML with strategy context
        formatted_data = generate_detailed_user_choices(choices, option_labels)
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
