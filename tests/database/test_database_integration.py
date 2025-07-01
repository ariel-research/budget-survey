import json
import random
import time

import mysql.connector
import pytest
from flask import session

from app import create_app
from database.db import execute_query
from database.queries import (
    check_user_participation,
    create_comparison_pair,
    create_survey_response,
    create_user,
    get_latest_survey_timestamp,
    get_subjects,
    get_survey_name,
    get_user_participation_overview,
    mark_survey_as_completed,
    retrieve_completed_survey_responses,
    user_exists,
)


@pytest.fixture(scope="session")
def app():
    """Create a new app instance for the test session."""
    from config import TestConfig

    app = create_app(TestConfig)
    return app


@pytest.fixture
def mock_language():
    """Mock the language setting for tests."""

    def _set_language(app, lang="he"):
        with app.test_request_context() as ctx:
            ctx.push()
            session["language"] = lang
            session.modified = True
            yield
            ctx.pop()

    return _set_language


@pytest.fixture(scope="session")
def setup_test_data(app):
    """Create the stories and surveys once for all tests."""
    with app.app_context():
        # 1. Insert test stories
        story_query = """
        INSERT INTO stories 
            (code, title, description, subjects) 
        VALUES 
            (%s, %s, %s, %s)
        """

        # First story
        code1 = "test_story_1"
        title_json1 = json.dumps({"en": "Test Survey", "he": "סקר בדיקה"})
        description_json1 = json.dumps({"en": "Description 1", "he": "תיאור 1"})
        subjects_json1 = json.dumps(
            [{"en": "Subject1", "he": "נושא1"}, {"en": "Subject2", "he": "נושא2"}]
        )
        execute_query(
            story_query, (code1, title_json1, description_json1, subjects_json1)
        )

        # Second story
        code2 = "test_story_2"
        title_json2 = json.dumps({"en": "Another Test Survey", "he": "סקר בדיקה נוסף"})
        description_json2 = json.dumps({"en": "Description 2", "he": "תיאור 2"})
        subjects_json2 = json.dumps(
            [{"en": "Subject3", "he": "נושא3"}, {"en": "Subject4", "he": "נושא4"}]
        )
        execute_query(
            story_query, (code2, title_json2, description_json2, subjects_json2)
        )

        # 2. Insert test surveys that reference the stories
        survey_query = """
        INSERT INTO surveys 
            (story_code, active, pair_generation_config) 
        VALUES 
            (%s, %s, %s)
        """

        # First survey
        pair_gen_config1 = json.dumps(
            {"strategy": "optimization_metrics", "params": {"num_pairs": 10}}
        )
        execute_query(survey_query, (code1, True, pair_gen_config1))

        # Second survey
        pair_gen_config2 = json.dumps(
            {"strategy": "weighted_average_vector", "params": {"num_pairs": 10}}
        )
        execute_query(survey_query, (code2, True, pair_gen_config2))

    yield
    with app.app_context():
        execute_query("DELETE FROM surveys")
        execute_query("DELETE FROM stories")
        execute_query("ALTER TABLE surveys AUTO_INCREMENT = 1")
        execute_query("ALTER TABLE stories AUTO_INCREMENT = 1")


@pytest.fixture(scope="function")
def app_context(app):
    with app.app_context():
        yield


@pytest.fixture(scope="function")
def cleanup_db(app):
    yield
    with app.app_context():
        execute_query("DELETE FROM comparison_pairs")
        execute_query("DELETE FROM survey_responses")
        execute_query("DELETE FROM users")


@pytest.fixture(scope="module")
def db_connection(app):
    """
    Establish a direct database connection for the test module using app config.
    Closes the connection after all tests in this module are complete.
    """
    conn = None  # Initialize connection variable
    with app.app_context():  # Need app context to access app.config
        try:
            conn = mysql.connector.connect(
                host=app.config["MYSQL_HOST"],
                port=app.config["MYSQL_PORT"],
                database=app.config["MYSQL_DATABASE"],
                user=app.config["MYSQL_USER"],
                password=app.config["MYSQL_PASSWORD"],
                charset="utf8mb4",
                collation="utf8mb4_unicode_ci",
            )
            print("\n--- Test DB Connection Established ---")
            yield conn  # Provide the connection to the tests
        except mysql.connector.Error as e:
            pytest.fail(f"Failed to establish direct test DB connection: {e}")
        finally:
            # Ensure connection is closed even if errors occur during yield
            if conn and conn.is_connected():
                conn.close()
                print("\n--- Test DB Connection Closed ---")


def generate_unique_id():
    """
    Helper function to generate a random unique ID for users.
    This ensures that each test works with unique data.
    """
    return random.randint(100000, 999999)


def test_database_connection(db_connection):
    """
    Ensure that a connection to the database can be established and is active.
    """
    assert db_connection is not None
    assert db_connection.is_connected()


def test_create_user(app_context, cleanup_db):
    """
    Test the creation of a user in the 'users' table.
    Verify that the user is correctly inserted and can be retrieved.
    """
    user_id = generate_unique_id()
    result = create_user(user_id)
    assert result is not None, "Failed to create user"

    # Verify the inserted user by querying the database
    query = "SELECT * FROM users WHERE id = %s"
    result = execute_query(query, (user_id,))
    assert len(result) == 1, f"User with ID {user_id} not found"
    assert result[0]["id"] == user_id, "User ID mismatch"


def test_create_survey_response(app_context, setup_test_data, cleanup_db):
    user_id = generate_unique_id()
    create_user(user_id)

    # Fetch an existing survey ID
    survey_query = "SELECT id FROM surveys LIMIT 1"
    result = execute_query(survey_query)
    assert result, "No surveys found in the database"
    survey_id = result[0]["id"]

    optimal_allocation = [10, 20, 70]
    user_comment = "This is a test comment"

    survey_response_id = create_survey_response(
        user_id,
        survey_id,
        optimal_allocation,
        user_comment,
        attention_check_failed=False,
    )
    assert survey_response_id is not None, "Failed to create survey response"

    # Verify the insertion
    verify_query = "SELECT * FROM survey_responses WHERE id = %s"
    result = execute_query(verify_query, (survey_response_id,))
    assert result, f"Survey response with ID {survey_response_id} not found"

    # Verify attention check field
    assert (
        result[0]["attention_check_failed"] == 0
    ), "Attention check should default to false"


def test_create_comparison_pair(app_context, setup_test_data, cleanup_db):
    """
    Test the creation of a comparison pair for a survey response.
    Verifies that the comparison pair is inserted into the 'comparison_pairs' table.
    """
    # Create test user and survey response
    user_id = generate_unique_id()
    create_user(user_id)

    # Get test survey
    survey_query = "SELECT id FROM surveys LIMIT 1"
    result = execute_query(survey_query)
    survey_id = result[0]["id"]

    # Create survey response
    survey_response_id = create_survey_response(
        user_id, survey_id, [5, 15, 80], "Test comment", attention_check_failed=False
    )

    # Test data for comparison pair
    test_data = {
        "pair_number": 1,
        "option_1": [10, 20, 70],
        "option_2": [30, 40, 30],
        "user_choice": 2,
        "raw_user_choice": 1,  # Original choice before swap
        "option1_strategy": "Test Random Vector",
        "option2_strategy": "Test Weighted Vector: 30%",
    }

    # Create comparison pair with new fields
    comparison_pair_id = create_comparison_pair(
        survey_response_id=survey_response_id,
        pair_number=test_data["pair_number"],
        option_1=test_data["option_1"],
        option_2=test_data["option_2"],
        user_choice=test_data["user_choice"],
        raw_user_choice=test_data["raw_user_choice"],
        option1_strategy=test_data["option1_strategy"],
        option2_strategy=test_data["option2_strategy"],
    )

    assert comparison_pair_id is not None, "Failed to create comparison pair"

    # Verify all fields were saved correctly
    verify_query = """
        SELECT * FROM comparison_pairs 
        WHERE id = %s
    """
    result = execute_query(verify_query, (comparison_pair_id,))
    assert result, f"Comparison pair {comparison_pair_id} not found"

    pair_data = result[0]
    assert json.loads(pair_data["option_1"]) == test_data["option_1"]
    assert json.loads(pair_data["option_2"]) == test_data["option_2"]
    assert pair_data["user_choice"] == test_data["user_choice"]
    assert pair_data["raw_user_choice"] == test_data["raw_user_choice"]
    assert pair_data["option1_strategy"] == test_data["option1_strategy"]
    assert pair_data["option2_strategy"] == test_data["option2_strategy"]


def test_mark_survey_as_completed(app_context, setup_test_data, cleanup_db):
    """
    Test the functionality to mark a survey as completed.
    Verifies that the 'completed' field is updated in the 'survey_responses' table.
    """
    user_id = generate_unique_id()
    create_user(user_id)

    # Fetch an existing survey ID
    survey_query = "SELECT id FROM surveys LIMIT 1"
    result = execute_query(survey_query)
    assert result, "No surveys found in the database"
    survey_id = result[0]["id"]

    survey_response_id = create_survey_response(
        user_id,
        survey_id,
        [15, 25, 60],
        "Completion test comment",
        attention_check_failed=False,
    )
    assert survey_response_id is not None, "Failed to create survey response"

    result = mark_survey_as_completed(survey_response_id)
    assert result is not None, "Failed to mark survey as completed"

    # Verify that the survey has been marked as completed
    query = "SELECT completed FROM survey_responses WHERE id = %s"
    result = execute_query(query, (survey_response_id,))
    assert result, f"Survey response with ID {survey_response_id} not found"
    assert result[0]["completed"] == 1, "Survey was not marked as completed"


def test_user_exists(app_context, cleanup_db):
    """
    Test the functionality to check if a user exists in the database.
    Verifies that the function correctly identifies existing and non-existing users.
    """
    user_id = generate_unique_id()

    # Check that the user doesn't exist initially
    assert not user_exists(user_id), f"User {user_id} should not exist initially"

    # Create the user
    create_user(user_id)

    # Check that the user now exists
    assert user_exists(user_id), f"User {user_id} should exist after creation"

    # Check for a non-existing user
    non_existing_id = generate_unique_id()
    assert not user_exists(non_existing_id), f"User {non_existing_id} should not exist"


def test_get_subjects(app_context, setup_test_data, mock_language, app):
    """
    Test the retrieval of subjects for a survey.
    Verifies that the function correctly fetches and decodes subjects for an existing survey.
    """
    mock_language(app)  # Set default language to Hebrew

    with app.test_request_context():
        # Fetch an existing survey ID
        survey_query = """
            SELECT s.id, st.subjects 
            FROM surveys s
            JOIN stories st ON s.story_code = st.code
            LIMIT 1
        """
        result = execute_query(survey_query)
        assert result, "No surveys found in the database"
        survey_id = result[0]["id"]
        expected_subjects = ["נושא1", "נושא2"]  # Default to Hebrew

        # Test the get_subjects function
        retrieved_subjects = get_subjects(survey_id)

        # Verify the results
        assert (
            retrieved_subjects == expected_subjects
        ), f"Expected {expected_subjects}, but got {retrieved_subjects}"

        # Test with a non-existent survey ID
        non_existent_id = 9999
        empty_subjects = get_subjects(non_existent_id)
        assert (
            empty_subjects == []
        ), f"Expected empty list for non-existent survey, but got {empty_subjects}"


def test_get_survey_name(app_context, setup_test_data, mock_language, app):
    """
    Test the retrieval of a survey name.
    Verifies that the function correctly fetches the name for an existing survey
    and returns an empty string for a non-existent survey.
    """
    mock_language(app)  # Set default language to Hebrew

    with app.test_request_context():
        # Fetch an existing survey ID and name
        survey_query = """
            SELECT s.id, st.title as name
            FROM surveys s
            JOIN stories st ON s.story_code = st.code
            LIMIT 1
        """
        result = execute_query(survey_query)
        assert result, "No surveys found in the database"
        survey_id = result[0]["id"]
        expected_name = "סקר בדיקה"  # Default to Hebrew

        # Test retrieving the name of the existing survey
        retrieved_name = get_survey_name(survey_id)
        assert (
            retrieved_name == expected_name
        ), f"Expected '{expected_name}', but got '{retrieved_name}'"

        # Test with a non-existent survey ID
        non_existent_id = 9999
        empty_name = get_survey_name(non_existent_id)
        assert (
            empty_name == ""
        ), f"Expected empty string for non-existent survey, but got '{empty_name}'"


def test_check_user_participation(app_context, setup_test_data, cleanup_db):
    """
    Test the check_user_participation function.
    Verifies that the function correctly identifies user participation in surveys.
    """
    user_id = generate_unique_id()
    create_user(user_id)

    # Fetch an existing survey ID
    survey_query = "SELECT id FROM surveys LIMIT 1"
    result = execute_query(survey_query)
    assert result, "No surveys found in the database"
    survey_id = result[0]["id"]

    # Initially, the user shouldn't have participated
    assert not check_user_participation(
        user_id, survey_id
    ), "User shouldn't have participated initially"

    survey_response_id = create_survey_response(
        user_id, survey_id, [50, 50], "", attention_check_failed=False
    )
    assert survey_response_id is not None, "Failed to create survey response"

    # User still shouldn't be marked as participated (survey not completed)
    assert not check_user_participation(
        user_id, survey_id
    ), "User shouldn't be marked as participated before completion"

    mark_survey_as_completed(survey_response_id)

    # Now the user should be marked as participated
    assert check_user_participation(
        user_id, survey_id
    ), "User should be marked as participated after completion"

    # Check for a different survey
    different_survey_id = survey_id + 1  # Assuming sequential IDs
    assert not check_user_participation(
        user_id, different_survey_id
    ), "User shouldn't be marked as participated in a different survey"

    # Check for a different user
    different_user_id = generate_unique_id()
    assert not check_user_participation(
        different_user_id, survey_id
    ), "Different user shouldn't be marked as participated"


def test_retrieve_completed_survey_responses(app_context, setup_test_data, cleanup_db):
    """
    Test the retrieval of completed survey responses.
    Verifies that the function correctly fetches all completed survey responses with their comparison pairs.
    """
    # Create test user and survey response
    user_id = generate_unique_id()
    create_user(user_id)

    # Get test survey
    survey_query = "SELECT id FROM surveys LIMIT 1"
    result = execute_query(survey_query)
    survey_id = result[0]["id"]

    # Create survey response
    optimal_allocation = [30, 30, 40]
    user_comment = "Retrieval test comment"
    survey_response_id = create_survey_response(
        user_id,
        survey_id,
        optimal_allocation,
        user_comment,
        attention_check_failed=False,
    )

    # Create comparison pairs with strategy information
    pairs_data = [
        {
            "pair_number": 1,
            "option_1": [25, 25, 50],
            "option_2": [35, 35, 30],
            "user_choice": 2,
            "raw_user_choice": 2,
            "option1_strategy": "Random Vector",
            "option2_strategy": "Weighted Vector: 50%",
        },
        {
            "pair_number": 2,
            "option_1": [20, 40, 40],
            "option_2": [40, 20, 40],
            "user_choice": 1,
            "raw_user_choice": 2,
            "option1_strategy": "Sum Optimized Vector: 30",
            "option2_strategy": "Ratio Optimized Vector: 0.8",
        },
    ]

    for pair_data in pairs_data:
        pair_id = create_comparison_pair(
            survey_response_id=survey_response_id,
            pair_number=pair_data["pair_number"],
            option_1=pair_data["option_1"],
            option_2=pair_data["option_2"],
            user_choice=pair_data["user_choice"],
            raw_user_choice=pair_data["raw_user_choice"],
            option1_strategy=pair_data["option1_strategy"],
            option2_strategy=pair_data["option2_strategy"],
        )
        assert pair_id is not None, f"Failed to create pair {pair_data['pair_number']}"

    # Mark survey as completed
    mark_survey_as_completed(survey_response_id)

    # Retrieve and verify responses
    completed_responses = retrieve_completed_survey_responses()
    assert completed_responses, "No completed survey responses retrieved"
    assert len(completed_responses) == 2, "Expected 2 comparison pairs"

    # Verify strategy information is included
    for response, expected_pair in zip(completed_responses, pairs_data):
        assert response["survey_response_id"] == survey_response_id
        assert response["user_id"] == user_id
        assert response["survey_id"] == survey_id
        assert json.loads(response["optimal_allocation"]) == optimal_allocation
        assert response["completed"] == 1
        assert "response_created_at" in response
        assert response["pair_number"] == expected_pair["pair_number"]
        assert json.loads(response["option_1"]) == expected_pair["option_1"]
        assert json.loads(response["option_2"]) == expected_pair["option_2"]
        assert response["user_choice"] == expected_pair["user_choice"]


def test_get_latest_survey_timestamp(app_context, setup_test_data, cleanup_db):
    """
    Test retrieval of latest survey response timestamp.
    """
    # Create a user and survey response
    user_id = generate_unique_id()
    create_user(user_id)

    # Fetch an existing survey ID
    survey_query = "SELECT id FROM surveys LIMIT 1"
    result = execute_query(survey_query)
    survey_id = result[0]["id"]

    # Create and complete a survey response
    survey_response_id = create_survey_response(
        user_id, survey_id, [30, 30, 40], "Test comment", attention_check_failed=False
    )
    mark_survey_as_completed(survey_response_id)

    # Add a small delay to ensure different timestamps
    time.sleep(1)

    # Create another survey response but don't complete it
    create_survey_response(user_id, survey_id, [40, 30, 30], "Test comment 2")

    # Test getting latest timestamp
    latest_timestamp = get_latest_survey_timestamp()

    # Verify results
    assert latest_timestamp is not None, "Should return a timestamp"

    # Verify by direct query
    query = """
        SELECT created_at 
        FROM survey_responses 
        WHERE completed = TRUE 
        ORDER BY created_at DESC 
        LIMIT 1
    """
    result = execute_query(query)
    expected_timestamp = result[0]["created_at"].timestamp()

    assert latest_timestamp == expected_timestamp, "Timestamps don't match"


def test_get_latest_survey_timestamp_no_surveys(app_context, cleanup_db):
    """
    Test retrieval of latest survey response timestamp when no surveys exist.
    """
    from database.queries import get_latest_survey_timestamp

    latest_timestamp = get_latest_survey_timestamp()
    assert latest_timestamp == 0, "Should return 0 when no completed surveys exist"


def test_get_subjects_multiple_languages(
    app_context, setup_test_data, mock_language, app
):
    """Test subject retrieval in different languages."""
    with app.test_request_context() as ctx:
        # Keep the context active for the entire test
        ctx.push()  # Push the context

        survey_query = """
            SELECT s.id, st.subjects 
            FROM surveys s
            JOIN stories st ON s.story_code = st.code
            LIMIT 1
        """
        result = execute_query(survey_query)
        assert result, "No surveys found in the database"
        survey_id = result[0]["id"]

        # Verify the raw data first
        subjects_data = json.loads(result[0]["subjects"])
        assert subjects_data == [
            {"en": "Subject1", "he": "נושא1"},
            {"en": "Subject2", "he": "נושא2"},
        ], "Raw subjects data does not match expected structure"

        # Test Hebrew
        session["language"] = "he"
        he_subjects = get_subjects(survey_id)
        assert he_subjects == [
            "נושא1",
            "נושא2",
        ], f"Expected Hebrew subjects but got {he_subjects}"

        # Test English
        session["language"] = "en"
        en_subjects = get_subjects(survey_id)
        assert en_subjects == [
            "Subject1",
            "Subject2",
        ], f"Expected English subjects but got {en_subjects}"

        ctx.pop()  # Pop the context when done


def test_get_survey_name_multiple_languages(
    app_context, setup_test_data, mock_language, app
):
    """Test survey name retrieval in different languages."""
    with app.test_request_context() as ctx:
        # Keep the context active for the entire test
        ctx.push()  # Push the context

        survey_query = """
            SELECT s.id, st.title as name
            FROM surveys s
            JOIN stories st ON s.story_code = st.code
            LIMIT 1
        """
        result = execute_query(survey_query)
        assert result, "No surveys found in the database"
        survey_id = result[0]["id"]

        # Test Hebrew
        session["language"] = "he"
        he_name = get_survey_name(survey_id)
        assert he_name == "סקר בדיקה", f"Expected 'סקר בדיקה' but got '{he_name}'"

        # Test English
        session["language"] = "en"
        en_name = get_survey_name(survey_id)
        assert en_name == "Test Survey", f"Expected 'Test Survey' but got '{en_name}'"

        ctx.pop()  # Pop the context when done


def test_attention_check_handling(app_context, setup_test_data, cleanup_db):
    """Test the handling of attention check failures in survey responses."""
    user_id = generate_unique_id()
    create_user(user_id)

    # Get test survey
    survey_query = "SELECT id FROM surveys LIMIT 1"
    result = execute_query(survey_query)
    survey_id = result[0]["id"]

    # Create failed attention check response
    failed_response_id = create_survey_response(
        user_id=user_id,
        survey_id=survey_id,
        optimal_allocation=[50, 50],
        user_comment="Failed attention check",
        attention_check_failed=True,
    )

    # Verify attention check status
    query = "SELECT attention_check_failed FROM survey_responses WHERE id = %s"
    result = execute_query(query, (failed_response_id,), fetch_one=True)
    assert (
        result["attention_check_failed"] == 1
    ), "Attention check should be marked as failed"

    # Mark as completed
    mark_survey_as_completed(failed_response_id)

    # Verify user participation check excludes failed attention checks
    assert check_user_participation(user_id, survey_id)

    # Verify failed checks are excluded from completed responses
    completed_responses = retrieve_completed_survey_responses()
    response_ids = [r["survey_response_id"] for r in completed_responses]
    assert failed_response_id not in response_ids


def test_get_user_participation_overview(app_context, setup_test_data, cleanup_db):
    """Test user participation overview with various scenarios."""

    # Get test survey IDs
    survey_query = "SELECT id FROM surveys ORDER BY id LIMIT 2"
    result = execute_query(survey_query)
    assert len(result) >= 2, "Need at least 2 surveys for this test"
    survey_id_1, survey_id_2 = result[0]["id"], result[1]["id"]

    # Create test users
    user1 = generate_unique_id()
    user2 = generate_unique_id()
    user3 = generate_unique_id()

    create_user(user1)
    create_user(user2)
    create_user(user3)

    # User 1: Two successful surveys
    response1_1 = create_survey_response(
        user1, survey_id_1, [50, 50], "Success 1", attention_check_failed=False
    )
    mark_survey_as_completed(response1_1)

    response1_2 = create_survey_response(
        user1, survey_id_2, [60, 40], "Success 2", attention_check_failed=False
    )
    mark_survey_as_completed(response1_2)

    # User 2: One successful, one failed
    response2_1 = create_survey_response(
        user2, survey_id_1, [40, 60], "Success", attention_check_failed=False
    )
    mark_survey_as_completed(response2_1)

    response2_2 = create_survey_response(
        user2, survey_id_2, [30, 70], "Failed", attention_check_failed=True
    )
    mark_survey_as_completed(response2_2)

    # User 3: Only failed survey
    response3_1 = create_survey_response(
        user3, survey_id_1, [70, 30], "Failed", attention_check_failed=True
    )
    mark_survey_as_completed(response3_1)

    # Test the function
    overview = get_user_participation_overview()

    # Should return data for all users (ordered by last_activity DESC)
    assert len(overview) == 3, f"Expected 3 users, got {len(overview)}"

    # Verify data structure and values
    user_data = {user["user_id"]: user for user in overview}

    # User 1: 2 successful, 0 failed
    assert user1 in user_data
    user1_data = user_data[user1]
    assert user1_data["successful_surveys_count"] == 2
    assert user1_data["failed_surveys_count"] == 0
    expected_ids = {str(survey_id_1), str(survey_id_2)}
    assert set(user1_data["successful_survey_ids"].split(",")) == expected_ids
    assert user1_data["failed_survey_ids"] == ""
    assert user1_data["last_activity"] is not None

    # User 2: 1 successful, 1 failed
    assert user2 in user_data
    user2_data = user_data[user2]
    assert user2_data["successful_surveys_count"] == 1
    assert user2_data["failed_surveys_count"] == 1
    assert user2_data["successful_survey_ids"] == str(survey_id_1)
    assert user2_data["failed_survey_ids"] == str(survey_id_2)
    assert user2_data["last_activity"] is not None

    # User 3: 0 successful, 1 failed
    assert user3 in user_data
    user3_data = user_data[user3]
    assert user3_data["successful_surveys_count"] == 0
    assert user3_data["failed_surveys_count"] == 1
    assert user3_data["successful_survey_ids"] == ""
    assert user3_data["failed_survey_ids"] == str(survey_id_1)
    assert user3_data["last_activity"] is not None


def test_get_user_participation_overview_empty(app_context, cleanup_db):
    """Test user participation overview when no completed surveys exist."""

    # Create a user but no completed surveys
    user_id = generate_unique_id()
    create_user(user_id)

    overview = get_user_participation_overview()
    assert overview == [], "Should return empty list when no completed surveys"


if __name__ == "__main__":
    pytest.main()
