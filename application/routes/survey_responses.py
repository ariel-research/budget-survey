"""
Survey responses route module.
Handles all survey response related endpoints including responses and comments.
"""

import logging
from typing import Dict, List, Optional

from flask import Blueprint, render_template, request

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
    get_survey_description,
    get_survey_pair_generation_config,
    retrieve_completed_survey_responses,
    retrieve_user_survey_choices,
)

logger = logging.getLogger(__name__)
responses_routes = Blueprint("responses", __name__)


def validate_sort_params(sort_by, sort_order):
    """
    Validate and sanitize sorting parameters.

    Args:
        sort_by: The field to sort by
        sort_order: The sort direction ('asc' or 'desc')

    Returns:
        tuple: (valid_sort_by, valid_sort_order)
    """
    allowed_sort_fields = ["user_id", "created_at"]
    allowed_sort_orders = ["asc", "desc"]

    valid_sort_by = sort_by if sort_by in allowed_sort_fields else None
    valid_sort_order = sort_order if sort_order in allowed_sort_orders else "asc"

    return valid_sort_by, valid_sort_order


def get_user_responses(
    survey_id: Optional[int] = None,
    user_choices: Optional[List[Dict]] = None,
    show_tables_only: bool = False,
    show_detailed_breakdown_table: bool = True,
    show_overall_survey_table: bool = True,
    sort_by: str = None,
    sort_order: str = "asc",
) -> Dict[str, str]:
    """
    Get formatted user survey responses with optional sorting.

    Args:
        survey_id: Optional survey ID to filter responses
        user_choices: Optional pre-filtered choices (if already fetched)
        show_tables_only: If True, only show summary tables
        show_detailed_breakdown_table: If True, show detailed breakdown table
        show_overall_survey_table: If True, show overall survey table
        sort_by: Optional field to sort by ('user_id', 'created_at')
        sort_order: Optional order for sorting, 'asc' (default) or 'desc'

    Returns:
        Dict[str, str]: A dictionary containing the formatted survey responses.

    Raises:
        SurveyNotFoundError: If no responses found.
        StrategyConfigError: If strategy configuration error.
        ResponseProcessingError: If general processing error.
    """
    try:
        strategy_name = None
        # Use provided choices or fetch new ones
        if user_choices is None:
            user_choices = retrieve_user_survey_choices()
            if survey_id is not None:
                user_choices = [
                    choice
                    for choice in user_choices
                    if choice["survey_id"] == survey_id
                ]

            # Apply sorting if requested
            if sort_by:
                reverse = sort_order.lower() == "desc"
                if sort_by == "user_id":
                    user_choices.sort(key=lambda x: x["user_id"], reverse=reverse)
                elif sort_by == "created_at":
                    user_choices.sort(
                        key=lambda x: x["response_created_at"], reverse=reverse
                    )

            if survey_id is not None and not user_choices:
                logger.warning(f"No responses found for survey {survey_id}")
                raise SurveyNotFoundError(survey_id)

        # Add strategy labels and get strategy name if survey_id is known
        survey_labels = {}  # Store labels for each survey
        if survey_id is not None:
            strategy_config = get_survey_pair_generation_config(survey_id)
            if strategy_config:
                try:
                    strategy = StrategyRegistry.get_strategy(
                        strategy_config["strategy"]
                    )
                    strategy_name = strategy.get_strategy_name()  # Get strategy name
                    survey_labels[survey_id] = strategy.get_option_labels()
                except ValueError as e:
                    logger.warning(f"Strategy not found for survey {survey_id}: {e}")
                    survey_labels[survey_id] = ("Option 1", "Option 2")

        # Add labels to each choice (if not already done via survey_id)
        for choice in user_choices:
            current_survey_id = choice["survey_id"]
            if current_survey_id not in survey_labels:
                # Fetch config only if needed (not fetched above)
                if survey_id is None or current_survey_id != survey_id:
                    config = get_survey_pair_generation_config(current_survey_id)
                    if config:
                        try:
                            strategy = StrategyRegistry.get_strategy(config["strategy"])
                            # Get name if this is the first time for this survey
                            if strategy_name is None and survey_id is None:
                                strategy_name = strategy.get_strategy_name()
                            survey_labels[current_survey_id] = (
                                strategy.get_option_labels()
                            )
                        except ValueError as e:
                            logger.warning(
                                f"Strat not found for survey {current_survey_id}: {e}"
                            )
                            survey_labels[current_survey_id] = (
                                "Option 1",
                                "Option 2",
                            )

            # Add labels to choice
            if current_survey_id in survey_labels:
                choice["strategy_labels"] = survey_labels[current_survey_id]

        # Get the appropriate labels for the main generation function
        if survey_id is not None and survey_id in survey_labels:
            option_labels = survey_labels[survey_id]
        elif user_choices and user_choices[0]["survey_id"] in survey_labels:
            # Fallback for /responses and /users/{id}/responses
            # where survey_id isn't fixed
            option_labels = survey_labels[user_choices[0]["survey_id"]]
        else:
            option_labels = ("Option 1", "Option 2")

        response_data = ResponseFormatter.format_response_data(user_choices)
        response_data["content"] = generate_detailed_user_choices(
            user_choices,
            option_labels=option_labels,
            strategy_name=strategy_name,
            show_tables_only=show_tables_only,
            show_detailed_breakdown_table=show_detailed_breakdown_table,
            show_overall_survey_table=show_overall_survey_table,
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

    return comments_data


@responses_routes.route("/<int:survey_id>/responses")
def get_survey_responses(survey_id: int):
    """
    Get all responses for a specific survey with optional sorting.

    Args:
        survey_id: ID of the survey to get responses for

    Returns:
        Rendered template with survey responses
    """
    try:
        # Get and validate sort parameters
        sort_by, sort_order = validate_sort_params(
            request.args.get("sort"), request.args.get("order", "asc")
        )

        logger.info(
            f"Sorting parameters - sort_by: {sort_by}, sort_order: {sort_order}"
        )

        # Get user responses filtered by survey_id
        data = get_user_responses(
            survey_id=survey_id,
            show_tables_only=True,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        # Fetch the survey description
        survey_description = get_survey_description(survey_id)
        return render_template(
            "responses/detail.html",
            data=data,
            survey_id=survey_id,
            survey_description=survey_description,
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
    """Get all responses across all surveys with optional sorting."""
    try:
        # Get and validate sort parameters
        sort_by, sort_order = validate_sort_params(
            request.args.get("sort"), request.args.get("order", "asc")
        )

        data = get_user_responses(
            show_overall_survey_table=False, sort_by=sort_by, sort_order=sort_order
        )
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


@responses_routes.route("/users/<string:user_id>/responses")
def get_user_responses_detail(user_id: str):
    """Get all responses from a specific user."""
    try:
        # Get all choices and filter for specific user
        choices = retrieve_user_survey_choices()
        user_choices = [c for c in choices if c["user_id"] == user_id]

        if not user_choices:
            logger.warning(f"No responses found for user {user_id}")
            return (
                render_template(
                    "error.html",
                    message=get_translation(
                        "no_user_responses", "messages", user_id=user_id
                    ),
                ),
                404,
            )

        # Use get_user_responses with show_tables_only=False for full details
        data = get_user_responses(
            user_choices=user_choices,
            show_tables_only=False,
            show_overall_survey_table=False,
        )

        return render_template(
            "responses/user_detail.html", data=data, user_id=user_id, full_title=False
        )

    except Exception as e:
        logger.error(f"Error retrieving user responses: {str(e)}", exc_info=True)
        return (
            render_template(
                "error.html",
                message=get_translation("survey_retrieval_error", "messages"),
            ),
            500,
        )


@responses_routes.route("/<int:survey_id>/users/<string:user_id>/responses")
def get_user_survey_response(survey_id: int, user_id: str):
    """Get specific user's response for a particular survey."""
    try:
        # Get all choices and filter for specific user and survey
        choices = retrieve_user_survey_choices()
        user_survey_choices = [
            c
            for c in choices
            if c["user_id"] == user_id and c["survey_id"] == survey_id
        ]

        if not user_survey_choices:
            return (
                render_template(
                    "error.html",
                    message=get_translation(
                        "no_user_responses", "messages", user_id=user_id
                    ),
                ),
                404,
            )

        # Pass the specific user_survey_choices to get_user_responses
        # It will handle fetching the strategy and labels for the given survey_id
        data = get_user_responses(
            survey_id=survey_id,  # Keep survey_id to fetch strategy
            user_choices=user_survey_choices,  # Pass pre-filtered choices
            show_tables_only=False,
            show_detailed_breakdown_table=False,  # Don't show breakdown table
            show_overall_survey_table=False,  # Don't show overall table
        )
        return render_template(
            "responses/user_detail.html",
            data=data,
            user_id=user_id,
            survey_id=survey_id,
            full_title=True,
        )

    except Exception as e:
        logger.error(f"Error retrieving user survey response: {str(e)}", exc_info=True)
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
        survey_comments = {survey_id: comments} if comments else {}

        return render_template(
            "responses/comments.html",
            data={"content": survey_comments},
            show_comments=True,
            survey_id=survey_id,
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
            "responses/comments.html",
            data={"content": grouped_comments} if grouped_comments else {},
            show_comments=True,
        )
    except Exception as e:
        logger.error(f"Error retrieving all comments: {str(e)}")
        return (
            render_template(
                "error.html",
                message=get_translation("survey_retrieval_error", "messages"),
            ),
            500,
        )
