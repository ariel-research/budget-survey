import logging
from urllib.parse import urlencode

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

from analysis.utils.report_utils import ensure_fresh_report
from application.translations import (
    TRANSLATIONS,
    get_current_language,
    get_translation,
    set_language,
)
from database.queries import (
    check_user_participation,
    create_comparison_pair,
    create_survey_response,
    create_user,
    get_subjects,
    get_survey_name,
    mark_survey_as_completed,
    user_exists,
)
from utils.generate_examples import generate_user_example
from utils.survey_utils import generate_awareness_check, is_valid_vector

main = Blueprint("main", __name__)

logger = logging.getLogger(__name__)


@main.context_processor
def inject_template_globals():
    """Make translation functions available to all templates."""
    return {
        "get_translation": get_translation,
        "get_current_language": get_current_language,
    }


@main.before_request
def before_request():
    """Handle language parameter for all routes."""
    handle_language_from_url()


def handle_language_from_url():
    """Set language based on URL parameter if present."""
    lang = request.args.get("lang")
    if lang in ["en", "he"]:
        set_language(lang)


def get_internal_survey_id() -> int:
    """
    Get the internal survey ID from application config.
    This is the ID used for database operations.

    Returns:
        int: The configured survey ID for the application.
    """
    return current_app.config["SURVEY_ID"]


def get_external_survey_id() -> str:
    """
    Get the external survey ID from the URL parameters.
    This is the ID used for Panel4All integration.

    Returns:
        str: The external survey ID from the URL parameters
    """
    return get_required_param("surveyID")


def get_user_id() -> str:
    """
    Get the user ID from the URL parameters.
    This is the ID used for Panel4All integration and for database operations.

    Returns:
        str: The user ID from the URL parameters
    """
    return get_required_param("userID")


def get_required_param(param_name: str) -> str:
    """
    Get a required parameter from the request arguments.

    Args:
        param_name (str): Name of the parameter to retrieve.

    Returns:
        str: The value of the requested parameter.

    Raises:
        400: If the parameter is missing from the request.
    """
    value = request.args.get(param_name)
    if not value:
        logger.warning(f"Required parameter '{param_name}' not found in request")
        error_message = get_translation("missing_parameter", "messages").format(
            param=param_name
        )
        abort(400, description=error_message)
    return value


def redirect_to_panel4all(user_id, survey_id):
    """
    Generate the Panel4All redirect URL with the required parameters.

    Args:
        user_id (str): The user ID from the survey
        survey_id (str): The survey ID

    Returns:
        str: The complete Panel4All URL for redirection
    """
    base_url = "http://www.panel4all.co.il/survey_runtime/external_survey_status.php"
    params = {"surveyID": survey_id, "userID": user_id, "status": "finish"}
    return f"{base_url}?{urlencode(params)}"


# Core page routes
@main.route("/")
def index():
    """Render the index page or redirect to thank you page if survey is already completed."""
    user_id = get_user_id()
    external_survey_id = get_external_survey_id()
    internal_survey_id = get_internal_survey_id()

    # Check if the survey exists
    survey_name = get_survey_name(internal_survey_id)
    if not survey_name:
        error_message = get_translation("survey_not_found", section="messages")
        abort(404, description=error_message)

    # Check if the user has already participated using internal ID
    if check_user_participation(user_id, internal_survey_id):
        logger.info(
            f"User {user_id} has already completed survey {internal_survey_id}. Redirecting to thank you page."
        )
        return redirect(
            url_for(
                "main.thank_you",
                lang=get_current_language(),
                userID=user_id,
                surveyID=external_survey_id,
            )
        )
    logger.info(
        f"Index page accessed by user_id {user_id}, internal_survey_id {internal_survey_id}, external_survey_id {external_survey_id}"
    )
    return render_template(
        "index.html",
        user_id=user_id,
        external_survey_id=external_survey_id,
        survey_name=survey_name,
    )


@main.route("/create_vector", methods=["GET", "POST"])
def create_vector():
    """Handle the creation of a budget vector."""
    user_id = get_user_id()
    external_survey_id = get_external_survey_id()
    internal_survey_id = get_internal_survey_id()
    subjects = get_subjects(internal_survey_id)
    current_lang = get_current_language()

    if not subjects:
        logger.error(f"No subjects found for internal_survey_id {internal_survey_id}")
        error_message = get_translation("survey_no_subjects", "messages")
        abort(404, description=error_message)

    if request.method == "POST":
        user_vector = [int(request.form.get(subject, 0)) for subject in subjects]
        logger.debug(f"User {user_id} submitted vector: {user_vector}")

        if not is_valid_vector(user_vector):
            logger.warning(f"Invalid vector submitted by user {user_id}: {user_vector}")
            return render_template(
                "create_vector.html",
                error=get_translation("invalid_vector", "messages"),
                subjects=subjects,
                user_id=user_id,
                external_survey_id=external_survey_id,
            )

        logger.info(f"Valid vector created by user {user_id}: {user_vector}")
        return redirect(
            url_for(
                "main.survey",
                vector=",".join(map(str, user_vector)),
                userID=user_id,
                surveyID=external_survey_id,
                lang=current_lang,
            )
        )

    logger.debug(
        f"Create vector page accessed by user {user_id}, internal_survey_id {internal_survey_id}, external_survey_id {external_survey_id}"
    )
    return render_template(
        "create_vector.html",
        subjects=subjects,
        user_id=user_id,
        internal_survey_id=internal_survey_id,
        external_survey_id=external_survey_id,
    )


@main.route("/survey", methods=["GET", "POST"])
def survey():
    """Handle the survey process."""
    user_id = get_user_id()
    external_survey_id = get_external_survey_id()
    internal_survey_id = get_internal_survey_id()
    subjects = get_subjects(internal_survey_id)
    current_lang = get_current_language()

    if not subjects:
        logger.error(f"No subjects found for internal_survey_id {internal_survey_id}")
        abort(404, description=get_translation("survey_no_subjects", "messages"))

    if request.method == "GET":
        user_vector = list(map(int, request.args.get("vector", "").split(",")))
        logger.debug(f"Survey accessed by user {user_id} with vector: {user_vector}")
        if len(user_vector) != len(subjects) or sum(user_vector) != 100:
            logger.warning(
                f"Invalid vector in survey GET for user {user_id}: {user_vector}"
            )
            return redirect(
                url_for(
                    "main.create_vector",
                    userID=user_id,
                    surveyID=external_survey_id,
                    lang=current_lang,
                )
            )

        comparison_pairs = list(
            generate_user_example(tuple(user_vector), n=10, vector_size=len(subjects))
        )
        awareness_check = generate_awareness_check(user_vector, len(subjects))

        logger.info(f"Survey generated for user {user_id} with vector: {user_vector}")
        return render_template(
            "survey.html",
            user_vector=user_vector,
            comparison_pairs=comparison_pairs,
            awareness_check=awareness_check,
            subjects=subjects,
            user_id=user_id,
            internal_survey_id=internal_survey_id,
            external_survey_id=external_survey_id,
            zip=zip,
        )

    elif request.method == "POST":
        data = request.form
        user_vector = list(map(int, data.get("user_vector").split(",")))
        user_comment = request.form.get("user_comment", "")
        logger.debug(
            f"Survey submission received from user {user_id}. User vector: {user_vector}, Comment: {user_comment}"
        )

        # Check awareness question
        awareness_answer = int(data.get("awareness_check", 0))
        if awareness_answer != 2:
            logger.warning(f"User {user_id} failed awareness check")
            flash(get_translation("failed_awareness", "messages"), "error")
            return redirect(
                url_for(
                    "main.survey",
                    vector=",".join(map(str, user_vector)),
                    userID=user_id,
                    surveyID=external_survey_id,
                    lang=current_lang,
                )
            )

        try:
            # Check if user already exists
            if not user_exists(user_id):
                create_user(user_id)
                logger.info(f"User created in database with ID: {user_id}")
            else:
                logger.info(f"User with ID {user_id} already exists")

            # Use internal survey ID for database operations
            survey_response_id = create_survey_response(
                user_id, internal_survey_id, user_vector, user_comment
            )
            logger.info(f"Survey response created with ID: {survey_response_id}")

            for i in range(10):
                option_1 = list(map(int, data.get(f"option1_{i}", "").split(",")))
                option_2 = list(map(int, data.get(f"option2_{i}", "").split(",")))
                user_choice = int(data.get(f"choice_{i}"))
                comparison_pair_id = create_comparison_pair(
                    survey_response_id, i + 1, option_1, option_2, user_choice
                )
                logger.debug(
                    f"Comparison pair created: ID {comparison_pair_id}, Pair {i+1}, Choice: {user_choice}"
                )

            mark_survey_as_completed(survey_response_id)
            logger.info(
                f"Survey marked as completed for user {user_id}: {survey_response_id}"
            )
        except Exception as e:
            logger.error(
                f"Error processing survey submission for user {user_id}: {str(e)}",
                exc_info=True,
            )
            return render_template(
                "error.html",
                message=get_translation("survey_processing_error", "messages"),
            )

        # Use external survey ID for Panel4All redirect
        panel4all_url = redirect_to_panel4all(user_id, external_survey_id)
        logger.info(
            f"Redirecting user {user_id} to Panel4All with external_survey_id {external_survey_id}"
        )
        return redirect(panel4all_url)


@main.route("/thank_you")
def thank_you():
    """Render the thank you page."""
    logger.info("Thank you page accessed")
    return render_template("thank_you.html")


@main.route("/report")
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


@main.route("/dev/report")
def dev_report():
    """
    Development endpoint for generating and displaying a fresh analysis report.
    Always generates a new PDF regardless of database state.
    """
    try:
        # Ensure CSV files exist using existing utility
        from analysis.utils.report_utils import ensure_fresh_csvs

        ensure_fresh_csvs()

        # Define development report path
        dev_report_path = "data/survey_analysis_report_dev.pdf"

        # Generate a new report with the development path
        from analysis.survey_report_generator import generate_report

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


# Utility routes
@main.route("/get_messages")
def get_messages():
    """
    Serve all translated messages based on current language.
    Returns all messages from the 'messages' section in the current language.
    """
    current_lang = get_current_language()
    return jsonify(
        {
            key: get_translation(key, "messages", current_lang)
            for key in TRANSLATIONS["messages"].keys()
        }
    )


@main.errorhandler(400)
def bad_request(e):
    """
    Handle 400 Bad Request errors.

    Args:
        e: The error object containing the description.

    Returns:
        tuple: Template and status code.
    """
    return (
        render_template(
            "error.html",
            message=e.description,
        ),
        400,
    )


@main.errorhandler(404)
def not_found(e):
    """
    Handle 404 Not Found errors.

    Args:
        e: The error object containing the description.

    Returns:
        tuple: Template and status code.
    """
    return (
        render_template(
            "error.html",
            message=e.description,
        ),
        404,
    )


# Language switching
@main.route("/set_language")
def change_language():
    """Handle language change requests."""
    # Get the new language
    new_lang = request.args.get("lang", "he")
    set_language(new_lang)

    # Get the referrer URL
    referrer = request.referrer

    if referrer:
        # Parse the referrer URL to preserve existing parameters
        from urllib.parse import parse_qs, urlencode, urlparse

        # Parse the URL
        parsed_url = urlparse(referrer)
        # Convert query string to dictionary
        query_params = parse_qs(parsed_url.query)

        # Update language parameter
        query_params["lang"] = [new_lang]

        # Ensure userID and surveyID are preserved
        if "userID" not in query_params and request.args.get("userID"):
            query_params["userID"] = [request.args.get("userID")]
        if "surveyID" not in query_params and request.args.get("surveyID"):
            query_params["surveyID"] = [request.args.get("surveyID")]

        # Reconstruct the URL with updated parameters
        new_query = urlencode(query_params, doseq=True)
        new_url = (
            f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}?{new_query}"
        )

        return redirect(new_url)

    # If no referrer, redirect to index with necessary parameters
    return redirect(
        url_for(
            "main.index",
            lang=new_lang,
            userID=request.args.get("userID"),
            surveyID=request.args.get("surveyID"),
        )
    )
