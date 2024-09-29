import json
import logging

from logging_config import setup_logging

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


def create_survey_response(
    user_id: int, survey_id: int, optimal_allocation: list
) -> int:
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
    logger.debug(
        "Inserting survey response for user_id: %s, survey_id: %s", user_id, survey_id
    )

    try:
        return execute_query(query, (user_id, survey_id, optimal_allocation_json))
    except Exception as e:
        logger.error("Error inserting survey response: %s", str(e))
        return None


def create_comparison_pair(
    survey_response_id: int,
    pair_number: int,
    option_1: list,
    option_2: list,
    user_choice: int,
) -> int:
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
    logger.debug(
        "Inserting comparison pair for survey_response_id: %s, pair_number: %s",
        survey_response_id,
        pair_number,
    )

    try:
        return execute_query(
            query,
            (
                survey_response_id,
                pair_number,
                option_1_json,
                option_2_json,
                user_choice,
            ),
        )
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
    logger.debug(
        "Marking survey as completed for survey_response_id: %s", survey_response_id
    )

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
        return bool(result[0]["user_exists"])
    except Exception as e:
        logger.error("Error checking if user exists: %s", str(e))
        return False


def get_survey_name(survey_id: int) -> str:
    """
    Retrieves the name of a survey given its ID.

    Args:
        survey_id (int): The ID of the survey.

    Returns:
        str: The name of the survey, or an empty string if the survey doesn't exist or an error occurs.
    """
    query = "SELECT name FROM surveys WHERE id = %s AND active = TRUE"
    logger.debug(f"Retrieving name for survey_id: {survey_id}")

    try:
        result = execute_query(query, (survey_id,))
        if result and len(result) > 0:
            return result[0]["name"]
        else:
            logger.warning(f"No active survey found with id: {survey_id}")
            return ""
    except Exception as e:
        logger.error(f"Error retrieving name for survey {survey_id}: {str(e)}")
        return ""


def get_subjects(survey_id: int) -> list:
    """
    Retrieves the subjects for a given survey from the database.

    Args:
        survey_id (int): The ID of the survey.

    Returns:
        list: A list of subjects for the survey, or an empty list if the survey doesn't exist or an error occurs.
    """
    query = "SELECT subjects FROM surveys WHERE id = %s AND active = TRUE"
    logger.debug("Retrieving subjects for survey_id: %s", survey_id)

    try:
        result = execute_query(query, (survey_id,))
        if result and len(result) > 0:
            subjects_json = result[0]["subjects"]
            return json.loads(subjects_json)
        else:
            logger.warning(f"No active survey found with id: {survey_id}")
            return []
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON for survey {survey_id}: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Error retrieving subjects for survey {survey_id}: {str(e)}")
        return []


def check_user_participation(user_id: int, survey_id: int) -> bool:
    """
    Checks if a user has participated in a specific survey.

    Args:
        user_id (int): The ID of the user.
        survey_id (int): The ID of the survey.

    Returns:
        bool: True if the user has participated in the survey, False otherwise.
    """
    query = """
    SELECT EXISTS(
        SELECT 1 FROM survey_responses
        WHERE user_id = %s AND survey_id = %s AND completed = TRUE
    ) as participated
    """
    logger.debug(
        f"Checking participation for user_id: {user_id}, survey_id: {survey_id}"
    )

    try:
        result = execute_query(query, (user_id, survey_id))
        return bool(result[0]["participated"])
    except Exception as e:
        logger.error(f"Error checking user participation: {str(e)}")
        return False


def retrieve_completed_survey_responses():
    """
    Retrieves all completed survey responses, including user choices and both options for each comparison.

    Returns:
        list: A list of dictionaries containing raw survey response data, or an empty list if an error occurs.
    """
    query = """
    SELECT 
        sr.id AS survey_response_id,
        sr.user_id,
        sr.survey_id,
        sr.optimal_allocation,
        sr.completed,
        sr.created_at AS response_created_at,
        cp.pair_number,
        cp.option_1,
        cp.option_2,
        cp.user_choice
    FROM 
        survey_responses sr
    JOIN 
        comparison_pairs cp ON sr.id = cp.survey_response_id
    WHERE
        sr.completed = TRUE
    ORDER BY 
        sr.id, cp.pair_number
    """
    logger.debug("Retrieving all completed survey responses and comparison pairs")

    try:
        results = execute_query(query)
        if results:
            logger.info(f"Retrieved {len(results)} rows of completed survey data")
            return results
        else:
            logger.warning("No completed survey responses found")
            return []
    except Exception as e:
        logger.error(f"Error retrieving completed survey responses: {str(e)}")
        return []
