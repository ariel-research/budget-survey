from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse

from flask import Blueprint, current_app, jsonify, redirect, request, url_for

from application.translations import (
    TRANSLATIONS,
    get_current_language,
    get_translation,
    set_language,
)
from database.db import get_db

util_routes = Blueprint("utils", __name__)


@util_routes.before_request
def before_request():
    """Handle language parameter for all routes."""
    lang = request.args.get("lang")
    if lang in ["en", "he"]:
        set_language(lang)


@util_routes.route("/health")
def health_check():
    """
    Health check endpoint for Docker and monitoring.
    Returns 200 OK if the application and database are healthy.
    """
    try:
        # Test database connection
        db = get_db()
        if db and db.is_connected():
            return (
                jsonify(
                    {
                        "status": "healthy",
                        "database": "connected",
                        "application": "running",
                    }
                ),
                200,
            )
        else:
            return (
                jsonify(
                    {
                        "status": "unhealthy",
                        "database": "disconnected",
                        "application": "running",
                    }
                ),
                503,
            )
    except Exception as e:
        return (
            jsonify(
                {
                    "status": "unhealthy",
                    "database": "error",
                    "application": "running",
                    "error": str(e),
                }
            ),
            503,
        )


@util_routes.route("/get_messages")
def get_messages():
    """
    Serve all translated messages based on current language.
    Returns all messages from the 'messages' section in the current language.
    """
    current_lang = get_current_language()
    messages = {
        key: get_translation(key, "messages", current_lang)
        for key in TRANSLATIONS["messages"].keys()
    }
    return jsonify(messages)


@util_routes.route("/change_language")
def change_language():
    """Handle language change requests."""
    new_lang = request.args.get("lang", "he")
    set_language(new_lang)

    referrer = request.referrer
    if not referrer:
        return redirect(
            url_for(
                "survey.index",
                userID=request.args.get("userID"),
                surveyID=request.args.get("surveyID"),
                lang=new_lang,
            )
        )

    # Preserve current URL with updated language
    parsed_url = urlparse(referrer)
    query_params = parse_qs(parsed_url.query)
    query_params["lang"] = [new_lang]

    new_query = urlencode(query_params, doseq=True)
    return redirect(
        f"{parsed_url.scheme}://{parsed_url.netloc}" f"{parsed_url.path}?{new_query}"
    )


def redirect_to_panel4all(
    user_id: str, survey_id: str, status: str = "finish", q: str = None
) -> str:
    """Generate Panel4All redirect URL with specified status."""
    params = {"surveyID": survey_id, "userID": user_id, "status": status}
    if q is not None:
        params["q"] = q
    return f"{current_app.config['PANEL4ALL']['BASE_URL']}?{urlencode(params)}"


def redirect_to_panel4all_with_pts(
    user_id: str, survey_id: str, status: str, pts: Optional[str] = None
) -> str:
    """Generate Panel4All redirect URL with PTS parameter."""
    params = {"surveyID": survey_id, "userID": user_id, "status": status}
    if pts is not None:
        params["PTS"] = pts
    return f"{current_app.config['PANEL4ALL']['BASE_URL']}?{urlencode(params)}"
