import logging
from functools import wraps

from flask import current_app, redirect, request, url_for

from application.routes.utils import redirect_to_panel4all
from application.services.survey_service import SurveyService

logger = logging.getLogger(__name__)


def check_survey_eligibility(f):
    """
    Decorator to check if user is eligible to take the survey.
    Checks if user has already completed the survey or is blacklisted,
    and redirects appropriately.
    """

    @wraps(f)  # Preserves the original function's metadata
    def decorated_function(*args, **kwargs):
        try:
            # Get required parameters
            user_id = request.args.get("userID")
            external_survey_id = request.args.get("surveyID")

            if not user_id or not external_survey_id:
                # If required parameters are missing, pass control to the route function
                # which will handle proper error reporting
                return f(*args, **kwargs)

            # Get internal_survey_id from query parameter or default config
            internal_survey_id = current_app.config["SURVEY_ID"]
            custom_internal_id = request.args.get("internalID")
            if custom_internal_id:
                try:
                    internal_survey_id = int(custom_internal_id)
                except ValueError:
                    logger.warning(
                        f"Invalid internal survey ID provided: {custom_internal_id}"
                    )
                    return redirect(url_for("survey.index"))

            # Check eligibility
            is_eligible, redirect_url = SurveyService.check_user_eligibility(
                user_id, internal_survey_id
            )

            if not is_eligible:
                # Check for demo parameter
                is_demo_args = request.args.get("demo", "").lower() == "true"
                is_demo_form = request.form.get("demo", "").lower() == "true"
                is_demo = is_demo_args or is_demo_form

                # If user is blacklisted and NOT in demo mode, redirect directly to Panel4All
                if redirect_url == "blacklisted" and not is_demo:
                    panel4all_status = current_app.config["PANEL4ALL"]["STATUS"][
                        "ATTENTION_FAILED"
                    ]
                    external_q_argument = request.args.get("q")
                    logger.info(
                        f"Redirecting blacklisted user {user_id} directly to Panel4All"
                    )
                    return redirect(
                        redirect_to_panel4all(
                            user_id,
                            external_survey_id,
                            status=panel4all_status,
                            q=external_q_argument,
                        )
                    )

                # Add lang parameter to the redirect if present in the original request
                lang = request.args.get("lang")
                redirect_kwargs = {
                    "userID": user_id,
                    "surveyID": external_survey_id,
                }

                # Only include these params if they exist and are needed
                if redirect_url != "blacklisted":
                    redirect_kwargs["internalID"] = internal_survey_id
                if lang:
                    redirect_kwargs["lang"] = lang
                if is_demo:
                    redirect_kwargs["demo"] = "true"

                return redirect(url_for(f"survey.{redirect_url}", **redirect_kwargs))

            # Call the decorated function with its original arguments
            return f(*args, **kwargs)

        except Exception as e:
            logger.error(f"Error in survey eligibility check: {str(e)}")
            return redirect(url_for("survey.index"))

    return decorated_function
