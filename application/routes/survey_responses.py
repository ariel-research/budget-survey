"""
Survey responses route module.
Handles all survey response related endpoints including responses and comments.
"""

import logging
from typing import Any, Dict, List, Optional

from flask import Blueprint, render_template, request

from analysis.report_content_generators import (
    generate_aggregated_percentile_breakdown,
    generate_detailed_user_choices,
)
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
    get_survey_response_counts,
    get_user_participation_overview,
    get_users_from_view,
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
    view_filter: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get formatted user survey responses with optional sorting and filtering.

    Args:
        survey_id: Optional survey ID to filter responses
        user_choices: Optional pre-filtered choices (if already fetched)
        show_tables_only: If True, only show summary tables
        show_detailed_breakdown_table: If True, show detailed breakdown table
        show_overall_survey_table: If True, show overall survey table
        sort_by: Optional field to sort by ('user_id', 'created_at')
        sort_order: Optional order for sorting, 'asc' (default) or 'desc'
        view_filter: Optional view name to filter users

    Returns:
        Dict[str, Any]: A dictionary containing the formatted survey responses.

    Raises:
        SurveyNotFoundError: If no responses found.
        StrategyConfigError: If strategy configuration error.
        ResponseProcessingError: If general processing error.
    """
    try:
        strategy_name = None
        survey_strategies = {}  # Maps survey_id to strategy_name

        # This variable will hold user_ids if a view_filter is active and valid
        characteristic_user_ids_from_view = None

        if view_filter:
            # Get all users matching the view's general criteria.
            temp_user_ids = get_users_from_view(view_filter)

            if not temp_user_ids:
                log_msg = (
                    f"No users found matching general criteria of view '{view_filter}'. "
                    f"No responses will be shown for survey {survey_id} with this filter."
                )
                logger.info(log_msg)

                survey_counts = get_survey_response_counts(survey_id)
                if survey_counts:
                    logger.info(
                        f"Context: Survey {survey_id} has {survey_counts['count']} "
                        f"responses from {survey_counts['unique_users']} unique users."
                    )
                else:
                    logger.info(
                        f"Context: Survey {survey_id} has no responses " f"in database."
                    )

                empty_data = ResponseFormatter.format_response_data([])
                empty_data["view_filter"] = view_filter
                empty_data["empty_filter"] = True
                empty_data["content"] = ""
                return empty_data
            else:
                characteristic_user_ids_from_view = temp_user_ids
                logger.debug(
                    f"View filter '{view_filter}' identified "
                    f"{len(characteristic_user_ids_from_view)} characteristic users."
                )

        if user_choices is None:
            user_choices = retrieve_user_survey_choices()

            # Apply view filter (characteristic users) if identified
            if characteristic_user_ids_from_view is not None:
                original_choice_count = len(user_choices)
                user_choices = [
                    choice
                    for choice in user_choices
                    if choice["user_id"] in characteristic_user_ids_from_view
                ]
                logger.debug(
                    f"Applied view filter '{view_filter}': "
                    f"{original_choice_count} initial choices -> {len(user_choices)} choices."
                )

            # Filter by the specific survey ID of the request
            if survey_id is not None:
                original_count = len(user_choices)
                user_choices = [
                    choice
                    for choice in user_choices
                    if choice["survey_id"] == survey_id
                ]
                logger.debug(
                    f"Applied survey_id filter {survey_id}: "
                    f"{original_count} initial choices -> {len(user_choices)} choices."
                )

            # Apply sorting
            if sort_by:
                reverse = sort_order.lower() == "desc"
                if sort_by == "user_id":
                    user_choices.sort(key=lambda x: x["user_id"], reverse=reverse)
                elif sort_by == "created_at":
                    user_choices.sort(
                        key=lambda x: x["response_created_at"], reverse=reverse
                    )

            # Handle the case where we have a view filter but no matching choices for the survey
            if survey_id is not None and not user_choices and view_filter:
                logger.info(
                    f"No responses found for survey {survey_id} with "
                    f"filter '{view_filter}'. Returning empty filter response."
                )
                empty_data = ResponseFormatter.format_response_data([])
                empty_data["view_filter"] = view_filter
                empty_data["empty_filter"] = True
                empty_data["content"] = ""
                return empty_data

            # Only raise error if no matches found and not using a view filter
            if survey_id is not None and not user_choices and not view_filter:
                logger.warning(
                    f"No responses found for survey {survey_id} after all filters "
                    f"(view_filter: '{view_filter or 'None'}')."
                )
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
                    strategy_name = strategy.get_strategy_name()
                    survey_labels[survey_id] = strategy.get_option_labels()
                    survey_strategies[survey_id] = strategy_name  # Store strategy name
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
                            strat_instance = StrategyRegistry.get_strategy(
                                config["strategy"]
                            )
                            s_name_for_survey = strat_instance.get_strategy_name()
                            survey_strategies[current_survey_id] = s_name_for_survey
                            if strategy_name is None and survey_id is None:
                                strategy_name = s_name_for_survey
                            survey_labels[current_survey_id] = (
                                strat_instance.get_option_labels()
                            )
                        except ValueError as e:
                            logger.warning(
                                f"Strat not found for survey {current_survey_id}: "
                                f"{e}"
                            )
                            survey_labels[current_survey_id] = (
                                "Option 1",
                                "Option 2",
                            )

            # Add labels to choice
            if current_survey_id in survey_labels:
                choice["strategy_labels"] = survey_labels[current_survey_id]

            # Add strategy name to choice
            if current_survey_id in survey_strategies:
                choice["strategy_name"] = survey_strategies[current_survey_id]

        # Get the appropriate labels for the main generation function
        if survey_id is not None and survey_id in survey_labels:
            option_labels = survey_labels[survey_id]
        elif user_choices and user_choices[0]["survey_id"] in survey_labels:
            option_labels = survey_labels[user_choices[0]["survey_id"]]
        else:
            option_labels = ("Option 1", "Option 2")

        response_data = ResponseFormatter.format_response_data(user_choices)

        # Generate detailed user choices content
        content_components = generate_detailed_user_choices(
            user_choices,
            option_labels=option_labels,
            strategy_name=strategy_name,
            show_tables_only=show_tables_only,
            show_detailed_breakdown_table=show_detailed_breakdown_table,
            show_overall_survey_table=show_overall_survey_table,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        # For backward compatibility
        if isinstance(content_components, str):
            response_data["content"] = content_components
        else:
            # Add all components to the response data
            response_data.update(content_components)
            # Keep the original content field for backward compatibility
            response_data["content"] = content_components.get("combined_html", "")

        # Add view filter information to response data
        if view_filter:
            response_data["view_filter"] = view_filter

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
    Get all responses for a specific survey with optional sorting and filtering.

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

        # Get view filter parameter
        view_filter = request.args.get("view_filter")

        logger.info(
            f"Request to /surveys/{survey_id}/responses. Sort: {sort_by} {sort_order}. "
            f"View filter: '{view_filter or 'None'}'"
        )

        # Get user responses filtered by survey_id and view_filter
        data = get_user_responses(
            survey_id=survey_id,
            show_tables_only=True,
            sort_by=sort_by,
            sort_order=sort_order,
            view_filter=view_filter,
        )

        # Fetch the survey description
        survey_description = get_survey_description(survey_id)

        # Get strategy information
        strategy_name = None
        strategy_config = get_survey_pair_generation_config(survey_id)
        if strategy_config:
            try:
                strategy = StrategyRegistry.get_strategy(strategy_config["strategy"])
                strategy_name = strategy.get_strategy_name()
            except ValueError as e:
                logger.warning(f"Strategy not found for survey {survey_id}: {e}")

        # Generate aggregated percentile breakdown table for extreme vector surveys
        percentile_breakdown = ""
        if strategy_name == "extreme_vectors":
            # Get all choices for this survey for aggregated analysis
            choices = retrieve_user_survey_choices()
            survey_choices = [c for c in choices if c["survey_id"] == survey_id]
            logger.info(f"Found {len(survey_choices)} choices for survey {survey_id}")

            # Apply view filter if present
            if view_filter and data.get("view_filter"):
                filtered_user_ids = set()
                for choice in data.get("responses", []):
                    filtered_user_ids.add(choice.get("user_id"))

                logger.info(f"Applying view filter with {len(filtered_user_ids)} users")
                if filtered_user_ids:
                    original_count = len(survey_choices)
                    survey_choices = [
                        c for c in survey_choices if c["user_id"] in filtered_user_ids
                    ]
                    logger.info(
                        f"Filtered from {original_count} to {len(survey_choices)} choices"
                    )

            percentile_breakdown = generate_aggregated_percentile_breakdown(
                survey_choices, strategy_name
            )
            logger.debug(
                f"Generated percentile breakdown HTML length: {len(percentile_breakdown)}"
            )

        return render_template(
            "responses/detail.html",
            data=data,
            survey_id=survey_id,
            survey_description=survey_description,
            strategy_name=strategy_name,
            view_filter=view_filter,
            percentile_breakdown=percentile_breakdown,
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
        view_filter = request.args.get("view_filter")

        data = get_user_responses(
            show_overall_survey_table=False,
            sort_by=sort_by,
            sort_order=sort_order,
            view_filter=view_filter,
        )
        return render_template(
            "responses/list.html", data=data, view_filter=view_filter
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
                        "no_user_responses", "answers", user_id=user_id
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
            logger.warning(
                f"No responses found for user {user_id} on survey " f"{survey_id}"
            )
            return (
                render_template(
                    "error.html",
                    message=get_translation(
                        "no_user_responses", "answers", user_id=user_id
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
            data={"content": grouped_comments if grouped_comments else {}},
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


@responses_routes.route("/users")
def get_users_overview():
    """
    Get user participation overview showing statistics for all users
    who have completed surveys.

    Returns:
        Rendered template with user participation data
    """
    try:
        # Get and validate sort parameters using standard naming convention
        sort_by = request.args.get("sort")
        sort_order = request.args.get("order", "asc")

        # Validate sorting parameters - allow user_id and last_activity
        allowed_sort_fields = ["user_id", "last_activity"]
        if sort_by not in allowed_sort_fields:
            sort_by = None

        allowed_sort_orders = ["asc", "desc"]
        if sort_order not in allowed_sort_orders:
            sort_order = "asc"

        # Get user participation data
        user_data = get_user_participation_overview()

        if not user_data:
            logger.info("No user participation data found")
            return render_template(
                "responses/users_overview.html",
                users=[],
                sort_by=sort_by,
                sort_order=sort_order,
            )

        # Apply sorting if requested
        if sort_by:
            reverse = sort_order.lower() == "desc"
            if sort_by == "user_id":
                user_data.sort(key=lambda x: x["user_id"], reverse=reverse)
            elif sort_by == "last_activity":
                user_data.sort(key=lambda x: x["last_activity"], reverse=reverse)

        # Process survey IDs for template display
        for user in user_data:
            # Convert successful survey IDs to list
            if user["successful_survey_ids"]:
                user["successful_survey_ids_list"] = [
                    int(sid) for sid in user["successful_survey_ids"].split(",")
                ]
            else:
                user["successful_survey_ids_list"] = []

            # Convert failed survey IDs to list
            if user["failed_survey_ids"]:
                user["failed_survey_ids_list"] = [
                    int(sid) for sid in user["failed_survey_ids"].split(",")
                ]
            else:
                user["failed_survey_ids_list"] = []

        logger.info(f"Retrieved participation data for {len(user_data)} users")

        return render_template(
            "responses/users_overview.html",
            users=user_data,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    except Exception as e:
        logger.error(f"Error retrieving user participation overview: {str(e)}")
        return (
            render_template(
                "error.html",
                message=get_translation("survey_retrieval_error", "messages"),
            ),
            500,
        )
