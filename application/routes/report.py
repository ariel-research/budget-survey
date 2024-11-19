import logging

from flask import Blueprint, render_template, send_file

from analysis.survey_report_generator import generate_report
from analysis.utils.report_utils import ensure_fresh_csvs, ensure_fresh_report
from application.translations import get_translation

logger = logging.getLogger(__name__)
report_routes = Blueprint("report", __name__)


@report_routes.route("/report")
def view_report():
    """Display the analysis report."""
    try:
        # Ensure CSV files and PDF report are up to date with database
        ensure_fresh_report()

        return send_file(
            "data/survey_analysis_report.pdf",
            mimetype="application/pdf",  # Explicitly tell browser this is a PDF file
            as_attachment=False,  # Display in browser instead of downloading
            download_name="survey_analysis_report.pdf",  # Name used if user chooses to download
        )

    except Exception as e:
        logger.error(f"Error serving report: {e}")
        return render_template(
            "error.html",
            message=get_translation("report_error", "messages"),
        )


@report_routes.route("/dev/report")
def dev_report():
    """
    Development endpoint for generating and displaying a fresh analysis report.
    Always generates a new PDF regardless of database state.
    """
    try:
        # Ensure CSV files exist using existing utility
        ensure_fresh_csvs()

        # Define development report path
        dev_report_path = "data/survey_analysis_report_dev.pdf"

        # Generate a new report with the development path
        generate_report(dev_report_path)

        return send_file(
            dev_report_path,
            mimetype="application/pdf",
            as_attachment=False,
            download_name="survey_analysis_report_dev.pdf",
        )

    except Exception as e:
        logger.error(f"Error generating development report: {e}")
        return render_template(
            "error.html",
            message=get_translation("report_error", "messages"),
        )
