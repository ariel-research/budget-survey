"""Dashboard routes and functionality for the survey analysis application."""

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

        return render_template("dashboard.html", charts=charts, **metrics)

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
#                 "message": get_translation("messages.dashboard_refreshed"),
#             }
#         )
#     except Exception as e:
#         logger.error(f"Error refreshing dashboard data: {str(e)}")
#         return (
#             jsonify(
#                 {
#                     "status": "error",
#                     "message": get_translation("messages.dashboard_refresh_error"),
#                 }
#             ),
#             500,
#         )


def get_dashboard_data():
    """Helper function to get dashboard data from CSVs."""
    try:
        return load_data()
    except Exception as e:
        logger.error(f"Error loading dashboard data: {str(e)}")
        raise
