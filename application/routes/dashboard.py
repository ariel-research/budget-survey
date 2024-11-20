import logging
from datetime import datetime

from flask import Blueprint, abort, render_template

from analysis.utils.analysis_utils import load_data
from analysis.utils.visualization_utils import (
    visualize_overall_majority_choice_distribution,
    visualize_per_survey_answer_percentages,
    visualize_total_answer_percentage_distribution,
    visualize_user_survey_majority_choices,
)
from application.translations import get_translation

logger = logging.getLogger(__name__)
dashboard_routes = Blueprint("dashboard", __name__)


@dashboard_routes.route("/dashboard/")
@dashboard_routes.route("/dashboard")
def dashboard():
    """Render the analytics dashboard with visualizations and metrics."""
    try:
        data = load_data()

        # Generate visualization charts
        charts = {
            "survey_percentages": visualize_per_survey_answer_percentages(
                data["summary"]
            ),
            "majority_choices": visualize_user_survey_majority_choices(
                data["optimization"]
            ),
            "overall_distribution": visualize_overall_majority_choice_distribution(
                data["summary"]
            ),
            "answer_distribution": visualize_total_answer_percentage_distribution(
                data["summary"]
            ),
        }

        # Calculate metrics
        total_row = data["summary"].loc[data["summary"]["survey_id"] == "Total"].iloc[0]
        metrics = {
            "total_surveys": len(data["summary"]) - 1,  # Exclude "Total" row
            "total_participants": total_row["total_survey_responses"],
            "completion_rate": round(
                (data["optimization"]["result"].count() / len(data["optimization"]))
                * 100,
                1,
            ),
            "last_update_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }

        # Pass translations using 'dashboard' section
        translations = {
            "title": get_translation("title", "dashboard"),
            "last_updated": get_translation("last_updated", "dashboard"),
            "refresh": get_translation("refresh", "dashboard"),
            "total_surveys": get_translation("total_surveys", "dashboard"),
            "total_participants": get_translation("total_participants", "dashboard"),
            "completion_rate": get_translation("completion_rate", "dashboard"),
            "survey_percentages": get_translation("survey_percentages", "dashboard"),
            "majority_choices": get_translation("majority_choices", "dashboard"),
            "overall_distribution": get_translation(
                "overall_distribution", "dashboard"
            ),
            "answer_distribution": get_translation("answer_distribution", "dashboard"),
            "expand": get_translation("expand", "dashboard"),
            "download": get_translation("download", "dashboard"),
        }

        return render_template(
            "dashboard.html", charts=charts, translations=translations, **metrics
        )

    except Exception as e:
        logger.error(f"Error rendering dashboard: {str(e)}", exc_info=True)
        abort(500, description=get_translation("messages.dashboard_error"))


# @dashboard_routes.route("/api/dashboard/refresh")
# def refresh_data():
#     """API endpoint to refresh dashboard data."""
#     try:
#         data = load_data()  # Regenerate CSVs if needed
#         return jsonify(
#             {
#                 "status": "success",
#                 "message": get_translation("dashboard_refreshed", "messages"),
#             }
#         )
#     except Exception as e:
#         logger.error(f"Error refreshing dashboard data: {str(e)}")
#         return (
#             jsonify(
#                 {
#                     "status": "error",
#                     "message": get_translation("dashboard_refresh_error", "messages"),
#                 }
#             ),
#             500,
#         )
