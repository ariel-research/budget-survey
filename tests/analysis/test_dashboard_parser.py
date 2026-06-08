from datetime import datetime
from unittest.mock import patch

from application.routes.dashboard import parse_survey_data


@patch("application.routes.dashboard.url_for")
def test_parser_logic(mock_url_for):
    # Mock the URL generation so we don't need a Flask App Context
    mock_url_for.return_value = "http://test-link/share"

    # Case 1: Active Survey - Gathering State (1 <= N < 30) -> "orange"
    gathering_survey = {
        "id": 42,
        "active": True,
        "created_at": datetime(2026, 2, 9, 14, 30, 0),
        "pair_generation_config": '{"strategy":"sign_symmetry","params":{"x":1}}',
        "title": '{"en":"Municipal Budget Study","he":"מחקר תקציב עירוני"}',
        "subjects": '[{"en":"Education","he":"חינוך"}]',
        "participant_count": 17,
    }

    # Case 2: Sufficient Survey (N >= 30) -> "green"
    sufficient_survey = {
        "id": 43,
        "active": True,
        "created_at": datetime(2026, 2, 9, 14, 30, 0),
        "participant_count": 55,
    }

    # Case 3: Malformed/Empty Data -> "gray"
    empty_bad_survey = {
        "id": 99,
        "created_at": None,
        "pair_generation_config": "{malformed-json",
        "title": None,
        "subjects": None,
        "participant_count": None,
    }

    # Case 4: Active Survey - No responses (N = 0) -> "red"
    no_response_survey = {
        "id": 44,
        "active": True,
        "created_at": datetime(2026, 2, 9, 14, 30, 0),
        "participant_count": 0,
    }

    gathering_result = parse_survey_data(gathering_survey)
    sufficient_result = parse_survey_data(sufficient_survey)
    empty_result = parse_survey_data(empty_bad_survey)
    no_response_result = parse_survey_data(no_response_survey)

    expected_keys = {
        "id",
        "ui_date",
        "ui_status",
        "ui_status_priority",
        "ui_status_tooltip",
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

    # Verify key structure
    assert expected_keys.issubset(gathering_result.keys())
    assert expected_keys.issubset(empty_result.keys())

    # --- Gathering State (Orange) Assertions ---
    assert gathering_result["ui_status"] == "orange"
    assert gathering_result["ui_status_priority"] == 2
    assert gathering_result["is_active_data"] is True
    assert gathering_result["ui_strategy"] == "Sign Symmetry"
    assert gathering_result["ui_context"] == "Municipal Budget Study"
    # Verify the new Date Format
    assert gathering_result["ui_date"] == "09 Feb 26"
    assert gathering_result["ui_volume"] == 17

    # --- Sufficient State (Green) Assertions ---
    assert sufficient_result["ui_status"] == "green"
    assert sufficient_result["ui_status_priority"] == 3
    assert sufficient_result["ui_volume"] == 55

    # --- No Response State (Red) Assertions ---
    assert no_response_result["ui_status"] == "red"
    assert no_response_result["ui_status_priority"] == 1
    assert no_response_result["ui_volume"] == 0
    assert no_response_result["is_active_data"] is False

    # --- Empty/Bad Data (Gray) Assertions ---
    assert empty_result["ui_status"] == "gray"
    assert empty_result["ui_status_priority"] == 0
    assert empty_result["is_active_data"] is False
    assert empty_result["ui_strategy"] == "Unknown"
    assert empty_result["ui_dimension"] == "N/A"
    assert empty_result["ui_date"] == ""

    # Link Assertion
    assert gathering_result["ui_share_link"] == "http://test-link/share"
