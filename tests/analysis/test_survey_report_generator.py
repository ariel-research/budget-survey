import os
import sys
from unittest.mock import ANY, Mock, mock_open, patch

import pandas as pd
import pytest
from jinja2 import Environment

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from analysis.survey_report_generator_pdf import (
    generate_pdf,
    generate_report,
    prepare_report_data,
    render_html_template,
)


@patch("analysis.survey_report_generator.load_data")
@patch("analysis.survey_report_generator.prepare_report_data")
@patch("analysis.survey_report_generator.render_html_template")
@patch("analysis.survey_report_generator_pdf.generate_pdf")
def test_generate_report(mock_generate_pdf, mock_render, mock_prepare, mock_load):
    """Test the complete report generation process."""
    mock_load.return_value = {
        "summary": pd.DataFrame(),
        "optimization": pd.DataFrame(),
        "responses": pd.DataFrame(),
    }
    mock_prepare.return_value = {"key": "value"}
    mock_render.return_value = "<html>Test</html>"

    generate_report()

    mock_load.assert_called_once()
    mock_prepare.assert_called_once()
    mock_render.assert_called_once_with({"key": "value"})
    mock_generate_pdf.assert_called_once_with("<html>Test</html>")


def test_prepare_report_data(
    sample_summary_stats, sample_optimization_stats, sample_survey_responses
):
    """Test preparation of report data using fixture data."""
    sample_data = {
        "summary": sample_summary_stats,
        "optimization": sample_optimization_stats,
        "responses": sample_survey_responses,
    }

    result = prepare_report_data(sample_data)

    assert isinstance(result, dict)
    assert "metadata" in result
    assert "sections" in result

    # Check metadata
    assert "generated_date" in result["metadata"]
    assert isinstance(result["metadata"]["total_surveys"], int)
    assert isinstance(result["metadata"]["total_participants"], int)
    assert isinstance(result["metadata"]["total_survey_responses"], int)

    # Check sections
    sections = result["sections"]
    assert "executive_summary" in sections
    assert "overall_stats" in sections
    assert "visualizations" in sections
    assert "analysis" in sections

    # Check visualizations
    viz = sections["visualizations"]
    assert "user_choices" in viz
    assert "per_survey_percentages" in viz
    assert "user_majority_choices" in viz
    assert "overall_distribution" in viz
    assert "answer_distribution" in viz

    # Check analysis sections
    analysis = sections["analysis"]
    assert "survey" in analysis
    assert "individual" in analysis
    assert "detailed_choices" in analysis
    assert "findings" in analysis
    assert "methodology" in analysis


def test_render_html_template():
    """Test HTML template rendering."""
    test_data = {
        "generated_date": "2024-01-01",
        "executive_summary": "Test summary",
        "overall_stats": "Test stats",
        "survey_analysis": "Test analysis",
        "methodology": "Test methodology",
    }

    with patch.object(Environment, "get_template") as mock_get_template:
        mock_template = Mock()
        mock_template.render.return_value = "<html>Test Report</html>"
        mock_get_template.return_value = mock_template

        result = render_html_template(test_data)

        assert isinstance(result, str)
        mock_template.render.assert_called_once_with(test_data)


@patch("builtins.open", new_callable=mock_open, read_data="dummy css content")
@patch("weasyprint.HTML.write_pdf")
@patch("os.path.abspath")
def test_generate_pdf(mock_abspath, mock_write_pdf, mock_file):
    """Test PDF generation from HTML content."""
    html_content = "<html>Test Report</html>"
    mock_abspath.return_value = "/mock/path/style.css"

    generate_pdf(html_content)

    mock_file.assert_called_with("/mock/path/style.css", "rb")
    mock_write_pdf.assert_called_once()


@patch("builtins.open", new_callable=mock_open, read_data="dummy css content")
@patch("os.path.abspath")
def test_generate_pdf_file_handling(mock_abspath, mock_file, tmp_path):
    """Test PDF file handling during generation."""
    css_path = str(tmp_path / "templates/report_style.css")
    mock_abspath.return_value = css_path
    html_content = "<html>Test Report</html>"

    # Create a mock for the write_pdf method
    mock_write_pdf = Mock()
    # Create a mock for the HTML class
    mock_html_instance = Mock()
    mock_html_instance.write_pdf = mock_write_pdf

    # Create a mock HTML class that returns our mock instance
    mock_html_class = Mock(return_value=mock_html_instance)

    with patch("analysis.survey_report_generator_pdf.HTML", mock_html_class):
        generate_pdf(html_content)

        # Verify HTML was created with correct parameters
        mock_html_class.assert_called_once_with(
            string=html_content, base_url=os.path.dirname(css_path)
        )
        # Verify write_pdf was called with correct parameters
        mock_write_pdf.assert_called_once_with(
            "data/survey_analysis_report.pdf",
            stylesheets=[ANY],  # Use ANY to avoid CSS object comparison
        )


@patch("analysis.survey_report_generator.load_data")
def test_generate_report_with_empty_data(mock_load):
    """Test report generation with empty data."""
    # Create empty summary DataFrame with required structure
    empty_summary = pd.DataFrame(
        {
            "survey_id": ["Total"],
            "total_survey_responses": [0],
            "unique_users": [0],
            "total_answers": [0],
            "sum_optimized": [0],
            "ratio_optimized": [0],
            "sum_optimized_percentage": [0],
            "ratio_optimized_percentage": [0],
            "sum_count": [0],
            "ratio_count": [0],
            "equal_count": [0],
        }
    )

    # Create empty optimization DataFrame with required structure
    empty_optimization = pd.DataFrame(
        {
            "survey_id": pd.Series([], dtype="int64"),
            "user_id": pd.Series([], dtype="object"),
            "num_of_answers": pd.Series([], dtype="int64"),
            "sum_optimized": pd.Series([], dtype="int64"),
            "ratio_optimized": pd.Series([], dtype="int64"),
            "result": pd.Series([], dtype="object"),
        }
    )

    # Create empty responses DataFrame with required structure
    empty_responses = pd.DataFrame(
        {
            "survey_id": pd.Series([], dtype="int64"),
            "user_id": pd.Series([], dtype="object"),
            "optimal_allocation": pd.Series([], dtype="object"),
            "comparisons": pd.Series([], dtype="object"),
        }
    )

    mock_load.return_value = {
        "summary": empty_summary,
        "optimization": empty_optimization,
        "responses": empty_responses,
    }

    # Generate report should raise ValueError for empty data
    with pytest.raises(ValueError) as exc_info:
        generate_report()

    # Check that the error message contains 'empty'
    assert "empty" in str(exc_info.value).lower()
