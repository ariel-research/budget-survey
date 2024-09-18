import json
from logging_config import setup_logging
import logging
from .db import execute_query

setup_logging()

logger = logging.getLogger(__name__)

def create_user(external_id: int) -> int:
    """
    Inserts a new user into the users table and returns the new user's ID.

    Args:
        external_id (int): The external ID of the new user.

    Returns:
        The ID of the newly created user, or None if an error occurs.
    """
    query = "INSERT INTO users (external_id) VALUES (%s)"
    logger.debug(f"Executing query: {query} with external_id: {external_id}")
    ans = execute_query(query, (external_id,))
    print(f'answer: {ans}')
    return ans

def create_survey_response(user_id: int, survey_id: int, optimal_allocation: list) -> int:
    """
    Inserts a new survey response into the survey_responses table.

    Args:
        user_id (int): The internal ID of the user submitting the survey.
        survey_id (int): The ID of the survey.
        optimal_allocation (list): The user optimal allocation in JSON format.

    Returns:
        int: The ID of the newly created survey response, or None if an error occurs.
    """
    query = """
        INSERT INTO survey_responses (user_id, survey_id, optimal_allocation)
        VALUES (%s, %s, %s)
    """
    optimal_allocation_json = json.dumps(optimal_allocation)
    logger.debug(f"Executing query: {query} with user_id: {user_id}, survey_id: {survey_id}, optimal_allocation: {optimal_allocation_json}")
    return execute_query(query, (user_id, survey_id, optimal_allocation_json))

def create_comparison_pair(survey_response_id: int, pair_number: int, option_1: list, option_2: list, user_choice: int) -> int:
    """
    Inserts a new comparison pair into the comparison_pairs table.

    Args:
        survey_response_id (int): The ID of the related survey response.
        pair_number (int): The number of the comparison pair.
        option_1 (list): JSON data for the first option in the comparison pair.
        option_2 (list): JSON data for the second option in the comparison pair.
        user_choice (int): The user's choice between the two options.

    Returns:
        int: The ID of the newly created comparison pair, or None if an error occurs.
    """
    query = """
        INSERT INTO comparison_pairs (survey_response_id, pair_number, option_1, option_2, user_choice)
        VALUES (%s, %s, %s, %s, %s)
    """
    option_1_json = json.dumps(option_1)
    option_2_json = json.dumps(option_2)
    logger.debug(f"Executing query: {query} with survey_response_id: {survey_response_id}, pair_number: {pair_number}, option_1: {option_1_json}, option_2: {option_2_json}, user_choice: {user_choice}")
    return execute_query(query, (survey_response_id, pair_number, option_1_json, option_2_json, user_choice))

def mark_survey_as_completed(survey_response_id: int) -> int:
    """
    Marks a survey response as completed in the database.

    Args:
        survey_response_id (int): The ID of the survey response to mark as completed.

    Returns:
        int: The number of rows affected by the update.
    """
    query = """
        UPDATE survey_responses
        SET completed = True
        WHERE id = %s
    """
    logger.debug(f"Executing query: {query} with survey_response_id: {survey_response_id}")
    return execute_query(query, (survey_response_id,))
