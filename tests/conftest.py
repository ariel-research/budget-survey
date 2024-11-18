import os
import sys

import pytest

from app import create_app

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)


@pytest.fixture
def app():
    # Creates test Flask app instance
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    # Creates test client for making requests
    return app.test_client()


@pytest.fixture
def sample_user_id():
    return "297d9c9b246687a50d06773b9d4a2e39"


@pytest.fixture
def sample_survey_id():
    return "1aadbb759d0f142448d9833af94ab948"
