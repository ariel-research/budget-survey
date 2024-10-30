import os
import sys

# Add the parent directory to the system path to allow importing from the backend module
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from unittest.mock import patch

import pytest

from app import create_app


@pytest.fixture
def client():
    app = create_app()
    with app.test_client() as client:
        yield client


# Example alphanumeric IDs that match the expected format
@pytest.fixture
def sample_user_id():
    return "297d9c9b246687a50d06773b9d4a2e39"


@pytest.fixture
def sample_survey_id():
    return "1aadbb759d0f142448d9833af94ab948"


def test_index_route(client, sample_user_id, sample_survey_id):
    """Test the index route with valid parameters."""
    with patch("application.routes.get_survey_name", return_value="Test Survey"):
        with patch("application.routes.check_user_participation", return_value=False):
            response = client.get(
                f"/?userID={sample_user_id}&surveyID={sample_survey_id}"
            )
            assert response.status_code == 200
            assert b"Test Survey" in response.data


def test_index_route_missing_param(client, sample_survey_id):
    """Test the index route with a missing required parameter."""
    response = client.get(f"/?surveyID={sample_survey_id}")
    assert response.status_code == 400


def test_create_vector_get(client, sample_user_id, sample_survey_id):
    """Test the GET request to create_vector route."""
    with patch("application.routes.get_subjects", return_value=["Health", "Education"]):
        response = client.get(
            f"/create_vector?userID={sample_user_id}&surveyID={sample_survey_id}"
        )
        assert response.status_code == 200
        assert b"Health" in response.data
        assert b"Education" in response.data


def test_create_vector_post_valid(client, sample_user_id, sample_survey_id):
    """Test the POST request to create_vector route with valid data."""
    with patch("application.routes.get_subjects", return_value=["Health", "Education"]):
        response = client.post(
            f"/create_vector?userID={sample_user_id}&surveyID={sample_survey_id}",
            data={"Health": "50", "Education": "50"},
        )
        assert response.status_code == 302  # Redirect


def test_create_vector_post_invalid(client, sample_user_id, sample_survey_id):
    """Test the POST request to create_vector route with invalid data."""
    with patch("application.routes.get_subjects", return_value=["Health", "Education"]):
        response = client.post(
            f"/create_vector?userID={sample_user_id}&surveyID={sample_survey_id}",
            data={"Health": "60", "Education": "60"},
        )
        assert response.status_code == 200
        # Check for the presence of an error message, not the specific text
        assert b"error" in response.data.lower() or b"invalid" in response.data.lower()


def test_survey_get(client, sample_user_id, sample_survey_id):
    """Test the GET request to survey route."""
    with patch("application.routes.get_subjects", return_value=["Health", "Education"]):
        with patch("application.routes.generate_user_example", return_value=[]):
            response = client.get(
                f"/survey?userID={sample_user_id}&surveyID={sample_survey_id}&vector=50,50"
            )
            assert response.status_code == 200


def test_survey_post_valid(client, sample_user_id, sample_survey_id):
    """Test the POST request to survey route with valid data."""
    with patch("application.routes.get_subjects", return_value=["Health", "Education"]):
        with patch("application.routes.user_exists", return_value=True):
            with patch("application.routes.create_survey_response", return_value=1):
                with patch("application.routes.create_comparison_pair", return_value=1):
                    with patch("application.routes.mark_survey_as_completed"):
                        response = client.post(
                            f"/survey?userID={sample_user_id}&surveyID={sample_survey_id}",
                            data={
                                "user_vector": "50,50",
                                "awareness_check": "2",
                                "option1_0": "60,40",
                                "option2_0": "40,60",
                                "choice_0": "1",
                            },
                        )
                        assert response.status_code in [
                            200,
                            302,
                        ]  # Allow both OK and redirect


def test_thank_you(client):
    """Test the thank_you route."""
    response = client.get("/thank_you")
    assert response.status_code == 200
    assert b"thank" in response.data.lower()  # Check for 'thank' in any case


def test_report_route(client):
    """Test the report route when report exists."""
    with patch("application.routes.send_file") as mock_send_file:
        response = client.get("/report")
        assert response.status_code == 200
        mock_send_file.assert_called_once()
        args = mock_send_file.call_args[0]
        assert args[0] == "data/survey_analysis_report.pdf"
        assert mock_send_file.call_args[1]["mimetype"] == "application/pdf"
