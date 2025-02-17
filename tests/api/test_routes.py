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
        f"/?userID={sample_user_id}&surveyID={sample_survey_id}&lang=en"
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
        f"/create_vector?userID={sample_user_id}&surveyID={sample_survey_id}&lang=en"
    )
    assert response.status_code == 200

    response = client.post(
        f"/create_vector?userID={sample_user_id}&surveyID={sample_survey_id}&lang=en",
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
        f"/create_vector?userID={sample_user_id}&surveyID={sample_survey_id}&lang=en",
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
        f"/survey?userID={sample_user_id}&surveyID={sample_survey_id}&vector=50,50&lang=en"
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
        f"/survey?userID={sample_user_id}&surveyID={sample_survey_id}&lang=en",
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
    response = client.get("/thank_you?lang=en")
    assert response.status_code == 200


def test_report_route(client, monkeypatch):
    """Tests report generation endpoint."""
    monkeypatch.setattr("flask.send_file", lambda *args, **kwargs: "")
    response = client.get("/report")
    assert response.status_code == 200


def test_missing_parameters(client):
    """Tests error handling for missing required parameters."""
    response = client.get("/")
    assert response.status_code == 400

    response = client.get("/?userID=123")
    assert response.status_code == 400

    response = client.get("/?surveyID=123")
    assert response.status_code == 400


def test_panel4all_status_codes(app):
    """Test Panel4All status code configuration."""
    assert "PANEL4ALL" in app.config
    assert "STATUS" in app.config["PANEL4ALL"]
    assert app.config["PANEL4ALL"]["STATUS"]["COMPLETE"] == "finish"
    assert app.config["PANEL4ALL"]["STATUS"]["ATTENTION_FAILED"] == "attentionfilter"
