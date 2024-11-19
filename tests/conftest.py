import pytest
from test_setup import setup_test_environment

# Get create_app function
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
