import os
from unittest.mock import Mock, mock_open, patch

import pandas as pd
import pytest
from jinja2 import Environment

from analysis.survey_report_generator_pdf import (
    generate_pdf,
    generate_report,
    prepare_report_data,
    render_html_template,
)


@patch("analysis.survey_report_generator_pdf.load_data")
@patch("analysis.survey_report_generator_pdf.prepare_report_data")
@patch("analysis.survey_report_generator_pdf.render_html_template")
@patch("analysis.survey_report_generator_pdf.generate_pdf")
def test_generate_report(mock_generate_pdf, mock_render, mock_prepare, mock_load, app):
    """Test the complete report generation process."""
    # Setup mock returns
    mock_load.return_value = {
        "summary": pd.DataFrame(
            {"survey_id": ["Total"], "total_survey_responses": [1]}
        ),
        "optimization": pd.DataFrame({"survey_id": [1], "user_id": ["test"]}),
        "responses": pd.DataFrame({"survey_id": [1], "user_id": ["test"]}),
    }
    mock_prepare.return_value = {"key": "value"}
    mock_render.return_value = "<html>Test</html>"

    # Execute
    generate_report()

    # Assert
    mock_load.assert_called_once()
    mock_prepare.assert_called_once()
    mock_render.assert_called_once_with({"key": "value"})
    mock_generate_pdf.assert_called_once_with(
        "<html>Test</html>", "data/survey_analysis_report.pdf"
    )


def test_prepare_report_data(
    sample_summary_stats, sample_optimization_stats, sample_survey_responses, app
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
        "metadata": {
            "generated_date": "2024-01-01",
            "total_surveys": 1,
            "total_participants": 1,
            "total_survey_responses": 1,
        },
        "sections": {
            "executive_summary": "Test summary",
            "overall_stats": "Test stats",
            "visualizations": {},
            "analysis": {"survey": "Test analysis", "methodology": "Test methodology"},
        },
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

    # Create mock for WeasyPrint HTML and CSS
    mock_css = Mock()
    mock_html = Mock()
    mock_html.write_pdf = Mock()

    with (
        patch(
            "analysis.survey_report_generator_pdf.CSS", return_value=mock_css
        ) as mock_css_class,
        patch(
            "analysis.survey_report_generator_pdf.HTML", return_value=mock_html
        ) as mock_html_class,
    ):

        generate_pdf(html_content)

        # Verify calls
        mock_abspath.assert_called_once_with("analysis/templates/report_style.css")
        mock_css_class.assert_called_once_with(filename=css_path)
        mock_html_class.assert_called_once_with(
            string=html_content, base_url=os.path.dirname(css_path)
        )
        mock_html.write_pdf.assert_called_once_with(
            "data/survey_analysis_report.pdf", stylesheets=[mock_css]
        )


@patch("analysis.survey_report_generator_pdf.load_data")
def test_generate_report_with_empty_data(mock_load, app):
    """Test report generation with empty data."""
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

    with pytest.raises(ValueError) as exc_info:
        generate_report()

    assert "input dataframe is empty" in str(exc_info.value).lower()
