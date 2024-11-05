"""
Generates the survey report in PDF format.
"""

from survey_report_generator import *

from jinja2 import Environment, FileSystemLoader
from weasyprint import CSS, HTML

def generate_pdf(html_content: str) -> None:
    """
    Generate the PDF from the HTML content.

    Args:
        html_content (str): Rendered HTML content.
    """
    logger.info("Generating PDF from HTML content")
    css_path = os.path.abspath("analysis/templates/report_style.css")
    css = CSS(filename=css_path)
    base_url = os.path.dirname(css_path)
    output_path = "data/survey_analysis_report.pdf"
    HTML(string=html_content, base_url=base_url).write_pdf(
        output_path, stylesheets=[css]
    )
    logger.info(f"PDF saved to {output_path}")



def generate_report() -> None:
    """Generate and save the survey analysis report as a PDF."""
    logger.info("Starting report generation process")

    try:
        data = load_data()
        logger.info("Data loaded successfully")
        report_data = prepare_report_data(data)
        logger.info("Report data prepared")
        html_content = render_html_template(report_data)
        logger.info("HTML content rendered")
        generate_pdf(html_content)
        logger.info("PDF Report generated successfully")
    except Exception as e:
        logger.error(
            f"Error occurred during report generation: {str(e)}", exc_info=True
        )
        raise


if __name__ == "__main__":
    generate_report()
