"""
Survey responses route module.
Handles all survey response related endpoints including responses and comments.
"""

import logging
from typing import Dict, List, Optional

from flask import Blueprint, render_template

from analysis.report_content_generators import generate_detailed_user_choices
from application.exceptions import (
    ResponseProcessingError,
    StrategyConfigError,
    SurveyNotFoundError,
)
from application.services.pair_generation.base import StrategyRegistry
from application.services.response_formatter import ResponseFormatter
from application.translations import get_translation
from database.queries import (
    get_survey_pair_generation_config,
    retrieve_completed_survey_responses,
    retrieve_user_survey_choices,
)

logger = logging.getLogger(__name__)
responses_routes = Blueprint("responses", __name__)


def get_user_answers(survey_id: Optional[int] = None) -> Dict[str, str]:
    """
    Get formatted user survey responses.

    Args:
        survey_id: Optional survey ID to filter responses

    Returns:
        Dictionary containing formatted response data

    Raises:
        SurveyNotFoundError: If survey not found
        StrategyConfigError: If strategy configuration is invalid
        ResponseProcessingError: If error processing responses
    """
    try:
        choices = retrieve_user_survey_choices()

        if survey_id is not None:
            choices = [c for c in choices if c["survey_id"] == survey_id]

            if not choices:
                logger.warning(f"No responses found for survey {survey_id}")
                raise SurveyNotFoundError(survey_id)

            strategy_config = get_survey_pair_generation_config(survey_id)
            if not strategy_config:
                logger.error(f"Invalid strategy config for survey {survey_id}")
                raise StrategyConfigError(survey_id, "unknown")

            strategy = StrategyRegistry.get_strategy(strategy_config["strategy"])
            option_labels = strategy.get_option_labels()
        else:
            option_labels = ("Option 1", "Option 2")

        response_data = ResponseFormatter.format_response_data(choices)
        response_data["content"] = generate_detailed_user_choices(
            choices, option_labels
        )
        return response_data

    except (SurveyNotFoundError, StrategyConfigError) as e:
        logger.warning(str(e))
        raise
    except Exception as e:
        logger.error(f"Error processing responses: {str(e)}", exc_info=True)
        raise ResponseProcessingError(f"Failed to process survey responses: {str(e)}")


def format_comments_data(responses: List[Dict]) -> List[Dict]:
    """
    Format survey responses for comments display.

    Args:
        responses: List of raw response data from database

    Returns:
        List of formatted comment data
    """
    processed_responses = set()
    comments_data = []

    for response in responses:
        response_id = (response["survey_response_id"], response["user_id"])

        if response_id in processed_responses:
            continue

        if response.get("user_comment") and response["user_comment"].strip():
            comments_data.append(
                {
                    "survey_id": response["survey_id"],
                    "user_id": response["user_id"],
                    "comment": response["user_comment"],
                    "created_at": response["response_created_at"],
                }
            )
            processed_responses.add(response_id)

    return ResponseFormatter.format_comments_data(comments_data)


@responses_routes.route("/<int:survey_id>/responses")
def get_survey_responses(survey_id: int):
    """
    Get all responses for a specific survey.

    Args:
        survey_id: ID of the survey to get responses for

    Returns:
        Rendered template with survey responses
    """
    try:
        data = get_user_answers(survey_id)
        return render_template("responses/detail.html", data=data, survey_id=survey_id)
    except SurveyNotFoundError as e:
        logger.warning(str(e))
        return (
            render_template(
                "error.html",
                message=get_translation(
                    "survey_not_found_or_empty", "messages", survey_id=survey_id
                ),
            ),
            404,
        )
    except ResponseProcessingError as e:
        logger.error(str(e))
        return (
            render_template(
                "error.html",
                message=get_translation("survey_retrieval_error", "messages"),
            ),
            500,
        )


@responses_routes.route("/responses")
def list_all_responses():
    """
    Get all responses across all surveys.

    Returns:
        Rendered template with all survey responses
    """
    try:
        data = get_user_answers()
        return render_template("responses/list.html", data=data)
    except ResponseProcessingError as e:
        logger.error(str(e))
        return (
            render_template(
                "error.html",
                message=get_translation("survey_retrieval_error", "messages"),
            ),
            500,
        )


@responses_routes.route("/<int:survey_id>/comments")
def get_survey_comments(survey_id: int):
    """
    Get all comments for a specific survey.

    Args:
        survey_id: ID of the survey to get comments for

    Returns:
        Rendered template with survey comments
    """
    try:
        responses = retrieve_completed_survey_responses()
        survey_responses = [r for r in responses if r["survey_id"] == survey_id]

        if not survey_responses:
            raise SurveyNotFoundError(survey_id)

        comments = format_comments_data(survey_responses)
        return render_template(
            "responses/comments/detail.html", data=comments, survey_id=survey_id
        )
    except SurveyNotFoundError as e:
        logger.warning(str(e))
        return (
            render_template(
                "error.html",
                message=get_translation(
                    "survey_not_found_or_empty", "messages", survey_id=survey_id
                ),
            ),
            404,
        )
    except Exception as e:
        logger.error(f"Error retrieving survey comments: {str(e)}")
        return (
            render_template(
                "error.html",
                message=get_translation("survey_retrieval_error", "messages"),
            ),
            500,
        )


@responses_routes.route("/comments")
def list_all_comments():
    """
    Get all comments across all surveys.

    Returns:
        Rendered template with all survey comments
    """
    try:
        responses = retrieve_completed_survey_responses()
        comments = format_comments_data(responses)
        return render_template("responses/comments/list.html", data=comments)
    except Exception as e:
        logger.error(f"Error retrieving all comments: {str(e)}")
        return (
            render_template(
                "error.html",
                message=get_translation("survey_retrieval_error", "messages"),
            ),
            500,
        )
