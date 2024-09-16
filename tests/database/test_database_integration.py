import pytest
import sys
import os
import random

# Add the parent directory to the system path to allow importing from the backend module.
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.database.db import get_db_connection, execute_query
from backend.database.queries import create_user, create_survey_response, create_comparison_pair, mark_survey_as_completed

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
    Helper function to generate a random unique external ID for users.
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
    external_id = generate_unique_id()  # Generate a unique external ID for the user
    user_id = create_user(external_id)  # Insert the user into the database
    assert user_id is not None  # Check that the user ID was generated (insert succeeded)

    # Verify the inserted user by querying the database
    query = "SELECT * FROM users WHERE id = %s"
    result = execute_query(query, (user_id,))
    assert len(result) == 1  # Ensure one result is returned
    assert result[0]['external_id'] == external_id  # Check that the external ID matches

def test_create_survey_response(cleanup_db):
    """
    Test the creation of a survey response and ensure it is correctly inserted into the 'survey_responses' table.
    """
    external_id = generate_unique_id()  # Generate a unique external ID for a new user
    user_id = create_user(external_id)  # Insert the user into the database
    survey_name = "Test Survey"  # Sample survey name
    optimal_allocation = [10, 20, 30]  # Sample optimal allocation

    # Insert a survey response for the user
    survey_response_id = create_survey_response(user_id, survey_name, optimal_allocation)
    assert survey_response_id is not None  # Ensure that the survey response was inserted

    # Verify the inserted survey response by querying the database
    query = "SELECT * FROM survey_responses WHERE id = %s"
    result = execute_query(query, (survey_response_id,))
    assert len(result) == 1  # Ensure one result is returned
    assert result[0]['user_id'] == user_id  # Check that the user ID matches
    assert result[0]['survey_name'] == survey_name  # Check that the survey name matches

def test_create_comparison_pair(cleanup_db):
    """
    Test the creation of a comparison pair for a survey response.
    Verifies that the comparison pair is inserted into the 'comparison_pairs' table.
    """
    external_id = generate_unique_id()  # Generate a unique external ID for a new user
    user_id = create_user(external_id)  # Insert the user into the database
    survey_response_id = create_survey_response(user_id, "Test Survey 2", [5, 15, 25])  # Create a new survey response

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
    external_id = generate_unique_id()  # Generate a unique external ID for a new user
    user_id = create_user(external_id)  # Insert the user into the database
    survey_response_id = create_survey_response(user_id, "Test Survey 3", [15, 25, 35])  # Create a new survey response

    # Mark the survey as completed
    result = mark_survey_as_completed(survey_response_id)
    assert result is not None  # Ensure the operation succeeded

    # Verify that the survey has been marked as completed
    query = "SELECT completed FROM survey_responses WHERE id = %s"
    result = execute_query(query, (survey_response_id,))
    assert len(result) == 1  # Ensure one result is returned
    assert result[0]['completed'] == 1  # Check that the 'completed' field is set to 1
