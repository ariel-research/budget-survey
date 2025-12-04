"""Tests for /api/awareness/check endpoint."""


class TestAwarenessCheckAPI:
    """Test suite for the awareness check API endpoint."""

    def test_correct_first_awareness_returns_valid(self, client):
        """First awareness with answer=1 should return valid=True."""
        payload = {
            "user_id": "test_user_1",
            "internal_survey_id": 4,
            "external_survey_id": "ext_survey_123",
            "question_index": 0,
            "answer": 1,  # Correct for first awareness
            "user_vector": [50, 30, 20],
        }
        response = client.post("/take-survey/api/awareness/check", json=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data["valid"] is True

    def test_correct_second_awareness_returns_valid(self, client):
        """Second awareness with answer=2 should return valid=True."""
        payload = {
            "user_id": "test_user_2",
            "internal_survey_id": 4,
            "external_survey_id": "ext_survey_123",
            "question_index": 1,
            "answer": 2,  # Correct for second awareness
            "user_vector": [50, 30, 20],
        }
        response = client.post("/take-survey/api/awareness/check", json=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data["valid"] is True

    def test_incorrect_first_awareness_returns_redirect(self, client):
        """First awareness with answer=2 should return valid=False with redirect and PTS=7."""
        payload = {
            "user_id": "test_user_3",
            "internal_survey_id": 4,
            "external_survey_id": "ext_survey_123",
            "question_index": 0,
            "answer": 2,  # Wrong for first awareness
            "user_vector": [50, 30, 20],
        }
        response = client.post("/take-survey/api/awareness/check", json=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data["valid"] is False
        assert "redirect_url" in data
        assert "PTS=7" in data["redirect_url"]
        assert data["pts_value"] == 7
        assert "filterout" in data["redirect_url"]
        assert "ext_survey_123" in data["redirect_url"]
        assert "test_user_3" in data["redirect_url"]

    def test_incorrect_second_awareness_returns_pts_10(self, client):
        """Second awareness failure should return PTS=10."""
        payload = {
            "user_id": "test_user_4",
            "internal_survey_id": 4,
            "external_survey_id": "ext_survey_456",
            "question_index": 1,
            "answer": 1,  # Wrong for second awareness (should be 2)
            "user_vector": [50, 30, 20],
        }
        response = client.post("/take-survey/api/awareness/check", json=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data["valid"] is False
        assert "PTS=10" in data["redirect_url"]
        assert data["pts_value"] == 10
        assert "filterout" in data["redirect_url"]

    def test_missing_user_id_returns_400(self, client):
        """Missing user_id should return 400."""
        payload = {
            "internal_survey_id": 4,
            "external_survey_id": "ext_123",
            "question_index": 0,
            "answer": 1,
            "user_vector": [50, 30, 20],
        }
        response = client.post("/take-survey/api/awareness/check", json=payload)
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_missing_internal_survey_id_returns_400(self, client):
        """Missing internal_survey_id should return 400."""
        payload = {
            "user_id": "test_user",
            "external_survey_id": "ext_123",
            "question_index": 0,
            "answer": 1,
            "user_vector": [50, 30, 20],
        }
        response = client.post("/take-survey/api/awareness/check", json=payload)
        assert response.status_code == 400

    def test_missing_external_survey_id_returns_400(self, client):
        """Missing external_survey_id should return 400."""
        payload = {
            "user_id": "test_user",
            "internal_survey_id": 4,
            "question_index": 0,
            "answer": 1,
            "user_vector": [50, 30, 20],
        }
        response = client.post("/take-survey/api/awareness/check", json=payload)
        assert response.status_code == 400

    def test_missing_question_index_returns_400(self, client):
        """Missing question_index should return 400."""
        payload = {
            "user_id": "test_user",
            "internal_survey_id": 4,
            "external_survey_id": "ext_123",
            "answer": 1,
            "user_vector": [50, 30, 20],
        }
        response = client.post("/take-survey/api/awareness/check", json=payload)
        assert response.status_code == 400

    def test_missing_answer_returns_400(self, client):
        """Missing answer should return 400."""
        payload = {
            "user_id": "test_user",
            "internal_survey_id": 4,
            "external_survey_id": "ext_123",
            "question_index": 0,
            "user_vector": [50, 30, 20],
        }
        response = client.post("/take-survey/api/awareness/check", json=payload)
        assert response.status_code == 400

    def test_missing_user_vector_returns_400(self, client):
        """Missing user_vector should return 400."""
        payload = {
            "user_id": "test_user",
            "internal_survey_id": 4,
            "external_survey_id": "ext_123",
            "question_index": 0,
            "answer": 1,
        }
        response = client.post("/take-survey/api/awareness/check", json=payload)
        assert response.status_code == 400

    def test_invalid_question_index_type_returns_400(self, client):
        """Invalid question_index type should return 400."""
        payload = {
            "user_id": "test_user",
            "internal_survey_id": 4,
            "external_survey_id": "ext_123",
            "question_index": "invalid",
            "answer": 1,
            "user_vector": [50, 30, 20],
        }
        response = client.post("/take-survey/api/awareness/check", json=payload)
        assert response.status_code == 400

    def test_non_numeric_answer_treated_as_wrong(self, client):
        """Non-numeric answer is treated as incorrect (not a validation error)."""
        payload = {
            "user_id": "test_user",
            "internal_survey_id": 4,
            "external_survey_id": "ext_123",
            "question_index": 0,
            "answer": "invalid",  # Will not equal 1, so treated as wrong answer
            "user_vector": [50, 30, 20],
        }
        response = client.post("/take-survey/api/awareness/check", json=payload)
        # Non-numeric answer is treated as an incorrect answer, not a 400 error
        assert response.status_code == 200
        data = response.get_json()
        assert data["valid"] is False  # Wrong answer
        assert "PTS=7" in data["redirect_url"]
