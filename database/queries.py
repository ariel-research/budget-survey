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
    option1_differences: list = None,
    option2_differences: list = None,
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
        option1_differences: Optional differences vector for option 1
                           (for cyclic shift)
        option2_differences: Optional differences vector for option 2
                           (for cyclic shift)

    Returns:
        int: The ID of the newly created comparison pair, or None if an error occurs
    """
    query = """
        INSERT INTO comparison_pairs (
            survey_response_id, pair_number, option_1, option_2, 
            user_choice, raw_user_choice, option1_strategy, option2_strategy,
            option1_differences, option2_differences
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    try:
        option_1_json = json.dumps(option_1)
        option_2_json = json.dumps(option_2)
        option1_differences_json = (
            json.dumps(option1_differences) if option1_differences is not None else None
        )
        option2_differences_json = (
            json.dumps(option2_differences) if option2_differences is not None else None
        )

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
                option1_differences_json,
                option2_differences_json,
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


def get_survey_field(survey_id: int, field_name: str) -> str:
    """
    Retrieves a JSON field from an active survey in the current language.

    Args:
        survey_id (int): The ID of the survey to retrieve.
        field_name (str): The field to retrieve (e.g., 'title', 'description')

    Returns:
        str: The field value with language fallback logic
    """
    query = f"""
        SELECT s.story_code, st.{field_name} 
        FROM surveys s
        JOIN stories st ON s.story_code = st.code
        WHERE s.id = %s AND s.active = TRUE
    """
    logger.debug(f"Retrieving {field_name} for survey_id: {survey_id}")

    try:
        result = execute_query(query, (survey_id,), fetch_one=True)
        if not result:
            logger.info(f"No active survey found with id: {survey_id}")
            return None

        field_json = result[field_name]
        if not field_json:
            return None

        field_dict = json.loads(field_json)
        current_lang = get_current_language()

        # Try current language, fallback to Hebrew
        return field_dict.get(current_lang, field_dict.get("he", ""))

    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON for survey {survey_id}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error retrieving {field_name} for survey {survey_id}: {str(e)}")
        return None


def get_survey_name(survey_id: int) -> str:
    """
    Retrieves the name of an active survey in the current language.
    """
    result = get_survey_field(survey_id, "title")
    return result if result is not None else ""


def get_survey_description(survey_id: int) -> str:
    """
    Retrieves the description of an active survey in the current language.
    """
    return get_survey_field(survey_id, "description")


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
    query = """
        SELECT st.subjects
        FROM surveys s
        JOIN stories st ON s.story_code = st.code
        WHERE s.id = %s AND s.active = TRUE
    """
    logger.debug("Retrieving subjects for survey_id: %s", survey_id)

    try:
        result = execute_query(query, (survey_id,), fetch_one=True)
        if not result:
            logger.info("No active survey found with id: %s", survey_id)
            return []

        subjects_json = result["subjects"]
        if not subjects_json:
            return []

        subjects_array = json.loads(subjects_json)
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
        cp.user_choice,
        cp.option1_differences,
        cp.option2_differences
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

                # Parse option1_differences if it exists and is not None
                if row.get("option1_differences"):
                    try:
                        row["option1_differences"] = json.loads(
                            row["option1_differences"]
                        )
                    except (json.JSONDecodeError, TypeError):
                        row["option1_differences"] = None

                # Parse option2_differences if it exists and is not None
                if row.get("option2_differences"):
                    try:
                        row["option2_differences"] = json.loads(
                            row["option2_differences"]
                        )
                    except (json.JSONDecodeError, TypeError):
                        row["option2_differences"] = None

            logger.debug(f"Retrieved {len(results)} rows of completed survey data")
            return results
        else:
            logger.info("No completed survey responses found")
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
            logger.info("No completed survey responses found")
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
        sr.created_at as response_created_at,
        cp.pair_number,
        cp.option_1,
        cp.option_2,
        cp.user_choice,
        cp.raw_user_choice,
        cp.option1_strategy,
        cp.option2_strategy,
        cp.option1_differences,
        cp.option2_differences
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
            # Parse JSON fields for differences
            for result in results:
                # Parse option1_differences if it exists and is not None
                if result.get("option1_differences"):
                    try:
                        result["option1_differences"] = json.loads(
                            result["option1_differences"]
                        )
                    except (json.JSONDecodeError, TypeError):
                        result["option1_differences"] = None

                # Parse option2_differences if it exists and is not None
                if result.get("option2_differences"):
                    try:
                        result["option2_differences"] = json.loads(
                            result["option2_differences"]
                        )
                    except (json.JSONDecodeError, TypeError):
                        result["option2_differences"] = None

            logger.debug(f"Retrieved choices data for {len(results)} comparison pairs")
            return results
        logger.info("No survey choices data found")
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
            logger.info(f"No configuration found for survey: {survey_id}")
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
    Retrieve all active surveys with their configurations and story details.

    Returns:
        List[Dict]: List of active surveys with their details.
        Each dict contains: id, pair_generation_config, story_code, and
        story details (title, description, subjects).
    """
    query = """
        SELECT s.id, s.story_code, s.pair_generation_config, 
               st.title, st.description, st.subjects
        FROM surveys s
        JOIN stories st ON s.story_code = st.code
        WHERE s.active = TRUE 
        ORDER BY s.id
    """
    logger.debug("Retrieving active surveys")

    try:
        results = execute_query(query)
        if not results:
            logger.info("No active surveys found")
            return []

        # Process the results - parse JSON fields
        processed_results = []
        for result in results:
            processed_result = {
                "id": result["id"],
                "story_code": result["story_code"],
                "pair_generation_config": (
                    json.loads(result["pair_generation_config"])
                    if result["pair_generation_config"]
                    else None
                ),
                "title": json.loads(result["title"]) if result["title"] else {},
                "description": (
                    json.loads(result["description"]) if result["description"] else {}
                ),
                "subjects": (
                    json.loads(result["subjects"]) if result["subjects"] else []
                ),
            }
            processed_results.append(processed_result)

        logger.info(f"Retrieved {len(processed_results)} active surveys")
        return processed_results
    except Exception as e:
        logger.error(f"Error retrieving active surveys: {str(e)}")
        return []


def get_story(code: str) -> Optional[Dict]:
    """
    Retrieves a story by its code.

    Args:
        code (str): The unique code of the story to retrieve.

    Returns:
        Optional[Dict]: Dictionary containing the story data or None if not found.
    """
    query = "SELECT * FROM stories WHERE code = %s"
    logger.debug(f"Retrieving story with code: {code}")

    try:
        result = execute_query(query, (code,), fetch_one=True)
        if not result:
            logger.info(f"No story found with code: {code}")
            return None

        # Parse JSON fields
        for json_field in ["title", "description", "subjects"]:
            if result[json_field]:
                result[json_field] = json.loads(result[json_field])

        return result
    except Exception as e:
        logger.error(f"Error retrieving story with code {code}: {str(e)}")
        return None


def get_all_stories() -> List[Dict]:
    """
    Retrieves all stories from the database.

    Returns:
        List[Dict]: List of dictionaries containing story data.
    """
    query = "SELECT * FROM stories ORDER BY id"
    logger.debug("Retrieving all stories")

    try:
        results = execute_query(query)
        if not results:
            logger.info("No stories found")
            return []

        # Parse JSON fields for each result
        for result in results:
            for json_field in ["title", "description", "subjects"]:
                if result[json_field]:
                    result[json_field] = json.loads(result[json_field])

        logger.info(f"Retrieved {len(results)} stories")
        return results
    except Exception as e:
        logger.error(f"Error retrieving stories: {str(e)}")
        return []


def create_story(
    code: str, title: Dict, description: Dict, subjects: List[Dict]
) -> int:
    """
    Creates a new story in the database.

    Args:
        code (str): Unique identifier for the story
        title (Dict): Multilingual title {"en": "English Title", "he": "Hebrew Title"}
        description (Dict): Multilingual description
        subjects (List[Dict]): List of multilingual subjects

    Returns:
        int: ID of the newly created story or None if an error occurs
    """
    query = """
        INSERT INTO stories (code, title, description, subjects)
        VALUES (%s, %s, %s, %s)
    """
    logger.debug(f"Creating new story with code: {code}")

    try:
        # Convert Python objects to JSON strings for storage
        title_json = json.dumps(title)
        description_json = json.dumps(description)
        subjects_json = json.dumps(subjects)

        return execute_query(query, (code, title_json, description_json, subjects_json))
    except Exception as e:
        logger.error(f"Error creating story: {str(e)}")
        return None


def create_survey(
    story_code: str, pair_generation_config: Dict, active: bool = True
) -> int:
    """
    Creates a new survey in the database.

    Args:
        story_code (str): Code of the story this survey is based on
        pair_generation_config (Dict): Configuration for pair generation
        active (bool): Whether this survey is active

    Returns:
        int: ID of the newly created survey or None if an error occurs
    """
    query = """
        INSERT INTO surveys (story_code, pair_generation_config, active)
        VALUES (%s, %s, %s)
    """
    logger.debug(f"Creating new survey with story_code: {story_code}")

    try:
        # Convert Python dict to JSON string for storage
        config_json = json.dumps(pair_generation_config)

        return execute_query(query, (story_code, config_json, active))
    except Exception as e:
        logger.error(f"Error creating survey: {str(e)}")
        return None


def blacklist_user(user_id: str, survey_id: int) -> bool:
    """
    Blacklists a user from participating in future surveys.

    Args:
        user_id (str): The ID of the user to blacklist.
        survey_id (int): The ID of the survey where the user failed attention checks.

    Returns:
        bool: True if the user was successfully blacklisted, False otherwise.
    """
    query = """
        UPDATE users
        SET blacklisted = TRUE, 
            blacklisted_at = CURRENT_TIMESTAMP,
            failed_survey_id = %s
        WHERE id = %s
    """
    logger.info(
        f"Blacklisting user {user_id} due to failed attention check in survey {survey_id}"
    )

    try:
        result = execute_query(query, (survey_id, user_id))
        return result > 0
    except Exception as e:
        logger.error(f"Error blacklisting user {user_id}: {str(e)}")
        return False


def is_user_blacklisted(user_id: str) -> bool:
    """
    Checks if a user is blacklisted from participating in surveys.

    Args:
        user_id (str): The ID of the user to check.

    Returns:
        bool: True if the user is blacklisted, False otherwise.
    """
    query = """
        SELECT blacklisted 
        FROM users 
        WHERE id = %s
    """
    logger.debug(f"Checking if user {user_id} is blacklisted")

    try:
        result = execute_query(query, (user_id,), fetch_one=True)
        return result and result.get("blacklisted", False)
    except Exception as e:
        logger.error(f"Error checking if user {user_id} is blacklisted: {str(e)}")
        return False


def get_blacklisted_users() -> List[Dict]:
    """
    Retrieves all blacklisted users with their blacklist details.

    Returns:
        List[Dict]: A list of dictionaries containing blacklisted user data.
        Each dictionary contains user_id, blacklisted_at, and failed_survey_id.
    """
    query = """
        SELECT u.id, u.blacklisted_at, u.failed_survey_id, 
               s.story_code, st.title 
        FROM users u
        LEFT JOIN surveys s ON u.failed_survey_id = s.id
        LEFT JOIN stories st ON s.story_code = st.code
        WHERE u.blacklisted = TRUE
        ORDER BY u.blacklisted_at DESC
    """
    logger.debug("Retrieving all blacklisted users")

    try:
        results = execute_query(query)
        processed_results = []

        for result in results:
            # Process title field if it exists
            title = None
            if result.get("title"):
                title_json = json.loads(result["title"])
                current_lang = get_current_language()
                title = title_json.get(current_lang, title_json.get("he", ""))

            processed_result = {
                "user_id": result["id"],
                "blacklisted_at": result["blacklisted_at"],
                "failed_survey_id": result["failed_survey_id"],
                "story_code": result.get("story_code"),
                "survey_title": title,
            }
            processed_results.append(processed_result)

        return processed_results
    except Exception as e:
        logger.error(f"Error retrieving blacklisted users: {str(e)}")
        return []


def get_users_from_view(view_name: str, survey_id: Optional[int] = None) -> List[str]:
    """
    Retrieves user IDs from a specified SQL view, optionally filtered by survey ID.

    Args:
        view_name (str): Name of the view to query (must be a valid view name)
        survey_id (Optional[int]): If provided, will filter users by this survey ID

    Returns:
        List[str]: List of user IDs found in the view
    """
    # Validate view name against allowed patterns to prevent SQL injection
    allowed_views = [
        "v_users_preferring_weighted_vectors",
        "v_users_preferring_rounded_weighted_vectors",
        "v_users_preferring_any_weighted_vectors",
    ]

    if view_name not in allowed_views:
        logger.warning(f"Invalid view name requested: {view_name}")
        return []

    query = f"""
        SELECT DISTINCT user_id
        FROM {view_name}
        WHERE 1=1
    """

    params = []

    # Add survey_id condition if specified
    if survey_id is not None:
        query += " AND survey_id = %s"
        params.append(survey_id)

    log_msg = f"Retrieving users from view {view_name}"
    if survey_id:
        log_msg += f" for survey {survey_id}"
    logger.debug(log_msg)

    try:
        results = execute_query(query, tuple(params) if params else None)
        if results:
            user_ids = [result["user_id"] for result in results]
            logger.debug(f"Retrieved {len(user_ids)} users from view {view_name}")

            # Additional log to help diagnose filter issues
            if survey_id is not None:
                if user_ids:
                    user_list = ", ".join(user_ids[:5])
                    if len(user_ids) > 5:
                        user_list += f"... (+{len(user_ids)-5} more)"
                    logger.debug(
                        f"Users for survey {survey_id} in view {view_name}: {user_list}"
                    )
                else:
                    # Check if there are ANY users in this view from any survey
                    check_query = (
                        f"SELECT COUNT(DISTINCT user_id) as count FROM {view_name}"
                    )
                    check_result = execute_query(check_query, fetch_one=True)
                    total_count = check_result.get("count", 0) if check_result else 0

                    if total_count > 0:
                        logger.info(
                            f"View {view_name} has {total_count} total users across all surveys, "
                            f"but none for survey {survey_id}"
                        )
                    else:
                        logger.info(
                            f"View {view_name} is empty (no users in any survey)"
                        )

            return user_ids

        if survey_id is not None:
            logger.info(f"No users found in view {view_name} for survey {survey_id}")
            return []
        else:
            logger.info(f"No users found in view {view_name}")
            return []
    except Exception as e:
        logger.error(f"Error retrieving users from view {view_name}: {str(e)}")
        return []


def get_survey_response_counts(survey_id: int) -> Optional[Dict[str, int]]:
    """
    Checks the number of responses and unique users for a given survey.

    Args:
        survey_id (int): The ID of the survey.

    Returns:
        Optional[Dict[str, int]]: A dictionary with 'count' and 'unique_users'
                                   or None if an error occurs or no responses.
    """
    query = """
        SELECT COUNT(*) as count, COUNT(DISTINCT user_id) as unique_users
        FROM survey_responses sr
        WHERE sr.survey_id = %s AND sr.completed = TRUE AND sr.attention_check_failed = FALSE
    """
    try:
        results = execute_query(query, (survey_id,), fetch_one=True)
        if results and results.get("count", 0) > 0:
            return {"count": results["count"], "unique_users": results["unique_users"]}
        return None
    except Exception as e:
        logger.error(
            f"Error checking survey response counts for survey {survey_id}: {str(e)}"
        )
        return None


def get_user_participation_overview() -> List[Dict]:
    """
    Get comprehensive participation statistics for all users who have completed surveys.

    Returns:
        List[Dict]: A list of dictionaries containing user participation data.
        Each dictionary contains:
        - user_id: The user's ID
        - successful_surveys_count: Number of completed surveys without attention check failure
        - successful_survey_ids: Comma-separated list of successful survey IDs
        - failed_surveys_count: Number of completed surveys with attention check failure
        - failed_survey_ids: Comma-separated list of failed survey IDs
        - last_activity: Most recent created_at timestamp across all surveys
    """
    query = """
        SELECT 
            sr.user_id,
            SUM(CASE WHEN sr.completed = TRUE AND sr.attention_check_failed = FALSE THEN 1 ELSE 0 END) as successful_surveys_count,
            GROUP_CONCAT(
                CASE WHEN sr.completed = TRUE AND sr.attention_check_failed = FALSE 
                THEN sr.survey_id ELSE NULL END 
                ORDER BY sr.survey_id
            ) as successful_survey_ids,
            SUM(CASE WHEN sr.completed = TRUE AND sr.attention_check_failed = TRUE THEN 1 ELSE 0 END) as failed_surveys_count,
            GROUP_CONCAT(
                CASE WHEN sr.completed = TRUE AND sr.attention_check_failed = TRUE 
                THEN sr.survey_id ELSE NULL END 
                ORDER BY sr.survey_id
            ) as failed_survey_ids,
            MAX(sr.created_at) as last_activity
        FROM survey_responses sr
        WHERE sr.completed = TRUE
        GROUP BY sr.user_id
        HAVING (successful_surveys_count > 0 OR failed_surveys_count > 0)
        ORDER BY last_activity DESC
    """

    logger.debug("Retrieving user participation overview")

    try:
        results = execute_query(query)
        processed_results = []

        for result in results:
            processed_result = {
                "user_id": result["user_id"],
                "successful_surveys_count": result["successful_surveys_count"],
                "successful_survey_ids": result["successful_survey_ids"] or "",
                "failed_surveys_count": result["failed_surveys_count"],
                "failed_survey_ids": result["failed_survey_ids"] or "",
                "last_activity": result["last_activity"],
            }
            processed_results.append(processed_result)

        logger.debug(f"Retrieved participation data for {len(processed_results)} users")
        return processed_results

    except Exception as e:
        logger.error(f"Error retrieving user participation overview: {str(e)}")
        return []
