from datetime import datetime

from application.routes.dashboard import parse_survey_data


def test_parser_logic():
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
        "date_label",
        "status",
        "is_active_data",
        "strategy_name",
        "context",
        "dimension",
        "participant_count",
    }

    assert expected_keys.issubset(complex_result.keys())
    assert expected_keys.issubset(empty_result.keys())

    assert complex_result["status"] == "active"
    assert complex_result["is_active_data"] is True
    assert complex_result["strategy_name"] == "Sign Symmetry"
    assert complex_result["dimension"] == "3D"
    assert complex_result["context"] == "Municipal Budget Study"
    assert complex_result["date_label"] == "Feb 09"
    assert complex_result["participant_count"] == 17

    assert empty_result["status"] == "inactive"
    assert empty_result["is_active_data"] is False
    assert empty_result["strategy_name"] == "Unknown"
    assert empty_result["dimension"] == "0D"
    assert empty_result["context"] == ""
    assert empty_result["date_label"] == ""
    assert empty_result["participant_count"] == 0
