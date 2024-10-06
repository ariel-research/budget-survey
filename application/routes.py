import logging

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from application.messages import ERROR_MESSAGES
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


def get_survey_id():
    """Get the current survey ID"""
    return current_app.config["SURVEY_ID"]


def get_required_param(param_name: str) -> str:
    """Get a required parameter from the request arguments."""
    value = request.args.get(param_name)
    if not value:
        logger.warning(f"Required parameter '{param_name}' not found in request")
        abort(400, description=f"Missing required parameter: {param_name}")
    return value


@main.route("/")
def index():
    """Render the index page or redirect to thank you page if survey is already completed."""
    user_id = get_required_param("userid")

    # Convert to integer for database queries
    user_id_int = int(user_id)

    # Check if the survey exists
    survey_id = get_survey_id()
    survey_name = get_survey_name(survey_id)
    if not survey_name:
        logger.error(f"No survey found for survey_id {survey_id}")
        abort(404, description="Survey not found")

    # Check if the user has already participated
    if check_user_participation(user_id_int, survey_id):
        logger.info(
            f"User {user_id} has already completed survey {survey_id}. Redirecting to thank you page."
        )
        return redirect(url_for("main.thank_you"))

    logger.info(f"Index page accessed by user_id {user_id} for survey_id {survey_id}")
    return render_template(
        "index.html", user_id=user_id, survey_id=survey_id, survey_name=survey_name
    )


@main.route("/create_vector", methods=["GET", "POST"])
def create_vector():
    """Handle the creation of a budget vector."""
    user_id = get_required_param("userid")
    survey_id = get_survey_id()
    subjects = get_subjects(survey_id)

    if not subjects:
        logger.error(f"No subjects found for survey_id {survey_id}")
        abort(404, description="Survey not found or has no subjects")

    if request.method == "POST":
        user_vector = [int(request.form.get(subject, 0)) for subject in subjects]
        logger.debug(f"User {user_id} submitted vector: {user_vector}")

        if not is_valid_vector(user_vector):
            logger.warning(f"Invalid vector submitted by user {user_id}: {user_vector}")
            return render_template(
                "create_vector.html",
                error=ERROR_MESSAGES["invalid_vector"],
                subjects=subjects,
                user_id=user_id,
                survey_id=survey_id,
            )

        logger.info(f"Valid vector created by user {user_id}: {user_vector}")
        return redirect(
            url_for(
                "main.survey", vector=",".join(map(str, user_vector)), userid=user_id
            )
        )

    logger.debug(f"Create vector page accessed by user {user_id}")
    return render_template(
        "create_vector.html", subjects=subjects, user_id=user_id, survey_id=survey_id
    )


@main.route("/survey", methods=["GET", "POST"])
def survey():
    """Handle the survey process."""
    user_id = get_required_param("userid")
    survey_id = get_survey_id()
    subjects = get_subjects(survey_id)

    if not subjects:
        logger.error(f"No subjects found for survey_id {survey_id}")
        abort(404, description="Survey not found or has no subjects")

    if request.method == "GET":
        user_vector = list(map(int, request.args.get("vector", "").split(",")))
        logger.debug(f"Survey accessed by user {user_id} with vector: {user_vector}")
        if len(user_vector) != len(subjects) or sum(user_vector) != 100:
            logger.warning(
                f"Invalid vector in survey GET for user {user_id}: {user_vector}"
            )
            return redirect(url_for("main.create_vector", userid=user_id))

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
            survey_id=survey_id,
            zip=zip,
        )

    elif request.method == "POST":
        data = request.form
        user_vector = list(map(int, data.get("user_vector").split(",")))
        logger.debug(
            f"Survey submission received from user {user_id}. User vector: {user_vector}"
        )

        # Check awareness question
        awareness_answer = int(data.get("awareness_check", 0))
        if awareness_answer != 2:
            logger.warning(f"User {user_id} failed awareness check")
            flash(ERROR_MESSAGES["failed_awareness"], "error")
            return redirect(
                url_for(
                    "main.survey",
                    vector=",".join(map(str, user_vector)),
                    userid=user_id,
                )
            )

        try:
            # Check if user already exists
            if not user_exists(int(user_id)):
                create_user(int(user_id))
                logger.info(f"User created in database with ID: {user_id}")
            else:
                logger.info(f"User with ID {user_id} already exists")

            survey_response_id = create_survey_response(user_id, survey_id, user_vector)
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
                "error.html", message=ERROR_MESSAGES["survey_processing_error"]
            )

        return redirect(url_for("main.thank_you"))


@main.route("/thank_you")
def thank_you():
    logger.info("Thank you page accessed")
    return render_template("thank_you.html")


@main.errorhandler(400)
def bad_request(e):
    return render_template("error.html", message=e.description), 400


@main.errorhandler(404)
def not_found(e):
    return render_template("error.html", message=e.description), 404


@main.route("/get_messages")
def get_messages():
    return jsonify(ERROR_MESSAGES)
