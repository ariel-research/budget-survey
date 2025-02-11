import logging
from functools import wraps

from flask import current_app, redirect, request, url_for

from application.services.survey_service import SurveyService

logger = logging.getLogger(__name__)


def check_survey_eligibility(f):
    """
    Decorator to check if user is eligible to take the survey.
    Checks if user has already completed the survey and redirects to
    thank you page if they have.
    """

    @wraps(f)  # Preserves the original function's metadata
    def decorated_function(*args, **kwargs):
        try:
            # Get required parameters
            user_id = request.args.get("userID")
            external_survey_id = request.args.get("surveyID")

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
                return redirect(
                    url_for(
                        f"survey.{redirect_url}",
                        userID=user_id,
                        surveyID=external_survey_id,
                        internalID=internal_survey_id,
                    )
                )

            # Call the decorated function with its original arguments
            return f(*args, **kwargs)

        except Exception as e:
            logger.error(f"Error in survey eligibility check: {str(e)}")
            return redirect(url_for("survey.index"))

    return decorated_function
