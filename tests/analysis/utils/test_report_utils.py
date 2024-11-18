from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from flask import Flask

# Create a test Flask app and context
app = Flask(__name__)


@pytest.fixture
def app_context():
    """Provide Flask application context for tests."""
    with app.app_context():
        yield


# Mock the entire survey_analysis module
mock_survey_analysis = Mock()
mock_survey_analysis.main = Mock()


@patch.dict("sys.modules", {"analysis.survey_analysis": mock_survey_analysis})
def test_ensure_fresh_csvs_with_no_files(app_context):
    """Test when no CSV files exist."""
    with (
        patch("analysis.utils.report_utils.CSV_PATHS", ["test.csv"]),
        patch("os.path.exists", return_value=False),
        patch(
            "database.queries.execute_query", return_value=[{"latest": datetime.now()}]
        ),
    ):
        from analysis.utils.report_utils import ensure_fresh_csvs

        result = ensure_fresh_csvs()
        assert result is True
        mock_survey_analysis.main.assert_called_once()


def test_ensure_fresh_csvs_with_outdated_files(app_context):
    """Test when CSV files exist but are outdated."""
    now = datetime.now()
    with (
        patch("analysis.utils.report_utils.CSV_PATHS", ["test.csv"]),
        patch("os.path.exists", return_value=True),
        patch("os.path.getmtime", return_value=50),
        patch("database.queries.execute_query", return_value=[{"latest": now}]),
        patch("analysis.survey_analysis.main") as mock_main,
    ):
        from analysis.utils.report_utils import ensure_fresh_csvs

        result = ensure_fresh_csvs()
        assert result is True
        mock_main.assert_called_once()


def test_ensure_fresh_csvs_with_up_to_date_files(app_context):
    """Test when CSV files exist and are up to date."""
    old_time = datetime.fromtimestamp(50)
    with (
        patch("analysis.utils.report_utils.CSV_PATHS", ["test.csv"]),
        patch("os.path.exists", return_value=True),
        patch("os.path.getmtime", return_value=100),
        patch("database.queries.execute_query", return_value=[{"latest": old_time}]),
        patch("analysis.survey_analysis.main") as mock_main,
    ):
        from analysis.utils.report_utils import ensure_fresh_csvs

        result = ensure_fresh_csvs()
        assert result is False
        mock_main.assert_not_called()


def test_ensure_fresh_report_regeneration_needed(app_context):
    """Test report regeneration when CSVs are updated."""
    mock_csv_checker = Mock(return_value=True)
    with (
        patch("analysis.utils.report_utils.ensure_fresh_csvs", mock_csv_checker),
        patch("os.path.exists", return_value=True),
        patch("analysis.survey_report_generator.generate_report") as mock_generate,
    ):
        from analysis.utils.report_utils import ensure_fresh_report

        ensure_fresh_report()
        mock_generate.assert_called_once()


def test_ensure_fresh_report_no_regeneration(app_context):
    """Test no report regeneration when CSVs are up to date."""
    mock_csv_checker = Mock(return_value=False)
    with (
        patch("analysis.utils.report_utils.ensure_fresh_csvs", mock_csv_checker),
        patch("os.path.exists", return_value=True),
        patch("analysis.survey_report_generator_pdf.generate_report") as mock_generate,
    ):
        from analysis.utils.report_utils import ensure_fresh_report

        ensure_fresh_report()
        mock_generate.assert_not_called()


def test_ensure_fresh_report_error_handling(app_context):
    """Test error handling in report generation."""
    mock_csv_checker = Mock(side_effect=Exception("Test error"))
    with patch("analysis.utils.report_utils.ensure_fresh_csvs", mock_csv_checker):
        from analysis.utils.report_utils import ensure_fresh_report

        with pytest.raises(Exception) as exc_info:
            ensure_fresh_report()
        assert str(exc_info.value) == "Test error"
