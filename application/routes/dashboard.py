import logging
from datetime import datetime

from flask import Blueprint, render_template

from application.services.dashboard_service import get_dashboard_metrics
from application.translations import get_translation

logger = logging.getLogger(__name__)
dashboard_routes = Blueprint("dashboard", __name__)


@dashboard_routes.route("/")
def view_dashboard():
    """Display the dashboard overview."""
    try:
        # Get dashboard data and metrics
        dashboard_data = get_dashboard_metrics()

        # Get translations for dashboard content
        translations = {
            "title": get_translation("title", "dashboard"),
            "subtitle": get_translation("subtitle", "dashboard"),
            "total_surveys": get_translation("total_surveys", "dashboard"),
            "total_surveys_description": get_translation(
                "total_surveys_description", "dashboard"
            ),
            "total_participants": get_translation("total_participants", "dashboard"),
            "excluded_users": get_translation("excluded_users", "dashboard"),
            "all_participants": get_translation("all_participants", "dashboard"),
            "total_participants_description": get_translation(
                "total_participants_description", "dashboard"
            ),
            "excluded_users_description": get_translation(
                "excluded_users_description", "dashboard"
            ),
            "all_participants_description": get_translation(
                "all_participants_description", "dashboard"
            ),
            "last_updated": get_translation("last_updated", "dashboard"),
            "view_responses": get_translation("view_responses", "dashboard"),
            "take_survey": get_translation("take_survey", "dashboard"),
        }

        return render_template(
            "dashboard/surveys_overview.html",
            surveys=dashboard_data["surveys"],
            total_surveys=dashboard_data["total_surveys"],
            total_participants=dashboard_data["total_participants"],
            unaware_users_count=dashboard_data["unaware_users_count"],
            users_with_surveys=dashboard_data["users_with_surveys"],
            translations=translations,
            last_update_time=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )

    except Exception as e:
        logger.error(f"Error displaying dashboard: {str(e)}")
        return render_template(
            "error.html",
            message=get_translation("dashboard_error", "messages"),
        )
