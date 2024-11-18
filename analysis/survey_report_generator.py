import logging
import os
from datetime import datetime
from typing import Any, Dict

import pandas as pd
from jinja2 import Environment, FileSystemLoader
from weasyprint import CSS, HTML

from analysis.report_content_generators import (
    generate_detailed_user_choices,
    generate_executive_summary,
    generate_individual_analysis,
    generate_key_findings,
    generate_methodology_description,
    generate_overall_stats,
    generate_survey_analysis,
    generate_user_comments_section,
)
from analysis.utils import (
    load_data,
    visualize_overall_majority_choice_distribution,
    visualize_per_survey_answer_percentages,
    visualize_total_answer_percentage_distribution,
    visualize_user_choices,
    visualize_user_survey_majority_choices,
)
from database.queries import retrieve_user_survey_choices
from logging_config import setup_logging

# from app import create_app

# app = create_app()


pd.set_option("future.no_silent_downcasting", True)

setup_logging()
logger = logging.getLogger(__name__)


def generate_report(output_path: str = "data/survey_analysis_report.pdf") -> None:
    """
    Generate and save the survey analysis report as a PDF.

    Args:
        output_path (str): Path where the PDF should be saved. Defaults to "data/survey_analysis_report.pdf"
    """
    logger.info("Starting report generation process")

    try:
        data = load_data()
        logger.info("Data loaded successfully")
        report_data = prepare_report_data(data)
        logger.info("Report data prepared")
        html_content = render_html_template(report_data)
        logger.info("HTML content rendered")
        generate_pdf(html_content, output_path)
        logger.info("PDF Report generated successfully")
    except Exception as e:
        logger.error(
            f"Error occurred during report generation: {str(e)}", exc_info=True
        )
        raise


def prepare_report_data(data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """
    Prepare all the data needed for the report.

    Args:
        data (Dict[str, pd.DataFrame]): Dictionary containing:
            - 'summary': summarize_stats_by_survey.csv data
            - 'optimization': survey_optimization_stats.csv data
            - 'responses': all_completed_survey_responses.csv data

    Returns:
        Dict[str, Any]: Prepared data for the report template.
    """
    logger.info("Preparing report data")

    try:
        report_data = {
            "metadata": {
                "generated_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "total_surveys": data["responses"]["survey_id"].nunique(),
                "total_participants": data["responses"]["user_id"].nunique(),
                "total_survey_responses": len(data["responses"]),
            },
            "sections": {
                "executive_summary": generate_executive_summary(
                    data["summary"], data["optimization"], data["responses"]
                ),
                "overall_stats": generate_overall_stats(
                    data["summary"], data["optimization"]
                ),
                "visualizations": {
                    "user_choices": visualize_user_choices(
                        retrieve_user_survey_choices()
                    ),
                    "per_survey_percentages": visualize_per_survey_answer_percentages(
                        data["summary"]
                    ),
                    "user_majority_choices": visualize_user_survey_majority_choices(
                        data["optimization"]
                    ),
                    "overall_distribution": visualize_overall_majority_choice_distribution(
                        data["summary"]
                    ),
                    "answer_distribution": visualize_total_answer_percentage_distribution(
                        data["summary"]
                    ),
                },
                "analysis": {
                    "survey": generate_survey_analysis(data["summary"]),
                    "individual": generate_individual_analysis(data["optimization"]),
                    "detailed_choices": generate_detailed_user_choices(
                        retrieve_user_survey_choices()
                    ),
                    "user_comments": generate_user_comments_section(data["responses"]),
                    "findings": generate_key_findings(
                        data["summary"], data["optimization"]
                    ),
                    "methodology": generate_methodology_description(),
                },
            },
        }

        logger.info("Report data preparation completed successfully")
        return report_data

    except Exception as e:
        logger.error(f"Error preparing report data: {str(e)}", exc_info=True)
        raise


def render_html_template(report_data: Dict[str, Any]) -> str:
    """
    Render the HTML template with the report data.

    Args:
        report_data (Dict[str, Any]): Prepared data for the report template.

    Returns:
        str: Rendered HTML content.
    """
    logger.info("Rendering HTML template")
    env = Environment(loader=FileSystemLoader("analysis/templates"))
    template = env.get_template("report_template.html")
    return template.render(report_data)


def generate_pdf(
    html_content: str, output_path: str = "data/survey_analysis_report.pdf"
) -> None:
    """
    Generate the PDF from the HTML content.

    Args:
        html_content (str): Rendered HTML content.
        output_path (str): Path where the PDF should be saved.
    """
    logger.info(f"Generating PDF from HTML content to {output_path}")
    css_path = os.path.abspath("analysis/templates/report_style.css")
    css = CSS(filename=css_path)
    base_url = os.path.dirname(css_path)
    HTML(string=html_content, base_url=base_url).write_pdf(
        output_path, stylesheets=[css]
    )
    logger.info(f"PDF saved to {output_path}")


if __name__ == "__main__":
    generate_report()
