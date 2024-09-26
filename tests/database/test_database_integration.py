import json
import os
import random
import sys

import pytest

# Add the parent directory to the system path to allow importing from the backend module.
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from app import create_app
from database.db import execute_query, get_db_connection
from database.queries import (
    check_user_participation,
    create_comparison_pair,
    create_survey_response,
    create_user,
    get_subjects,
    get_survey_name,
    mark_survey_as_completed,
    user_exists,
)


@pytest.fixture(scope="session")
def app():
    """Create a new app instance for the test session."""
    from config import TestConfig

    app = create_app(TestConfig)
    return app


@pytest.fixture(scope="session")
def setup_test_data(app):
    """Create the surveys once for all tests and delete them only after all the tests done."""
    with app.app_context():
        # Insert test surveys
        survey_query = "INSERT INTO surveys (name, description, subjects, active) VALUES (%s, %s, %s, %s)"
        execute_query(
            survey_query,
            (
                "Test Survey",
                "Description 1",
                json.dumps(["Subject1", "Subject2"]),
                True,
            ),
        )
        execute_query(
            survey_query,
            (
                "Another Test Survey",
                "Description 2",
                json.dumps(["Subject3", "Subject4"]),
                True,
            ),
        )
        execute_query(
            survey_query,
            (
                "Third Test Survey",
                "Description 3",
                json.dumps(["Subject5", "Subject6", "Subject7"]),
                True,
            ),
        )
    yield
    with app.app_context():
        execute_query("DELETE FROM surveys")
        execute_query("ALTER TABLE surveys AUTO_INCREMENT = 1")


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
    Establish a connection to the database for the entire module.
    Closes the connection after all tests in this module are complete.
    """
    with app.app_context():
        conn = get_db_connection()
        yield conn
        if conn:
            conn.close()


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

    survey_response_id = create_survey_response(user_id, survey_id, optimal_allocation)
    assert survey_response_id is not None, "Failed to create survey response"

    # Verify the insertion
    verify_query = "SELECT * FROM survey_responses WHERE id = %s"
    result = execute_query(verify_query, (survey_response_id,))
    assert result, f"Survey response with ID {survey_response_id} not found"


def test_create_comparison_pair(app_context, setup_test_data, cleanup_db):
    """
    Test the creation of a comparison pair for a survey response.
    Verifies that the comparison pair is inserted into the 'comparison_pairs' table.
    """
    user_id = generate_unique_id()
    create_user(user_id)

    # Fetch an existing survey ID
    survey_query = "SELECT id FROM surveys LIMIT 1"
    result = execute_query(survey_query)
    assert result, "No surveys found in the database"
    survey_id = result[0]["id"]

    survey_response_id = create_survey_response(user_id, survey_id, [5, 15, 80])
    assert survey_response_id is not None, "Failed to create survey response"

    pair_number = 1
    option_1 = [10, 20, 70]
    option_2 = [30, 40, 30]
    user_choice = 2

    comparison_pair_id = create_comparison_pair(
        survey_response_id, pair_number, option_1, option_2, user_choice
    )
    assert comparison_pair_id is not None, "Failed to create comparison pair"

    # Verify the insertion
    verify_query = "SELECT * FROM comparison_pairs WHERE id = %s"
    result = execute_query(verify_query, (comparison_pair_id,))
    assert result, f"Comparison pair with ID {comparison_pair_id} not found"


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

    survey_response_id = create_survey_response(user_id, survey_id, [15, 25, 60])
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


def test_get_subjects(app_context, setup_test_data):
    """
    Test the retrieval of subjects for a survey.
    Verifies that the function correctly fetches and decodes subjects for an existing survey.
    """
    # Fetch an existing survey ID
    survey_query = "SELECT id, subjects FROM surveys LIMIT 1"
    result = execute_query(survey_query)
    assert result, "No surveys found in the database"
    survey_id = result[0]["id"]
    expected_subjects = json.loads(result[0]["subjects"])

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


def test_get_survey_name(app_context, setup_test_data):
    """
    Test the retrieval of a survey name.
    Verifies that the function correctly fetches the name for an existing survey
    and returns an empty string for a non-existent survey.
    """
    # Fetch an existing survey ID and name
    survey_query = "SELECT id, name FROM surveys LIMIT 1"
    result = execute_query(survey_query)
    assert result, "No surveys found in the database"
    survey_id = result[0]["id"]
    expected_name = result[0]["name"]

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

    survey_response_id = create_survey_response(user_id, survey_id, [50, 50])
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


if __name__ == "__main__":
    pytest.main()
