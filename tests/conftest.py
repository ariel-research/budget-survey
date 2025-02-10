import pytest
from test_setup import setup_test_environment

create_app = setup_test_environment()


@pytest.fixture
def app():
    """Creates test Flask app instance with application context"""
    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        yield app


@pytest.fixture
def client(app):
    """Creates test client for making requests"""
    return app.test_client()


@pytest.fixture
def sample_user_id():
    """Returns a sample user ID for testing"""
    return "297d9c9b246687a50d06773b9d4a2e39"


@pytest.fixture
def sample_survey_id():
    """Returns a sample survey ID for testing"""
    return "1aadbb759d0f142448d9833af94ab948"


@pytest.fixture
def test_request_context(app):
    """Provides a test request context with default language"""
    with app.test_request_context():
        yield


@pytest.fixture
def mock_translations():
    """Returns all necessary test translations to avoid request context dependencies"""
    return {
        "original_choice": "Original choice",
        "option_number": "Option {number}",
        "not_available": "Not available",
        "pair_number": "Pair",
        "table_choice": "Choice",
        "table_option": "Option",
        "table_type": "Type",
        "user_id": "User ID",
        "survey_id": "Survey ID",
        "ideal_budget": "Ideal budget",
        "survey_summary": "Survey Summary",
        "overall_statistics": "Overall Survey Statistics",
        "survey_response_breakdown": "Survey Response Breakdown",
        "metric": "Metric",
        "average_percentage": "Average Percentage",
        "percentage": "Percentage",
        "choice": "Choice",
        "based_on_responses": "Based on {x} survey responses",
    }
