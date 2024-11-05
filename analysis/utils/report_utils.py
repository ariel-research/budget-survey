import logging
import os

from database.queries import get_latest_survey_timestamp

logger = logging.getLogger(__name__)

CSV_PATHS = [
    "data/all_completed_survey_responses.csv",
    "data/survey_optimization_stats.csv",
    "data/summarize_stats_by_survey.csv",
]
REPORT_PATH = "data/survey_analysis_report.pdf"


def ensure_fresh_csvs() -> bool:
    """
    Ensure CSV files are up to date with the database.
    Returns True if CSVs were regenerated.
    """
    latest_survey_time = get_latest_survey_timestamp()

    # Check if CSVs need updating
    if not all(os.path.exists(p) for p in CSV_PATHS):
        csv_update_needed = True
    else:
        csv_times = [os.path.getmtime(p) for p in CSV_PATHS]
        csv_update_needed = any(csv_time < latest_survey_time for csv_time in csv_times)

    if csv_update_needed:
        try:
            from analysis.survey_analysis import main as analysis_main

            analysis_main()
            logger.info("CSV files regenerated successfully")
            return True
        except Exception as e:
            logger.error(f"Error regenerating CSV files: {e}")
            raise

    return False


def ensure_fresh_report() -> None:
    """Ensure analysis report is up to date."""
    try:
        csvs_regenerated = ensure_fresh_csvs()

        # Check if PDF needs updating
        if csvs_regenerated or not os.path.exists(REPORT_PATH):
            from analysis.survey_report_generator import generate_report

            generate_report()
            logger.info("Report regenerated successfully")
    except Exception as e:
        logger.error(f"Error ensuring fresh report: {e}")
        raise
