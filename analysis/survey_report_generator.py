import logging
from datetime import datetime

import pandas as pd
from jinja2 import Environment, FileSystemLoader
from weasyprint import CSS, HTML

from analysis.report_content_generators import (
    generate_executive_summary,
    generate_individual_analysis,
    generate_key_findings,
    generate_methodology_description,
    generate_overall_stats,
    generate_survey_analysis,
)
from analysis.utils import (
    load_data,
    visualize_overall_majority_choice_distribution,
    visualize_per_survey_answer_percentages,
    visualize_total_answer_percentage_distribution,
    visualize_user_survey_majority_choices,
)

pd.set_option("future.no_silent_downcasting", True)

logger = logging.getLogger(__name__)


def generate_report():
    """Generate and save the survey analysis report as a PDF."""
    logger.info("Starting report generation process")

    try:
        data = load_data()
        report_data = prepare_report_data(data)
        html_content = render_html_template(report_data)
        generate_pdf(html_content)
        logger.info("PDF Report generated successfully")
    except Exception as e:
        logger.error(
            f"Error occurred during report generation: {str(e)}", exc_info=True
        )
        raise


def prepare_report_data(data):
    """Prepare all the data needed for the report."""
    return {
        "generated_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "executive_summary": generate_executive_summary(
            data["summary"], data["optimization"]
        ),
        "overall_stats": generate_overall_stats(data["summary"]),
        "per_survey_answer_percentages": visualize_per_survey_answer_percentages(
            data["summary"]
        ),
        "user_survey_majority_choices": visualize_user_survey_majority_choices(
            data["optimization"]
        ),
        "overall_majority_choice_distribution": visualize_overall_majority_choice_distribution(
            data["summary"]
        ),
        "total_answer_percentage_distribution": visualize_total_answer_percentage_distribution(
            data["summary"]
        ),
        "survey_analysis": generate_survey_analysis(data["summary"]),
        "individual_analysis": generate_individual_analysis(data["optimization"]),
        "key_findings": generate_key_findings(data["summary"], data["optimization"]),
        "methodology": generate_methodology_description(),
    }


def render_html_template(report_data):
    """Render the HTML template with the report data."""
    env = Environment(loader=FileSystemLoader("analysis/templates"))
    template = env.get_template("report_template.html")
    return template.render(report_data)


def generate_pdf(html_content):
    """Generate the PDF from the HTML content."""
    css = CSS(filename="analysis/templates/report_style.css")
    HTML(string=html_content).write_pdf(
        "data/survey_analysis_report.pdf", stylesheets=[css]
    )


if __name__ == "__main__":
    generate_report()
