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


def build_html_table(
    headers: list,
    rows: list,
    table_id: str = "",
    table_classes: str = "",
    caption: str = "",
    title: str = "",
) -> str:
    """Build a generic HTML table from headers and rows."""
    header_html = "".join(f"<th>{h}</th>" for h in headers)
    rows_html = "".join(f"<tr>{r}</tr>" for r in rows)

    caption_html = (
        f'<caption class="table-caption">{caption}</caption>' if caption else ""
    )
    title_html = f'<h4 class="table-title">{title}</h4>' if title else ""
    table_id_attr = f'id="{table_id}"' if table_id else ""
    table_classes_attr = f'class="{table_classes}"' if table_classes else ""

    return f"""
    <div class="table-container">
        {title_html}
        <table {table_id_attr} {table_classes_attr}>
            {caption_html}
            <thead>
                <tr>{header_html}</tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>
    """
