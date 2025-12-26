import json
import logging
from typing import Dict, List, Optional, Tuple

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
    user_id: str,
    survey_id: int,
    optimal_allocation: list,
    user_comment: str,
    attention_check_failed: bool = False,
    unsuitable_for_strategy: bool = False,
) -> int:
    """
    Inserts a new survey response into the survey_responses table.

    Args:
        user_id (str): The ID of the user submitting the survey.
        survey_id (int): The ID of the survey.
        optimal_allocation (list): The user optimal allocation in JSON format.
        user_comment (str): The user's comment on the survey.
        attention_check_failed (bool): Whether the user failed the attention check.
        unsuitable_for_strategy (bool): Whether user was unsuitable for strategy.

    Returns:
        int: The ID of the newly created survey response, or None if an error occurs.
    """
    query = """
        INSERT INTO survey_responses 
        (user_id, survey_id, optimal_allocation, user_comment, attention_check_failed, unsuitable_for_strategy)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    optimal_allocation_json = json.dumps(optimal_allocation)
    logger.debug(
        f"Inserting survey response for user_id: {user_id}, survey_id: {survey_id}, "
        f"unsuitable: {unsuitable_for_strategy}"
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
                unsuitable_for_strategy,
            ),
        )
    except Exception as e:
        logger.error("Error inserting survey response: %s", str(e))
        return None


def user_already_responded_to_survey(user_id: str, survey_id: int) -> bool:
    """
    Check if a user has already responded to a specific survey.

    Args:
        user_id (str): The user's identifier
        survey_id (int): The survey ID

    Returns:
        bool: True if user already has a response for this survey, False otherwise
    """
    query = (
        "SELECT id FROM survey_responses WHERE user_id = %s AND survey_id = %s LIMIT 1"
    )

    try:
        result = execute_query(query, (user_id, survey_id), fetch_one=True)
        has_response = result is not None
        logger.debug(
            f"User {user_id} response check for survey {survey_id}: {has_response}"
        )
        return has_response
    except Exception as e:
        logger.error(f"Error checking user response: {str(e)}")
        return False


def create_early_awareness_failure(
    user_id: str,
    survey_id: int,
    optimal_allocation: list,
    pts_value: int,
) -> int:
    """
    Records an early awareness check failure (detected by frontend before survey completion).

    Args:
        user_id (str): The ID of the user.
        survey_id (int): The ID of the survey.
        optimal_allocation (list): The user's budget vector.
        pts_value (int): Awareness failure code (1=first awareness, 2=second awareness).

    Returns:
        int: The ID of the newly created survey response, or None if an error occurs.
    """
    query = """
        INSERT INTO survey_responses 
        (user_id, survey_id, optimal_allocation, completed, attention_check_failed, pts_value)
        VALUES (%s, %s, %s, FALSE, TRUE, %s)
    """
    optimal_allocation_json = json.dumps(optimal_allocation)
    logger.debug(
        "Inserting early awareness failure for user_id: %s, survey_id: %s, pts_value: %s",
        user_id,
        survey_id,
        pts_value,
    )

    try:
        return execute_query(
            query,
            (
                user_id,
                survey_id,
                optimal_allocation_json,
                pts_value,
            ),
        )
    except Exception as e:
        logger.error("Error inserting early awareness failure: %s", str(e))
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
    generation_metadata: dict = None,
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
        generation_metadata: Optional metadata about pair generation
                           (e.g., relaxation level, epsilon for rank-based strategies)

    Returns:
        int: The ID of the newly created comparison pair, or None if an error occurs
    """
    query = """
        INSERT INTO comparison_pairs (
            survey_response_id, pair_number, option_1, option_2, 
            user_choice, raw_user_choice, option1_strategy, option2_strategy,
            option1_differences, option2_differences, generation_metadata
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
        generation_metadata_json = (
            json.dumps(generation_metadata) if generation_metadata is not None else None
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
                generation_metadata_json,
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


def get_survey_awareness_pts(survey_id: int) -> Optional[Dict[str, str]]:
    """
    Retrieve per-survey awareness PTS tokens if present.

    Args:
        survey_id (int): The ID of the survey.

    Returns:
        Optional[Dict[str, str]]: A dictionary with optional 'first'/'second' tokens,
        or empty dict if not set/malformed, or None if survey inactive/missing.
    """
    query = """
        SELECT awareness_pts
        FROM surveys
        WHERE id = %s AND active = TRUE
    """
    logger.debug("Retrieving awareness PTS tokens for survey_id: %s", survey_id)

    try:
        result = execute_query(query, (survey_id,), fetch_one=True)
        if not result:
            logger.info("No active survey found with id: %s", survey_id)
            return None

        pts_json = result.get("awareness_pts")
        if not pts_json:
            return {}

        try:
            pts_data = json.loads(pts_json)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(
                "Malformed awareness_pts for survey %s: %s", survey_id, str(e)
            )
            return {}

        if not isinstance(pts_data, dict):
            logger.warning(
                "Unexpected awareness_pts type for survey %s: %s",
                survey_id,
                type(pts_data),
            )
            return {}

        tokens = {}
        for key in ("first", "second"):
            val = pts_data.get(key)
            if isinstance(val, str) and val:
                tokens[key] = val

        return tokens
    except Exception as e:
        logger.error(
            "Error retrieving awareness_pts for survey %s: %s", survey_id, str(e)
        )
        return {}


def check_user_participation(user_id: str, survey_id: int) -> bool:
    """
    Checks if a user has successfully completed a specific survey.
    Counts also completions where attention checks were not passed.

    Args:
        user_id (str): The ID of the user.
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
        sr.id as survey_response_id,
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
        cp.option2_differences,
        cp.generation_metadata
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
            # Parse JSON fields and enrich with strategy metadata for
            # asymmetric_loss_distribution rendering
            import re

            type_re = re.compile(r"Type\s*([AB])", re.IGNORECASE)
            mag_re = re.compile(r"\((\d+)\s*,\s*Type\s*[AB]\)")

            for result in results:
                # Parse differences if present
                if result.get("option1_differences"):
                    try:
                        result["option1_differences"] = json.loads(
                            result["option1_differences"]
                        )
                    except (json.JSONDecodeError, TypeError):
                        result["option1_differences"] = None

                if result.get("option2_differences"):
                    try:
                        result["option2_differences"] = json.loads(
                            result["option2_differences"]
                        )
                    except (json.JSONDecodeError, TypeError):
                        result["option2_differences"] = None

                # Parse generation_metadata if present
                if result.get("generation_metadata"):
                    try:
                        result["generation_metadata"] = json.loads(
                            result["generation_metadata"]
                        )
                    except (json.JSONDecodeError, TypeError):
                        result["generation_metadata"] = None

                # Try to enrich with pair_type, magnitude, target_category
                try:
                    opt_alloc = json.loads(result.get("optimal_allocation", "[]"))
                except (json.JSONDecodeError, TypeError):
                    opt_alloc = []

                try:
                    v1 = json.loads(result.get("option_1", "[]"))
                except (json.JSONDecodeError, TypeError):
                    v1 = []
                try:
                    v2 = json.loads(result.get("option_2", "[]"))
                except (json.JSONDecodeError, TypeError):
                    v2 = []

                s1 = str(result.get("option1_strategy", ""))
                s2 = str(result.get("option2_strategy", ""))

                m = mag_re.search(s1) or mag_re.search(s2)
                t = type_re.search(s1) or type_re.search(s2)

                if m:
                    try:
                        result["magnitude"] = int(m.group(1))
                    except Exception:
                        pass
                if t:
                    result["pair_type"] = t.group(1).upper()

                # Infer target index from vectors when possible
                if opt_alloc and v1 and v2 and len(opt_alloc) == 3:
                    try:
                        d1 = [a - b for a, b in zip(v1, opt_alloc)]
                        d2 = [a - b for a, b in zip(v2, opt_alloc)]

                        # Choose the index with the largest total movement
                        # relative to the ideal allocation. For Type A pairs
                        # the target index changes by 2x while the others by x,
                        # so argmax(abs(d1)+abs(d2)) reliably identifies target.
                        inferred = max(
                            range(len(opt_alloc)),
                            key=lambda i: abs(d1[i]) + abs(d2[i]),
                        )
                        result["target_category"] = int(inferred)
                    except Exception:
                        pass

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


def get_survey_instructions(survey_id: int) -> Optional[str]:
    """
    Get custom pair instructions for a survey from pair_generation_config.

    Args:
        survey_id: ID of the survey

    Returns:
        Custom instructions text in current language, or None if not found
    """
    from application.translations import get_current_language

    query = "SELECT pair_generation_config FROM surveys WHERE id = %s AND active = TRUE"
    logger.debug(f"Retrieving pair instructions for survey: {survey_id}")

    try:
        result = execute_query(query, (survey_id,), fetch_one=True)
        if not result or not result.get("pair_generation_config"):
            logger.debug(f"No pair generation config found for survey: {survey_id}")
            return None

        config_json = result.get("pair_generation_config")
        if not config_json:
            return None

        # Parse JSON config and extract pair_instructions
        try:
            config = json.loads(config_json)
            instructions = config.get("pair_instructions")

            if not instructions:
                logger.debug(
                    f"No pair_instructions found in config for survey {survey_id}"
                )
                return None

            current_lang = get_current_language()
            custom_instruction = instructions.get(current_lang)

            if custom_instruction:
                logger.debug(
                    f"Found custom instruction for survey {survey_id} in {current_lang}"
                )
                return custom_instruction
            else:
                logger.debug(
                    f"No instruction found for language {current_lang} in survey {survey_id}"
                )
                return None

        except json.JSONDecodeError as e:
            logger.error(
                f"Error parsing pair generation config JSON for survey {survey_id}: {str(e)}"
            )
            return None

    except Exception as e:
        logger.error(
            f"Error retrieving pair instructions for survey {survey_id}: {str(e)}"
        )
        return None


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


def get_user_participation_overview(user_ids: Optional[List[str]] = None) -> List[Dict]:
    """
    Get comprehensive participation statistics for all users who have completed surveys.

    Args:
        user_ids (Optional[List[str]]): If provided, filter results to these users only

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
    """

    params = []

    # Add user_ids filter if provided
    if user_ids is not None:
        # Create placeholders for the IN clause
        placeholders = ", ".join(["%s"] * len(user_ids))
        query += f" AND sr.user_id IN ({placeholders})"
        params.extend(user_ids)

    query += """
        GROUP BY sr.user_id
        HAVING (successful_surveys_count > 0 OR failed_surveys_count > 0)
        ORDER BY last_activity DESC
    """

    logger.debug(
        f"Retrieving user participation overview{' for specific users' if user_ids else ''}"
    )

    try:
        results = execute_query(query, tuple(params) if params else None)
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


def get_paginated_user_ids(
    page: int, per_page: int, sort_by: str = "last_activity", sort_order: str = "desc"
) -> Tuple[List[str], int]:
    """
    Get paginated list of user IDs who have completed surveys, with configurable sorting.

    Args:
        page (int): Page number (1-based)
        per_page (int): Number of users per page
        sort_by (str): Field to sort by ('user_id' or 'last_activity')
        sort_order (str): Sort order ('asc' or 'desc')

    Returns:
        Tuple[List[str], int]: (list of user IDs for current page, total user count)
    """
    # First get the total count of distinct users
    count_query = """
        SELECT COUNT(DISTINCT user_id) as total_count
        FROM survey_responses 
        WHERE completed = TRUE AND attention_check_failed = FALSE
    """

    try:
        count_result = execute_query(count_query, fetch_one=True)
        total_count = count_result["total_count"] if count_result else 0

        # If no users found, return empty result
        if total_count == 0:
            logger.info("No completed survey responses found for pagination")
            return [], 0

        # Calculate offset for pagination (page is 1-based)
        offset = (page - 1) * per_page

        # Whitelist of allowed sort columns and their corresponding SQL expressions
        allowed_sort_columns = {
            "user_id": "user_id",
            "last_activity": "MAX(created_at)",
        }
        sort_column = allowed_sort_columns.get(
            sort_by, "MAX(created_at)"
        )  # Default to last_activity

        # Sanitize sort order
        if sort_order.upper() not in ["ASC", "DESC"]:
            sort_order = "DESC"

        # Build the final paginated query using the safe, dynamic values
        paginated_query = f"""
            SELECT DISTINCT user_id
            FROM survey_responses 
            WHERE completed = TRUE AND attention_check_failed = FALSE
            GROUP BY user_id
            ORDER BY {sort_column} {sort_order.upper()}
            LIMIT %s OFFSET %s
        """

        paginated_result = execute_query(paginated_query, (per_page, offset))
        user_ids = (
            [row["user_id"] for row in paginated_result] if paginated_result else []
        )

        logger.debug(
            f"Retrieved {len(user_ids)} user IDs for page {page} "
            f"(total: {total_count}, sort: {sort_by} {sort_order})"
        )
        return user_ids, total_count

    except Exception as e:
        logger.error(f"Error retrieving paginated user IDs: {str(e)}")
        return [], 0


def get_user_survey_performance_data(
    user_ids: Optional[List[str]] = None,
) -> List[Dict]:
    """
    Get comprehensive user performance data across all surveys for matrix display.

    Args:
        user_ids (Optional[List[str]]): If provided, filter results to these users only

    Returns:
        List[Dict]: List containing user-survey performance data with strategy-specific metrics.
                   Each dict contains: user_id, survey_id, strategy_name, strategy_columns,
                   basic_stats, strategy_metrics, ideal_budget, response_created_at
    """
    try:
        # Get all user choices data
        user_choices = retrieve_user_survey_choices()

        if not user_choices:
            logger.info("No user choices data found")
            return []

        # Filter by user_ids if provided
        if user_ids is not None:
            original_count = len(user_choices)
            user_choices = [
                choice for choice in user_choices if choice["user_id"] in user_ids
            ]
            logger.debug(
                f"Filtered user choices from {original_count} to {len(user_choices)} based on user_ids filter"
            )

        # Group choices by user and survey
        grouped_choices = {}
        survey_strategies = {}  # Cache strategy info

        for choice in user_choices:
            user_id = choice["user_id"]
            survey_id = choice["survey_id"]

            if user_id not in grouped_choices:
                grouped_choices[user_id] = {}
            if survey_id not in grouped_choices[user_id]:
                grouped_choices[user_id][survey_id] = []

            grouped_choices[user_id][survey_id].append(choice)

            # Cache survey strategy info
            if survey_id not in survey_strategies:
                config = get_survey_pair_generation_config(survey_id)
                if config:
                    try:
                        from application.services.pair_generation.base import (
                            StrategyRegistry,
                        )

                        strategy = StrategyRegistry.get_strategy(config["strategy"])
                        survey_strategies[survey_id] = {
                            "strategy_name": strategy.get_strategy_name(),
                            "strategy_columns": strategy.get_table_columns(),
                        }
                    except ValueError:
                        survey_strategies[survey_id] = {
                            "strategy_name": "unknown",
                            "strategy_columns": {},
                        }
                else:
                    survey_strategies[survey_id] = {
                        "strategy_name": "unknown",
                        "strategy_columns": {},
                    }

        # Generate performance data for each user-survey combination
        performance_data = []

        for user_id, user_surveys in grouped_choices.items():
            for survey_id, choices in user_surveys.items():
                strategy_info = survey_strategies.get(survey_id, {})
                strategy_name = strategy_info.get("strategy_name", "unknown")
                strategy_columns = strategy_info.get("strategy_columns", {})

                # Calculate basic choice statistics
                from analysis.report_content_generators import (
                    calculate_choice_statistics,
                )

                basic_stats = calculate_choice_statistics(choices)

                # Calculate strategy-specific metrics
                strategy_metrics = {}

                if "consistency" in strategy_columns:
                    # Handle peak_linearity_test strategy
                    from analysis.report_content_generators import (
                        _extract_extreme_vector_preferences,
                    )

                    try:
                        _, processed_pairs, _, consistency_info, _ = (
                            _extract_extreme_vector_preferences(choices)
                        )
                        if processed_pairs > 0 and consistency_info:
                            total_matches = sum(
                                matches for matches, total, _ in consistency_info
                            )
                            total_pairs = sum(total for _, total, _ in consistency_info)
                            overall_consistency = (
                                int(round(100 * total_matches / total_pairs))
                                if total_pairs > 0
                                else 0
                            )
                            strategy_metrics["consistency"] = overall_consistency
                        else:
                            strategy_metrics["consistency"] = 0
                    except Exception:
                        strategy_metrics["consistency"] = 0

                elif (
                    "group_consistency" in strategy_columns
                    or "linear_consistency" in strategy_columns
                ):
                    # Handle component_symmetry_test and sign_symmetry_test strategies
                    try:
                        if strategy_name == "component_symmetry_test":
                            from analysis.report_content_generators import (
                                _calculate_cyclic_shift_group_consistency,
                            )

                            consistencies = _calculate_cyclic_shift_group_consistency(
                                choices
                            )
                        elif strategy_name == "sign_symmetry_test":
                            from analysis.report_content_generators import (
                                _calculate_linear_symmetry_group_consistency,
                            )

                            consistencies = (
                                _calculate_linear_symmetry_group_consistency(choices)
                            )
                        else:
                            consistencies = {"overall": 0.0}

                        overall_consistency = consistencies.get("overall", 0.0)
                        strategy_metrics["group_consistency"] = overall_consistency
                    except Exception:
                        strategy_metrics["group_consistency"] = 0.0

                elif "sum" in strategy_columns and "ratio" in strategy_columns:
                    # Handle l1_vs_leontief_comparison and similar strategies
                    strategy_metrics["sum_percent"] = basic_stats["sum_percent"]
                    strategy_metrics["ratio_percent"] = basic_stats["ratio_percent"]

                elif "rss" in strategy_columns:
                    # Handle root sum squared strategies
                    if "sum" in strategy_columns:  # l1_vs_l2_comparison
                        rss_percent = 100 - basic_stats["sum_percent"]
                        strategy_metrics["rss_percent"] = rss_percent
                        strategy_metrics["sum_percent"] = basic_stats["sum_percent"]
                    elif "ratio" in strategy_columns:  # l2_vs_leontief_comparison
                        rss_percent = 100 - basic_stats["ratio_percent"]
                        strategy_metrics["rss_percent"] = rss_percent
                        strategy_metrics["ratio_percent"] = basic_stats["ratio_percent"]

                elif (
                    "concentrated_changes" in strategy_columns
                    and "distributed_changes" in strategy_columns
                ):
                    # Handle asymmetric_loss_distribution strategy
                    # Use option1_percent for concentrated changes,
                    # option2_percent for distributed changes
                    strategy_metrics["concentrated_changes_percent"] = basic_stats[
                        "option1_percent"
                    ]
                    strategy_metrics["distributed_changes_percent"] = basic_stats[
                        "option2_percent"
                    ]

                else:
                    # Default: use option percentages
                    strategy_metrics["option1_percent"] = basic_stats["option1_percent"]
                    strategy_metrics["option2_percent"] = basic_stats["option2_percent"]

                # Extract ideal budget
                ideal_budget = "N/A"
                if choices:
                    try:
                        import json

                        optimal_allocation = json.loads(
                            choices[0]["optimal_allocation"]
                        )
                        ideal_budget = str(optimal_allocation)
                    except (json.JSONDecodeError, KeyError, IndexError):
                        pass

                performance_record = {
                    "user_id": user_id,
                    "survey_id": survey_id,
                    "strategy_name": strategy_name,
                    "strategy_columns": strategy_columns,
                    "basic_stats": basic_stats,
                    "strategy_metrics": strategy_metrics,
                    "ideal_budget": ideal_budget,
                    "response_created_at": (
                        choices[0].get("response_created_at") if choices else None
                    ),
                }

                performance_data.append(performance_record)

        logger.info(
            f"Generated performance data for {len(performance_data)} user-survey combinations"
        )
        return performance_data

    except Exception as e:
        logger.error(f"Error getting user survey performance data: {str(e)}")
        return []
