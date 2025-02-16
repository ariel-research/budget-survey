import json
import logging
from typing import Dict, List, Optional

from application.translations import get_current_language
from logging_config import setup_logging

from .db import execute_query

setup_logging()

logger = logging.getLogger(__name__)


def create_user(user_id: str) -> str:
    """
    Inserts a new user into the users table.

    Args:
        user_id (str): The ID of the new user.

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
    user_id: int,
    survey_id: int,
    optimal_allocation: list,
    user_comment: str,
    attention_check_failed: bool = False,
) -> int:
    """
    Inserts a new survey response into the survey_responses table.

    Args:
        user_id (int): The ID of the user submitting the survey.
        survey_id (int): The ID of the survey.
        optimal_allocation (list): The user optimal allocation in JSON format.
        user_comment (str): The user's comment on the survey.
        attention_check_failed (bool): Whether the user failed the attention check.

    Returns:
        int: The ID of the newly created survey response, or None if an error occurs.
    """
    query = """
        INSERT INTO survey_responses 
        (user_id, survey_id, optimal_allocation, user_comment, attention_check_failed)
        VALUES (%s, %s, %s, %s, %s)
    """
    optimal_allocation_json = json.dumps(optimal_allocation)
    logger.debug(
        "Inserting survey response for user_id: %s, survey_id: %s", user_id, survey_id
    )

    try:
        return execute_query(
            query,
            (
                user_id,
                survey_id,
                optimal_allocation_json,
                user_comment,
                attention_check_failed,
            ),
        )
    except Exception as e:
        logger.error("Error inserting survey response: %s", str(e))
        return None


def create_comparison_pair(
    survey_response_id: int,
    pair_number: int,
    option_1: list,
    option_2: list,
    user_choice: int,
    raw_user_choice: int,
    option1_strategy: str,
    option2_strategy: str,
) -> int:
    """
    Inserts a new comparison pair into the comparison_pairs table.

    Args:
        survey_response_id: The ID of the related survey response
        pair_number: The number of the comparison pair
        option_1: JSON data for the first option
        option_2: JSON data for the second option
        user_choice: The user's choice after swap adjustment
        raw_user_choice: The original user choice before swap adjustment
        option1_strategy: Strategy description for option 1
        option2_strategy: Strategy description for option 2

    Returns:
        int: The ID of the newly created comparison pair, or None if an error occurs
    """
    query = """
        INSERT INTO comparison_pairs (
            survey_response_id, pair_number, option_1, option_2, 
            user_choice, raw_user_choice, option1_strategy, option2_strategy
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    try:
        option_1_json = json.dumps(option_1)
        option_2_json = json.dumps(option_2)

        return execute_query(
            query,
            (
                survey_response_id,
                pair_number,
                option_1_json,
                option_2_json,
                user_choice,
                raw_user_choice,
                option1_strategy,
                option2_strategy,
            ),
        )
    except Exception as e:
        logger.error(f"Error inserting comparison pair: {str(e)}")
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


def user_exists(user_id: str) -> bool:
    """
    Checks if the user already exists in the database.

    Args:
        user_id (str): The ID of the user.

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
    Retrieves the name of an active survey in the current language.

    Args:
        survey_id (int): The ID of the survey to retrieve.

    Returns:
        str: The survey name with the following language fallback logic:
             - Returns name in current language if available
             - Falls back to Hebrew if current language is not available
             - Returns empty string if survey doesn't exist or on error

    Examples:
        >>> get_survey_name(1)  # Hebrew user
        'תקציב המדינה'
        >>> get_survey_name(1)  # English user, with both translations available
        'State Budget'
        >>> get_survey_name(1)  # English user, only Hebrew available
        'תקציב המדינה'
        >>> get_survey_name(999)  # Non-existent survey
        ''
    """
    query = "SELECT name FROM surveys WHERE id = %s AND active = TRUE"
    logger.debug("Retrieving name for survey_id: %s", survey_id)

    try:
        result = execute_query(query, (survey_id,), fetch_one=True)
        if not result:
            logger.warning("No active survey found with id: %s", survey_id)
            return ""

        name_column = result["name"]
        if not name_column:
            return ""

        name_dict = json.loads(name_column)
        current_lang = get_current_language()

        # Try current language, fallback to Hebrew
        return name_dict.get(current_lang, name_dict.get("he", ""))

    except json.JSONDecodeError as e:
        logger.error("Error decoding JSON for survey %s: %s", survey_id, str(e))
        return ""
    except Exception as e:
        logger.error("Error retrieving name for survey %s: %s", survey_id, str(e))
        return ""


def get_subjects(survey_id: int) -> List[str]:
    """
    Retrieves the subjects in the current language for a given survey.
    Falls back to Hebrew if translation not found.

    Args:
        survey_id (int): The ID of the survey.

    Returns:
        List[str]: A list of subjects in the current language, falling back to Hebrew
                  if the current language is not available. Returns an empty list if
                  the survey doesn't exist, is inactive, or if an error occurs.

    Example:
        >>> get_subjects(1)  # When language is 'en'
        ['Ministry of Education', 'Ministry of Health', 'Ministry of Defense']
        >>> get_subjects(1)  # When language is 'he' or translation missing
        ['משרד החינוך', 'משרד הבריאות', 'משרד הביטחון']
    """
    query = "SELECT subjects FROM surveys WHERE id = %s AND active = TRUE"
    logger.debug("Retrieving subjects for survey_id: %s", survey_id)

    try:
        result = execute_query(query, (survey_id,), fetch_one=True)
        if not result:
            logger.warning("No active survey found with id: %s", survey_id)
            return []

        subjects_column = result["subjects"]
        if not subjects_column:
            return []

        subjects_array = json.loads(subjects_column)
        current_lang = get_current_language()

        return [
            # Fallback to Hebrew
            subject.get(current_lang, subject.get("he", ""))
            for subject in subjects_array
        ]

    except json.JSONDecodeError as e:
        logger.error("Error decoding JSON for survey %s: %s", survey_id, str(e))
        return []
    except Exception as e:
        logger.error("Error retrieving subjects for survey %s: %s", survey_id, str(e))
        return []


def check_user_participation(user_id: int, survey_id: int) -> bool:
    """
    Checks if a user has successfully completed a specific survey.
    Counts also completions where attention checks were not passed.

    Args:
        user_id (int): The ID of the user.
        survey_id (int): The ID of the survey.

    Returns:
        bool: True if the user has successfully completed the survey, False otherwise.
    """
    query = """
    SELECT EXISTS(
        SELECT 1 FROM survey_responses
        WHERE user_id = %s 
        AND survey_id = %s 
        AND completed = TRUE
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


def retrieve_completed_survey_responses() -> List[Dict]:
    """
    Retrieves all successfully completed survey responses.
    Excludes responses where attention checks failed.

    Returns:
        list: A list of dictionaries containing raw survey response data.
              Only includes responses where attention checks were passed.
    """
    query = """
    SELECT 
        sr.id AS survey_response_id,
        sr.user_id,
        sr.survey_id,
        sr.optimal_allocation,
        sr.completed,
        sr.created_at AS response_created_at,
        COALESCE(sr.user_comment, '') as user_comment,
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
        AND sr.attention_check_failed = FALSE
    ORDER BY 
        sr.id, cp.pair_number
    """
    logger.debug("Retrieving all successfully completed survey responses")

    try:
        results = execute_query(query)
        if results:
            # Additional data cleaning at Python level
            for row in results:
                # Ensure user_comment is always a string
                row["user_comment"] = str(row["user_comment"] or "").strip()

            logger.debug(f"Retrieved {len(results)} rows of completed survey data")
            return results
        else:
            logger.warning("No completed survey responses found")
            return []
    except Exception as e:
        logger.error(f"Error retrieving completed survey responses: {str(e)}")
        return []


def get_latest_survey_timestamp() -> float:
    """
    Retrieves the timestamp of the latest completed survey response.

    Returns:
        float: Unix timestamp of the latest completed survey response,
              or 0 if no completed surveys exist or if an error occurs.
    """
    query = """
        SELECT MAX(created_at) as latest
        FROM survey_responses 
        WHERE completed = TRUE
    """
    logger.debug("Retrieving timestamp of latest completed survey response")

    try:
        result = execute_query(query)
        if result and result[0]["latest"]:
            return result[0]["latest"].timestamp()
        else:
            logger.warning("No completed survey responses found")
            return 0
    except Exception as e:
        logger.error(f"Error retrieving latest survey timestamp: {str(e)}")
        return 0


def retrieve_user_survey_choices() -> List[Dict]:
    """
    Retrieves survey choices data organized by user and survey.
    Only includes choices from successfully completed surveys where attention checks passed.

    Returns:
        List[Dict]: List of dictionaries containing survey choice data.
                   Each dictionary contains user_id, survey_id, and choice details.
                   Only includes data from surveys where attention checks were passed.
    """
    query = """
    SELECT 
        sr.user_id,
        sr.survey_id,
        sr.optimal_allocation,
        cp.pair_number,
        cp.option_1,
        cp.option_2,
        cp.user_choice,
        cp.raw_user_choice,
        cp.option1_strategy,
        cp.option2_strategy
    FROM 
        survey_responses sr
    JOIN 
        comparison_pairs cp ON sr.id = cp.survey_response_id
    WHERE
        sr.completed = TRUE
        AND sr.attention_check_failed = FALSE
    ORDER BY 
        sr.user_id,
        sr.survey_id,
        cp.pair_number
    """

    try:
        results = execute_query(query)
        if results:
            logger.debug(f"Retrieved choices data for {len(results)} comparison pairs")
            return results
        logger.warning("No survey choices data found")
        return []
    except Exception as e:
        logger.error(f"Error retrieving survey choices: {str(e)}")
        return []


def get_survey_pair_generation_config(survey_id: int) -> Optional[dict]:
    """
    Get pair generation configuration for a survey.

    Args:
        survey_id: ID of the survey

    Returns:
        Dict containing strategy configuration or None if not found
    """
    query = "SELECT pair_generation_config FROM surveys WHERE id = %s AND active = TRUE"
    logger.debug(f"Retrieving pair generation config for survey: {survey_id}")

    try:
        result = execute_query(query, (survey_id,), fetch_one=True)
        if not result:
            logger.warning(f"No configuration found for survey: {survey_id}")
            return None

        config_str = result.get("pair_generation_config")
        if not config_str:
            return None

        # Parse JSON string into dict
        config = json.loads(config_str)
        logger.debug(f"Retrieved config: {config}")
        return config

    except json.JSONDecodeError as e:
        logger.error(f"Error parsing pair generation config JSON: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error retrieving pair generation config: {str(e)}")
        return None


def get_active_surveys() -> List[Dict]:
    """
    Retrieve all active surveys with their configurations.

    Returns:
        List[Dict]: List of active surveys with their details.
        Each dict contains: id, name, description, pair_generation_config
    """
    query = """
        SELECT id, name, description, pair_generation_config 
        FROM surveys 
        WHERE active = TRUE 
        ORDER BY id
    """
    logger.debug("Retrieving active surveys")

    try:
        results = execute_query(query)
        logger.info(f"Retrieved {len(results)} active surveys")
        return results
    except Exception as e:
        logger.error(f"Error retrieving active surveys: {str(e)}")
        return []
