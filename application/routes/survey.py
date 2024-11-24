import logging
from typing import Tuple
from urllib.parse import urlencode

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from application.schemas.validators import SurveySubmission
from application.services.survey_service import SurveyService, SurveySessionData
from application.translations import get_current_language, get_translation, set_language
from utils.survey_utils import is_valid_vector

logger = logging.getLogger(__name__)
survey_routes = Blueprint("survey", __name__)


@survey_routes.before_request
def before_request():
    """Handle language parameter for all routes."""
    lang = request.args.get("lang")
    if lang in ["en", "he"]:
        set_language(lang)


def get_required_params() -> Tuple[str, str, int]:
    """
    Get and validate required URL parameters.

    Returns:
        Tuple[str, str, int]: user_id, external_survey_id, internal_survey_id

    Raises:
        abort(400): If required parameters are missing
    """
    try:
        user_id = request.args.get("userID")
        external_survey_id = request.args.get("surveyID")

        if not user_id or not external_survey_id:
            missing_param = "userID" if not user_id else "surveyID"
            raise ValueError(f"Missing {missing_param}")

        # Get internal_survey_id from session if available, otherwise from config
        internal_survey_id = session.get(
            "internal_survey_id", current_app.config["SURVEY_ID"]
        )
        return user_id, external_survey_id, internal_survey_id

    except ValueError as e:
        logger.warning(f"Missing required parameter: {str(e)}")
        abort(
            400,
            description=get_translation("missing_parameter", "messages", param=str(e)),
        )


@survey_routes.route("/")
def index():
    """Landing page route handler."""
    user_id, external_survey_id, internal_survey_id = get_required_params()

    # Handle custom internal survey ID
    custom_internal_id = request.args.get("internalID")
    if custom_internal_id:
        try:
            internal_survey_id = int(custom_internal_id)
            # Store in session for subsequent requests
            session["internal_survey_id"] = internal_survey_id
            logger.info(f"Custom internal survey ID set: {custom_internal_id}")
        except ValueError:
            logger.warning(f"Invalid internal survey ID provided: {custom_internal_id}")
            abort(400, description=get_translation("invalid_parameter", "messages"))

    # Verify survey exists
    survey_exists, error, survey_data = SurveyService.check_survey_exists(
        internal_survey_id
    )
    if not survey_exists:
        error_key, error_params = error
        abort(404, description=get_translation(error_key, "messages", **error_params))

    # Check user eligibility
    is_eligible, redirect_url = SurveyService.check_user_eligibility(
        user_id, internal_survey_id
    )
    if not is_eligible:
        return redirect(
            url_for(
                f"survey.{redirect_url}",
                userID=user_id,
                surveyID=external_survey_id,
            )
        )

    return render_template(
        "index.html",
        user_id=user_id,
        external_survey_id=external_survey_id,
        survey_name=survey_data["name"],
    )


@survey_routes.route("/create_vector", methods=["GET", "POST"])
def create_vector():
    """Budget vector creation route handler."""
    user_id, external_survey_id, internal_survey_id = get_required_params()
    current_lang = get_current_language()

    # Verify survey exists and get data
    survey_exists, error, survey_data = SurveyService.check_survey_exists(
        internal_survey_id
    )
    if not survey_exists:
        error_key, error_params = error
        abort(404, description=get_translation(error_key, "messages", **error_params))

    if request.method == "POST":
        try:
            user_vector = [
                int(request.form.get(subject, 0)) for subject in survey_data["subjects"]
            ]
            logger.debug(f"User {user_id} submitted vector: {user_vector}")

            if not is_valid_vector(user_vector):
                return render_template(
                    "create_vector.html",
                    error=get_translation("invalid_vector", "messages"),
                    subjects=survey_data["subjects"],
                    user_id=user_id,
                    external_survey_id=external_survey_id,
                )

            logger.info(f"Valid vector created by user {user_id}: {user_vector}")
            return redirect(
                url_for(
                    "survey.survey",
                    vector=",".join(map(str, user_vector)),
                    userID=user_id,
                    surveyID=external_survey_id,
                    lang=current_lang,
                )
            )

        except ValueError as e:
            logger.error(f"Invalid vector data: {str(e)}")
            return render_template(
                "create_vector.html",
                error=get_translation("invalid_vector", "messages"),
                subjects=survey_data["subjects"],
                user_id=user_id,
                external_survey_id=external_survey_id,
            )

    logger.debug(
        f"Create vector page accessed by user {user_id}, internal_survey_id {internal_survey_id}, external_survey_id {external_survey_id}"
    )
    return render_template(
        "create_vector.html",
        subjects=survey_data["subjects"],
        user_id=user_id,
        external_survey_id=external_survey_id,
        internal_survey_id=internal_survey_id,
    )


@survey_routes.route("/survey", methods=["GET", "POST"])
def survey():
    """Main survey route handler."""
    user_id, external_survey_id, internal_survey_id = get_required_params()

    survey_exists, error, survey_data = SurveyService.check_survey_exists(
        internal_survey_id
    )
    if not survey_exists:
        error_key, error_params = error
        abort(404, description=get_translation(error_key, "messages", **error_params))

    if request.method == "GET":
        return handle_survey_get(user_id, external_survey_id, survey_data["subjects"])
    elif request.method == "POST":
        return handle_survey_post(user_id, external_survey_id, internal_survey_id)
    else:
        abort(405)  # Method Not Allowed


def handle_survey_get(
    user_id: str, external_survey_id: str, subjects: list[str]
) -> str:
    """Handle GET request for survey page."""
    try:
        user_vector = list(map(int, request.args.get("vector", "").split(",")))
        current_lang = get_current_language()

        if not SurveyService.validate_vector(user_vector, len(subjects)):
            return redirect(
                url_for(
                    "survey.create_vector",
                    userID=user_id,
                    surveyID=external_survey_id,
                    lang=current_lang,
                )
            )

        session_data = SurveySessionData(
            user_id=user_id,
            survey_id=external_survey_id,
            user_vector=user_vector,
            subjects=subjects,
        )

        return render_template("survey.html", **session_data.to_template_data())

    except Exception as e:
        logger.error(f"Error in survey GET: {str(e)}", exc_info=True)
        abort(400, description=get_translation("survey_processing_error", "messages"))


def handle_survey_post(
    user_id: str, external_survey_id: str, internal_survey_id: int
) -> str:
    """Handle POST request for survey submission."""
    try:
        # Create and validate submission
        submission = SurveySubmission.from_form_data(
            request.form, user_id, internal_survey_id
        )

        is_valid, error_message = submission.validate()
        if not is_valid:
            flash(error_message, "error")
            return redirect(
                url_for(
                    "survey.survey",
                    vector=",".join(map(str, submission.user_vector)),
                    userID=user_id,
                    surveyID=external_survey_id,
                )
            )

        # Process submission
        SurveyService.process_survey_submission(submission)

        # Redirect to Panel4All
        panel4all_url = redirect_to_panel4all(user_id, external_survey_id)
        logger.info(
            f"Redirecting user {user_id} to Panel4All with survey {external_survey_id}"
        )
        return redirect(panel4all_url)

    except Exception as e:
        logger.error(f"Error in survey POST: {str(e)}", exc_info=True)
        return render_template(
            "error.html", message=get_translation("survey_processing_error", "messages")
        )


@survey_routes.route("/thank_you")
def thank_you():
    """Thank you page route handler."""
    logger.info("Thank you page accessed")
    return render_template("thank_you.html")


def redirect_to_panel4all(user_id: str, survey_id: str) -> str:
    """Generate Panel4All redirect URL."""
    params = {
        "surveyID": survey_id,
        "userID": user_id,
        "status": current_app.config["PANEL4ALL"]["STATUS"]["COMPLETE"],
    }
    return f"{current_app.config['PANEL4ALL']['BASE_URL']}?{urlencode(params)}"
