import pytest
import sys
import os
import random
import json

# Add the parent directory to the system path to allow importing from the backend module.
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.db import get_db_connection, execute_query
from database.queries import create_user, create_survey_response, create_comparison_pair, mark_survey_as_completed, user_exists, get_subjects, get_survey_name

@pytest.fixture(scope="module")
def db_connection():
    """
    Establish a connection to the database for the entire module.
    Closes the connection after all tests in this module are complete.
    """
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

@pytest.fixture(scope="function")
def cleanup_db():
    """
    Cleanup function that deletes entries from all relevant tables after each test.
    Ensures tests are independent by resetting the database state after each test.
    """
    yield
    execute_query("DELETE FROM comparison_pairs")
    execute_query("DELETE FROM survey_responses")
    execute_query("DELETE FROM users")
    execute_query("DELETE FROM surveys")

def test_database_connection(db_connection):
    """
    Ensure that a connection to the database can be established and is active.
    """
    assert db_connection is not None
    assert db_connection.is_connected()

def test_create_user(cleanup_db):
    """
    Test the creation of a user in the 'users' table.
    Verify that the user is correctly inserted and can be retrieved.
    """
    user_id = generate_unique_id()
    result = create_user(user_id)
    assert result is not None  # Check that the user was inserted successfully

    # Verify the inserted user by querying the database
    query = "SELECT * FROM users WHERE id = %s"
    result = execute_query(query, (user_id,))
    assert len(result) == 1  # Ensure one result is returned
    assert result[0]['id'] == user_id  # Check that the ID matches

def test_create_survey_response(cleanup_db):
    """
    Test the creation of a survey response and ensure it is correctly inserted into the 'survey_responses' table.
    """
    user_id = generate_unique_id()
    create_user(user_id)  # Insert the user into the database
    survey_id = 1  # Sample survey ID
    optimal_allocation = [10, 20, 30]  # Sample optimal allocation

    # Insert a survey response for the user
    survey_response_id = create_survey_response(user_id, survey_id, optimal_allocation)
    assert survey_response_id is not None  # Ensure that the survey response was inserted

    # Verify the inserted survey response by querying the database
    query = "SELECT * FROM survey_responses WHERE id = %s"
    result = execute_query(query, (survey_response_id,))
    assert len(result) == 1  # Ensure one result is returned
    assert result[0]['user_id'] == user_id  # Check that the user ID matches
    assert result[0]['survey_id'] == survey_id  # Check that the survey id matches

def test_create_comparison_pair(cleanup_db):
    """
    Test the creation of a comparison pair for a survey response.
    Verifies that the comparison pair is inserted into the 'comparison_pairs' table.
    """
    user_id = generate_unique_id()
    create_user(user_id)  # Insert the user into the database
    survey_response_id = create_survey_response(user_id, 2, [5, 15, 25])  # Create a new survey response

    pair_number = 1  # Define a pair number for comparison
    option_1 = [10, 20]  # First set of options
    option_2 = [30, 40]  # Second set of options
    user_choice = 2  # User's selected option

    # Insert the comparison pair
    comparison_pair_id = create_comparison_pair(survey_response_id, pair_number, option_1, option_2, user_choice)
    assert comparison_pair_id is not None  # Ensure that the comparison pair was inserted

    # Verify the inserted comparison pair by querying the database
    query = "SELECT * FROM comparison_pairs WHERE id = %s"
    result = execute_query(query, (comparison_pair_id,))
    assert len(result) == 1  # Ensure one result is returned
    assert result[0]['survey_response_id'] == survey_response_id  # Check that the survey response ID matches
    assert result[0]['pair_number'] == pair_number  # Check that the pair number matches
    assert result[0]['user_choice'] == user_choice  # Check that the user's choice matches

def test_mark_survey_as_completed(cleanup_db):
    """
    Test the functionality to mark a survey as completed.
    Verifies that the 'completed' field is updated in the 'survey_responses' table.
    """
    user_id = generate_unique_id()
    create_user(user_id)  # Insert the user into the database
    survey_response_id = create_survey_response(user_id, 3, [15, 25, 35])  # Create a new survey response

    # Mark the survey as completed
    result = mark_survey_as_completed(survey_response_id)
    assert result is not None  # Ensure the operation succeeded

    # Verify that the survey has been marked as completed
    query = "SELECT completed FROM survey_responses WHERE id = %s"
    result = execute_query(query, (survey_response_id,))
    assert len(result) == 1  # Ensure one result is returned
    assert result[0]['completed'] == 1  # Check that the 'completed' field is set to 1

def test_user_exists(cleanup_db):
    """
    Test the functionality to check if a user exists in the database.
    Verifies that the function correctly identifies existing and non-existing users.
    """
    user_id = generate_unique_id()

    # Check that the user doesn't exist initially
    assert not user_exists(user_id)

    # Create the user
    create_user(user_id)

    # Check that the user now exists
    assert user_exists(user_id)

    # Check for a non-existing user
    non_existing_id = generate_unique_id()
    assert not user_exists(non_existing_id)

def test_get_subjects(cleanup_db):
    """
    Test the retrieval of subjects for a survey.
    Verifies that the function correctly fetches and decodes subjects for an existing survey.
    """
    # Insert a test survey
    test_subjects = ["ביטחון", "חינוך", "בריאות"]
    survey_id = 1  
    insert_survey_query = """
    INSERT INTO surveys (id, name, subjects, active)
    VALUES (%s, %s, %s, %s)
    """
    execute_query(insert_survey_query, (survey_id, "Test Survey", json.dumps(test_subjects), True))

    # Test the get_subjects function
    retrieved_subjects = get_subjects(survey_id)

    # Verify the results
    assert retrieved_subjects == test_subjects, f"Expected {test_subjects}, but got {retrieved_subjects}"

    # Test with a non-existent survey ID
    non_existent_id = 9999
    empty_subjects = get_subjects(non_existent_id)
    assert empty_subjects == [], f"Expected empty list for non-existent survey, but got {empty_subjects}"

    # Test with an inactive survey
    inactive_survey_id = 2
    execute_query(insert_survey_query, (inactive_survey_id, "Inactive Survey", json.dumps(["Test"]), False))
    inactive_subjects = get_subjects(inactive_survey_id)
    assert inactive_subjects == [], f"Expected empty list for inactive survey, but got {inactive_subjects}"

def test_get_survey_name(cleanup_db):
    """
    Test the retrieval of a survey name.
    Verifies that the function correctly fetches the name for an existing survey
    and returns an empty string for a non-existent survey.
    """
    # Insert a test survey
    test_survey_id = 1
    test_survey_name = "טסט תקציב המדינה"
    insert_survey_query = """
    INSERT INTO surveys (id, name, subjects, active)
    VALUES (%s, %s, %s, %s)
    """
    execute_query(insert_survey_query, (test_survey_id, test_survey_name, json.dumps(["Subject1", "Subject2"]), True))

    # Test retrieving the name of the existing survey
    retrieved_name = get_survey_name(test_survey_id)
    assert retrieved_name == test_survey_name, f"Expected '{test_survey_name}', but got '{retrieved_name}'"

    # Test with a non-existent survey ID
    non_existent_id = 9999
    empty_name = get_survey_name(non_existent_id)
    assert empty_name == "", f"Expected empty string for non-existent survey, but got '{empty_name}'"

    # Test with an inactive survey
    inactive_survey_id = 2
    inactive_survey_name = "Inactive Survey"
    execute_query(insert_survey_query, (inactive_survey_id, inactive_survey_name, json.dumps(["Subject"]), False))
    inactive_name = get_survey_name(inactive_survey_id)
    assert inactive_name == "", f"Expected empty string for inactive survey, but got '{inactive_name}'"
