def test_index_route(client, sample_user_id, sample_survey_id, monkeypatch):
    """Tests the index route with valid parameters and English language."""

    def mock_survey_exists(*args):
        return True, None, {"name": "Test Survey", "subjects": ["Health", "Education"]}

    monkeypatch.setattr(
        "application.services.survey_service.SurveyService.check_survey_exists",
        mock_survey_exists,
    )
    monkeypatch.setattr(
        "database.queries.check_user_participation", lambda *args: False
    )

    with client.session_transaction() as sess:
        sess["language"] = "en"

    response = client.get(
        f"/take-survey/?userID={sample_user_id}&surveyID={sample_survey_id}&lang=en"
    )
    assert response.status_code == 200


def test_create_vector_route(client, sample_user_id, sample_survey_id, monkeypatch):
    """Tests both GET and POST methods of create_vector route."""

    def mock_survey_exists(*args):
        return True, None, {"subjects": ["Health", "Education"]}

    monkeypatch.setattr(
        "application.services.survey_service.SurveyService.check_survey_exists",
        mock_survey_exists,
    )
    monkeypatch.setattr(
        "application.services.survey_service.SurveyService.validate_vector",
        lambda *args: True,
    )

    with client.session_transaction() as sess:
        sess["language"] = "en"

    response = client.get(
        f"/take-survey/create_vector?userID={sample_user_id}&surveyID={sample_survey_id}&lang=en"
    )
    assert response.status_code in [200, 302]

    response = client.post(
        f"/take-survey/create_vector?userID={sample_user_id}&surveyID={sample_survey_id}&lang=en",
        data={"Health": "50", "Education": "50"},
    )
    assert response.status_code == 302


def test_invalid_vector(client, sample_user_id, sample_survey_id, monkeypatch):
    """Tests vector validation by submitting invalid budget allocation."""

    def mock_survey_exists(*args):
        return True, None, {"subjects": ["Health", "Education"]}

    monkeypatch.setattr(
        "application.services.survey_service.SurveyService.check_survey_exists",
        mock_survey_exists,
    )
    monkeypatch.setattr(
        "application.services.survey_service.SurveyService.validate_vector",
        lambda *args: False,
    )
    with client.session_transaction() as sess:
        sess["language"] = "en"

    response = client.post(
        f"/take-survey/create_vector?userID={sample_user_id}&surveyID={sample_survey_id}&lang=en",
        data={"Health": "60", "Education": "60"},
    )
    assert response.status_code == 200


def test_survey_route(client, sample_user_id, sample_survey_id, monkeypatch):
    """Tests survey page rendering with mocked session data."""

    def mock_survey_exists(*args):
        return True, None, {"subjects": ["Health", "Education"]}

    def mock_session_data(self, *args, **kwargs):
        return {
            "user_vector": [50, 50],
            "comparison_pairs": [
                {"display": ([60, 40], [40, 60]), "was_swapped": False}
            ],
            "awareness_check": {
                "option1": [60, 40],
                "option2": [50, 50],
                "correct_answer": 2,
            },
            "subjects": ["Health", "Education"],
            "user_id": sample_user_id,
            "survey_id": sample_survey_id,
            "zip": zip,
        }

    monkeypatch.setattr(
        "application.services.survey_service.SurveyService.check_survey_exists",
        mock_survey_exists,
    )
    monkeypatch.setattr(
        "application.services.survey_service.SurveySessionData.to_template_data",
        mock_session_data,
    )

    with client.session_transaction() as sess:
        sess["language"] = "en"

    response = client.get(
        f"/take-survey/survey?userID={sample_user_id}&surveyID={sample_survey_id}&vector=50,50&lang=en"
    )
    assert response.status_code == 200


def test_survey_submission(client, sample_user_id, sample_survey_id, monkeypatch):
    """Tests successful survey submission processing."""

    def mock_survey_exists(*args):
        return True, None, {"subjects": ["Health", "Education"]}

    monkeypatch.setattr(
        "application.services.survey_service.SurveyService.check_survey_exists",
        mock_survey_exists,
    )
    monkeypatch.setattr(
        "application.services.survey_service.SurveyService.process_survey_submission",
        lambda *args: None,
    )

    with client.session_transaction() as sess:
        sess["language"] = "en"

    response = client.post(
        f"/take-survey/survey?userID={sample_user_id}&surveyID={sample_survey_id}&lang=en",
        data={
            "user_vector": "50,50",
            "awareness_check": "2",
            "option1_0": "60,40",
            "option2_0": "40,60",
            "choice_0": "1",
        },
    )
    assert response.status_code in [200, 302]


def test_thank_you_route(client):
    """Tests thank you page rendering."""
    with client.session_transaction() as sess:
        sess["language"] = "en"
    response = client.get("/take-survey/thank_you?lang=en")
    assert response.status_code == 200


def test_report_route(client, monkeypatch):
    """Tests report generation endpoint."""
    monkeypatch.setattr("flask.send_file", lambda *args, **kwargs: "")
    response = client.get("/report")
    assert response.status_code == 200


def test_missing_parameters(client):
    """Tests error handling for missing required parameters."""
    response = client.get("/take-survey/")
    assert response.status_code == 400

    response = client.get("/take-survey/?userID=123")
    assert response.status_code == 400

    response = client.get("/take-survey/?surveyID=123")
    assert response.status_code == 400


def test_panel4all_status_codes(app):
    """Test Panel4All status code configuration."""
    assert "PANEL4ALL" in app.config
    assert "STATUS" in app.config["PANEL4ALL"]
    assert "COMPLETE" in app.config["PANEL4ALL"]["STATUS"]
    assert "ATTENTION_FAILED" in app.config["PANEL4ALL"]["STATUS"]
    # assert app.config["PANEL4ALL"]["STATUS"]["COMPLETE"] == "finish"
    # assert app.config["PANEL4ALL"]["STATUS"]["ATTENTION_FAILED"] == "attentionfilter"


def test_get_users_overview_route(client, monkeypatch):
    """Tests the users overview endpoint with sample data."""

    # Mock user participation data
    mock_user_data = [
        {
            "user_id": "user123",
            "successful_surveys_count": 2,
            "failed_surveys_count": 1,
            "last_activity": "2024-01-15 10:30:00",
            "successful_survey_ids": "1,3",
            "failed_survey_ids": "2",
        },
        {
            "user_id": "user456",
            "successful_surveys_count": 1,
            "failed_surveys_count": 0,
            "last_activity": "2024-01-14 09:15:00",
            "successful_survey_ids": "1",
            "failed_survey_ids": "",
        },
    ]

    monkeypatch.setattr(
        "database.queries.get_user_participation_overview", lambda: mock_user_data
    )

    # Test basic route
    response = client.get("/surveys/users")
    assert response.status_code == 200


def test_get_users_overview_with_sorting(client, monkeypatch):
    """Tests users overview endpoint with sorting parameters."""

    mock_user_data = [
        {
            "user_id": "user123",
            "successful_surveys_count": 2,
            "failed_surveys_count": 1,
            "last_activity": "2024-01-15 10:30:00",
            "successful_survey_ids": "1,3",
            "failed_survey_ids": "2",
        }
    ]

    monkeypatch.setattr(
        "database.queries.get_user_participation_overview", lambda: mock_user_data
    )

    # Test with valid sort parameters
    response = client.get("/surveys/users?sort=user_id&order=desc")
    assert response.status_code == 200

    response = client.get("/surveys/users?sort=last_activity&order=asc")
    assert response.status_code == 200


def test_get_users_overview_empty_data(client, monkeypatch):
    """Tests users overview endpoint when query succeeds but returns no data."""

    # Test both None and empty list scenarios
    for empty_result in [None, []]:
        monkeypatch.setattr(
            "database.queries.get_user_participation_overview", lambda: empty_result
        )

        response = client.get("/surveys/users")
        assert response.status_code == 200
