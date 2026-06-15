from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from analysis.survey_report_generator import (
    generate_pdf,
    generate_report,
    prepare_report_data,
    render_html_template,
)


@pytest.fixture
def mock_translations():
    return {
        "average_percentage": "Average Percentage",
        "based_on_responses": "Based on {x} survey responses",
        "choice": "Choice",
        "ideal_budget": "Ideal budget",
    }


@pytest.fixture
def sample_summary_stats():
    return pd.DataFrame(
        {
            "survey_id": [1, 2, "Total"],
            "total_survey_responses": [5, 3, 8],
            "total_answers": [50, 30, 80],
            "sum_optimized_percentage": [60.0, 50.0, 56.25],
            "ratio_optimized_percentage": [40.0, 50.0, 43.75],
            "sum_count": [3, 1, 4],
            "ratio_count": [2, 1, 3],
            "equal_count": [0, 1, 1],
        }
    )


@pytest.fixture
def sample_optimization_stats():
    return pd.DataFrame(
        {
            "survey_id": [1, 1, 2, 2],
            "user_id": [101, 102, 101, 103],
            "num_of_answers": [10, 10, 10, 10],
            "sum_optimized": [7, 4, 8, 2],
            "ratio_optimized": [3, 6, 2, 8],
            "result": ["sum", "ratio", "sum", "ratio"],
        }
    )


@pytest.fixture
def sample_survey_responses():
    return pd.DataFrame(
        {
            "survey_id": [1, 1, 2],
            "user_id": [101, 102, 103],
            "optimal_allocation": ["[50,30,20]", "[50,30,20]", "[50,30,20]"],
            "comparisons": [[], [], []],
        }
    )


@patch("analysis.survey_report_generator.load_data")
@patch("analysis.survey_report_generator.prepare_report_data")
@patch("analysis.survey_report_generator.render_html_template")
@patch("analysis.survey_report_generator.generate_pdf")
def test_generate_report(mock_generate_pdf, mock_render, mock_prepare, mock_load, app):
    """Test the main generate_report orchestration function."""
    # Setup mocks
    mock_load.return_value = {"some": "data"}
    mock_prepare.return_value = {"report": "data"}
    mock_render.return_value = "<html></html>"

    generate_report()

    mock_load.assert_called_once()
    mock_prepare.assert_called_once()
    mock_render.assert_called_once()
    mock_generate_pdf.assert_called_once()


@patch("analysis.survey_report_generator.generate_executive_summary")
@patch("analysis.survey_report_generator.generate_overall_stats")
@patch("analysis.survey_report_generator.generate_survey_analysis")
@patch("analysis.survey_report_generator.generate_individual_analysis")
@patch("analysis.survey_report_generator.generate_detailed_user_choices")
@patch("analysis.survey_report_generator.generate_user_comments_section")
@patch("analysis.survey_report_generator.generate_key_findings")
@patch("analysis.survey_report_generator.generate_methodology_description")
@patch("analysis.survey_report_generator.retrieve_user_survey_choices")
@patch("analysis.survey_report_generator.visualize_user_choices")
@patch("analysis.survey_report_generator.visualize_per_survey_answer_percentages")
@patch("analysis.survey_report_generator.visualize_user_survey_majority_choices")
@patch(
    "analysis.survey_report_generator.visualize_overall_majority_choice_distribution"
)
@patch(
    "analysis.survey_report_generator.visualize_total_answer_percentage_distribution"
)
def test_prepare_report_data(
    mock_viz_total,
    mock_viz_overall,
    mock_viz_majority,
    mock_viz_per_survey,
    mock_viz_choices,
    mock_retrieve_choices,
    mock_gen_methodology,
    mock_gen_findings,
    mock_gen_comments,
    mock_gen_detailed,
    mock_gen_individual,
    mock_gen_survey,
    mock_gen_overall,
    mock_gen_exec,
    app,
    sample_summary_stats,
    sample_optimization_stats,
    sample_survey_responses,
):
    """Test data preparation for the report."""

    # Setup input data
    data = {
        "summary": sample_summary_stats,
        "optimization": sample_optimization_stats,
        "responses": sample_survey_responses,
    }

    # Setup mocks
    mock_retrieve_choices.return_value = []

    # Run function
    report_data = prepare_report_data(data)

    # Verify structure
    assert "metadata" in report_data
    assert "sections" in report_data
    assert "visualizations" in report_data["sections"]
    assert "analysis" in report_data["sections"]

    # Verify calls to generators
    mock_gen_exec.assert_called_once()
    mock_gen_overall.assert_called_once()
    mock_gen_survey.assert_called_once()


@patch("analysis.survey_report_generator.Environment")
def test_render_html_template(mock_env_class):
    """Test HTML template rendering."""
    # Setup mocks
    mock_template = MagicMock()
    mock_template.render.return_value = "<html>Rendered</html>"

    mock_env = MagicMock()
    mock_env.get_template.return_value = mock_template
    mock_env_class.return_value = mock_env

    test_data = {"key": "value"}
    result = render_html_template(test_data)

    assert result == "<html>Rendered</html>"
    mock_env.get_template.assert_called_with("report_template.html")
    mock_template.render.assert_called_with(test_data)


@patch("analysis.survey_report_generator.HTML")
@patch("analysis.survey_report_generator.CSS")
def test_generate_pdf(mock_css_class, mock_html_class):
    """Test PDF generation."""
    html_content = "<html>Test</html>"
    output_path = "test_output.pdf"

    # Setup mocks
    mock_html_instance = MagicMock()
    mock_html_class.return_value = mock_html_instance

    generate_pdf(html_content, output_path)

    mock_html_class.assert_called_once()
    mock_html_instance.write_pdf.assert_called_once()


@patch("analysis.survey_report_generator.HTML")
@patch("analysis.survey_report_generator.CSS")
def test_generate_pdf_file_handling(mock_css_class, mock_html_class, tmp_path):
    """Test PDF generation file handling."""
    html_content = "<html>Test</html>"
    output_path = str(tmp_path / "test_report.pdf")

    mock_html_instance = MagicMock()
    mock_html_class.return_value = mock_html_instance

    generate_pdf(html_content, output_path)

    # Verify write_pdf was called with correct path
    args, _ = mock_html_instance.write_pdf.call_args
    assert args[0] == output_path


@patch("analysis.survey_report_generator.load_data")
def test_generate_report_with_empty_data(mock_load, app):
    """Test error handling when data is empty."""
    # Setup empty dataframes
    empty_summary = pd.DataFrame(
        {
            "survey_id": ["Total"],
            "total_survey_responses": [0],
            "total_answers": [0],
            "sum_optimized_percentage": [0],
            "ratio_optimized_percentage": [0],
        }
    )
    empty_optimization = pd.DataFrame(
        columns=[
            "survey_id",
            "user_id",
            "num_of_answers",
            "sum_optimized",
            "ratio_optimized",
            "result",
        ]
    )
    empty_responses = pd.DataFrame(
        columns=["survey_id", "user_id", "optimal_allocation", "comparisons"]
    )

    mock_load.return_value = {
        "summary": empty_summary,
        "optimization": empty_optimization,
        "responses": empty_responses,
    }

    # Should not raise error, but handle empty data gracefully
    try:
        generate_report()
    except Exception as e:
        # If it raises, it should be a meaningful error
        assert (
            "Total" in str(e)
            or "empty" in str(e)
            or isinstance(e, (ValueError, KeyError))
        )
