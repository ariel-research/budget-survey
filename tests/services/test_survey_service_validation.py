"""Integration tests for SurveyService validation logic."""

from unittest.mock import MagicMock, patch

import pytest

from application.exceptions import UnsuitableForStrategyError
from application.services.survey_service import SurveyService


@pytest.fixture
def mock_get_rules():
    with patch(
        "application.services.survey_service.get_survey_suitability_rules"
    ) as mock:
        yield mock


@pytest.fixture
def mock_get_config():
    with patch(
        "application.services.survey_service.get_survey_pair_generation_config"
    ) as mock:
        mock.return_value = {"strategy": "asymmetric_loss_distribution", "params": {}}
        yield mock


@pytest.fixture
def mock_strategy_registry():
    with patch("application.services.survey_service.StrategyRegistry") as mock:
        mock_strategy = MagicMock()
        mock_strategy.generate_pairs.return_value = [{"pair": 1}]
        mock.get_strategy.return_value = mock_strategy
        yield mock


@pytest.fixture
def mock_get_translation():
    with patch("application.services.survey_service.get_translation") as mock:
        # Return the expected string so assertions pass
        mock.return_value = "User vector contains too many zero values"
        yield mock


def test_generate_pairs_blocks_zero_values_when_configured(
    mock_get_rules, mock_get_config, mock_strategy_registry, mock_get_translation
):
    """Ensure service raises error if DB rules forbid zeros."""
    # Setup: DB says max 0 zeros allowed
    mock_get_rules.return_value = {"max_zero_values": 0}

    # Input: Vector with a zero
    user_vector = [50, 50, 0]

    # Assert: Service raises error
    with pytest.raises(UnsuitableForStrategyError) as exc:
        SurveyService.generate_survey_pairs(user_vector, 3, survey_id=1)

    assert "User vector contains too many zero values" in str(exc.value)


def test_generate_pairs_allows_valid_vectors(
    mock_get_rules, mock_get_config, mock_strategy_registry
):
    """Ensure service proceeds if validation passes."""
    # Setup: DB says max 0 zeros allowed
    mock_get_rules.return_value = {"max_zero_values": 0}

    # Input: Vector with NO zeros
    user_vector = [50, 25, 25]

    # Act: Should not raise
    SurveyService.generate_survey_pairs(user_vector, 3, survey_id=1)

    # Verify rules were checked
    mock_get_rules.assert_called_with(1)


def test_generate_pairs_skips_check_if_no_rules(
    mock_get_rules, mock_get_config, mock_strategy_registry
):
    """Ensure backward compatibility if no rules exist."""
    # Setup: No rules in DB
    mock_get_rules.return_value = None

    # Input: Vector with zero (should pass validation here)
    user_vector = [50, 50, 0]

    # Act: Should proceed
    SurveyService.generate_survey_pairs(user_vector, 3, survey_id=1)
