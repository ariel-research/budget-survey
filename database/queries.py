import json
from logging_config import setup_logging
import logging
from .db import execute_query

setup_logging()

logger = logging.getLogger(__name__)

def create_user(user_id: int) -> int:
    """
    Inserts a new user into the users table.
    
    Args:
        user_id (int): The ID of the new user.
    
    Returns:
        The ID of the newly created user, or None if an error occurs.
    """
    query = "INSERT INTO users (id) VALUES (%s)"
    logger.debug("Inserting new user with id: %s", user_id)
    
    try:
        return execute_query(query, (user_id,))
    except Exception as e:
        logger.error("Error inserting new user: %s", str(e))
        return None

def create_survey_response(user_id: int, survey_id: int, optimal_allocation: list) -> int:
    """
    Inserts a new survey response into the survey_responses table.

    Args:
        user_id (int): The ID of the user submitting the survey.
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
    logger.debug("Inserting survey response for user_id: %s, survey_id: %s", user_id, survey_id)
    
    try:
        return execute_query(query, (user_id, survey_id, optimal_allocation_json))
    except Exception as e:
        logger.error("Error inserting survey response: %s", str(e))
        return None

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
    logger.debug("Inserting comparison pair for survey_response_id: %s, pair_number: %s", survey_response_id, pair_number)
    
    try:
        return execute_query(query, (survey_response_id, pair_number, option_1_json, option_2_json, user_choice))
    except Exception as e:
        logger.error("Error inserting comparison pair: %s", str(e))
        return None

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
    logger.debug("Marking survey as completed for survey_response_id: %s", survey_response_id)
    
    try:
        return execute_query(query, (survey_response_id,))
    except Exception as e:
        logger.error("Error marking survey as completed: %s", str(e))
        return 0  # Return 0 to indicate no rows affected

def user_exists(user_id: int) -> bool:
    """
    Checks if the user already exists in the database.

    Args:
        user_id (int): The ID of the user.

    Returns:
        bool: True if the user already exists in the database, False otherwise.
    """
    query = "SELECT EXISTS(SELECT 1 FROM users WHERE id = %s) as user_exists"
    logger.debug("Checking if user exists with user_id: %s", user_id)
    
    try:
        result = execute_query(query, (user_id,))
        return bool(result[0]['user_exists'])
    except Exception as e:
        logger.error("Error checking if user exists: %s", str(e))
        return False
    
# def survey_exists(survey_id: int) -> bool:
#     """
#     Checks if the survey already exists in the database.

#     Args:
#         survey_id (int) The ID of the survey.

#     Returns:
#         bool: True if the survey already exists in the database, False otherwise.
#     """
#     pass
