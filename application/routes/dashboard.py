import logging
from datetime import datetime
from json import JSONDecodeError, loads

from flask import Blueprint, render_template

from application.services.dashboard_service import get_dashboard_metrics
from application.translations import get_translation

logger = logging.getLogger(__name__)
dashboard_routes = Blueprint("dashboard", __name__)


def _safe_json(value, default):
    """Safely parse a JSON-like value (str/dict/list) with fallback."""
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return loads(value)
        except JSONDecodeError:
            return default
    return default


def parse_survey_data(survey):
    """
    Parse raw survey row into a resilient dashboard console shape.

    Rules:
    - status ignores `active`; survey is active only when participant_count > 0
    - strategy from pair_generation_config.strategy, default Unknown
    - dimension from subjects length
    - context from English story title with Hebrew fallback
    - date in `%b %d` format
    """
    pair_config = _safe_json(survey.get("pair_generation_config"), {})
    title = _safe_json(survey.get("title"), {})
    subjects = _safe_json(survey.get("subjects"), [])

    strategy_raw = (
        pair_config.get("strategy") if isinstance(pair_config, dict) else None
    )
    if isinstance(strategy_raw, str) and strategy_raw.strip():
        strategy_name = strategy_raw.strip().replace("_", " ").title()
    else:
        strategy_name = "Unknown"

    if not isinstance(subjects, list):
        subjects = []

    if isinstance(title, dict):
        context = title.get("en") or title.get("he") or ""
    else:
        context = str(title or "")

    participant_count_raw = survey.get("participant_count", 0)
    try:
        participant_count = int(participant_count_raw or 0)
    except (TypeError, ValueError):
        participant_count = 0

    created_at = survey.get("created_at")
    created_dt = None
    date_label = ""
    sort_date = ""
    if isinstance(created_at, datetime):
        created_dt = created_at
    elif isinstance(created_at, str):
        try:
            created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except ValueError:
            # Keep empty when date is malformed; do not break rendering.
            created_dt = None

    if created_dt:
        date_label = created_dt.strftime("%b %d")
        sort_date = created_dt.strftime("%Y-%m-%d")

    is_active_data = participant_count > 0
    dimension_count = len(subjects)
    dimension_label = f"{dimension_count}D" if dimension_count > 0 else "N/A"

    return {
        "id": survey.get("id"),
        "ui_date": date_label,
        "ui_status": "active" if is_active_data else "inactive",
        "is_active_data": is_active_data,
        "ui_strategy": strategy_name,
        "ui_context": context,
        "ui_dimension": dimension_label,
        "ui_volume": participant_count,
        "sort_date": sort_date,
        "sort_identity": strategy_name,
        "sort_dim": dimension_count,
    }


@dashboard_routes.route("/")
def view_dashboard():
    """Display the dashboard overview."""
    try:
        # Get dashboard data and metrics
        dashboard_data = get_dashboard_metrics()
        raw_surveys = dashboard_data.get("surveys", [])
        parsed_surveys = [parse_survey_data(survey) for survey in raw_surveys]

        inactive_surveys = sum(1 for survey in raw_surveys if not survey.get("active"))
        logger.info(
            "Dashboard survey load complete: total=%s, inactive=%s",
            len(raw_surveys),
            inactive_surveys,
        )

        # Get translations for dashboard content
        translations = {
            "title": get_translation("title", "dashboard"),
            "subtitle": get_translation("subtitle", "dashboard"),
            "total_surveys": get_translation("total_surveys", "dashboard"),
            "total_surveys_description": get_translation(
                "total_surveys_description", "dashboard"
            ),
            "total_participants": get_translation(
                "total_participants",
                "dashboard",
            ),
            "excluded_users": get_translation("excluded_users", "dashboard"),
            "all_participants": get_translation(
                "all_participants",
                "dashboard",
            ),
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
            "blocked_users": get_translation("blocked_users", "dashboard"),
            "search_placeholder": get_translation("search_placeholder", "dashboard"),
            "active_data_toggle": get_translation("active_data_toggle", "dashboard"),
            "all_surveys_toggle": get_translation("all_surveys_toggle", "dashboard"),
            "copied_to_clipboard": get_translation("copied_to_clipboard", "dashboard"),
        }

        return render_template(
            "dashboard/surveys_overview.html",
            surveys=raw_surveys,
            surveys_console=parsed_surveys,
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
