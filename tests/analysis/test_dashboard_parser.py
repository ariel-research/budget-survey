from datetime import datetime
from unittest.mock import patch

from application.routes.dashboard import parse_survey_data


@patch("application.routes.dashboard.url_for")
def test_parser_logic(mock_url_for):
    # Mock the URL generation so we don't need a Flask App Context
    mock_url_for.return_value = "http://test-link/share"

    complex_survey = {
        "id": 42,
        "created_at": datetime(2026, 2, 9, 14, 30, 0),
        "pair_generation_config": '{"strategy":"sign_symmetry","params":{"x":1}}',
        "title": '{"en":"Municipal Budget Study","he":"מחקר תקציב עירוני"}',
        "subjects": (
            '[{"en":"Education","he":"חינוך"},'
            '{"en":"Health","he":"בריאות"},'
            '{"en":"Transport","he":"תחבורה"}]'
        ),
        "participant_count": 17,
    }
    empty_bad_survey = {
        "id": 99,
        "created_at": None,
        "pair_generation_config": "{malformed-json",
        "title": None,
        "subjects": None,
        "participant_count": None,
    }

    complex_result = parse_survey_data(complex_survey)
    empty_result = parse_survey_data(empty_bad_survey)

    expected_keys = {
        "id",
        "ui_date",
        "ui_status",
        "is_active_data",
        "ui_strategy",
        "ui_context",
        "ui_dimension",
        "ui_volume",
        "ui_share_link",
        "sort_date",
        "sort_identity",
        "sort_dim",
    }

    assert expected_keys.issubset(complex_result.keys())
    assert expected_keys.issubset(empty_result.keys())

    # Assertions
    assert complex_result["ui_status"] == "active"
    assert complex_result["is_active_data"] is True
    assert complex_result["ui_strategy"] == "Sign Symmetry"
    assert complex_result["ui_dimension"] == "3D"
    assert complex_result["ui_context"] == "Municipal Budget Study"

    assert complex_result["ui_date"] == "09/02/26"

    assert complex_result["ui_volume"] == 17

    # Link Assertion
    assert complex_result["ui_share_link"] == "http://test-link/share"

    # Empty/Bad Data Assertions
    assert empty_result["ui_status"] == "inactive"
    assert empty_result["is_active_data"] is False
    assert empty_result["ui_strategy"] == "Unknown"

    # Dimension Logic (N/A for 0)
    assert empty_result["ui_dimension"] == "N/A"
