import logging
from typing import List
from flask import Blueprint, render_template, request, redirect, url_for, abort, flash
from database.queries import create_user, create_survey_response, create_comparison_pair, mark_survey_as_completed, user_exists, get_subjects
from utils.generate_examples import generate_user_example
from utils.survey_utils import is_valid_vector, generate_awareness_check
from application.messages import ERROR_MESSAGES

main = Blueprint('main', __name__)

logger = logging.getLogger(__name__)

def get_required_param(param_name: str) -> str:
    """Get a required parameter from the request arguments."""
    value = request.args.get(param_name)
    if not value:
        logger.warning(f"Required parameter '{param_name}' not found in request")
        abort(400, description=f"Missing required parameter: {param_name}")
    return value

@main.route('/')
def index():
    """Render the index page."""
    user_id = get_required_param('userid')
    survey_id = get_required_param('surveyid')
    logger.info(f"Index page accessed by user_id {user_id} for survey_id {survey_id}")
    return render_template('index.html', user_id=user_id, survey_id=survey_id)

@main.route('/create_vector', methods=['GET', 'POST'])
def create_vector():
    """Handle the creation of a budget vector."""
    user_id = get_required_param('userid')
    survey_id = get_required_param('surveyid')
    subjects = get_subjects(int(survey_id))
    
    if not subjects:
        logger.error(f"No subjects found for survey_id {survey_id}")
        abort(404, description="Survey not found or has no subjects")
   
    if request.method == 'POST':
        user_vector = [int(request.form.get(subject, 0)) for subject in subjects]
        logger.debug(f"User {user_id} submitted vector: {user_vector}")
        
        if not is_valid_vector(user_vector):
            logger.warning(f"Invalid vector submitted by user {user_id}: {user_vector}")
            return render_template('create_vector.html', error=ERROR_MESSAGES['invalid_vector'], subjects=subjects, user_id=user_id, survey_id=survey_id)
        
        logger.info(f"Valid vector created by user {user_id}: {user_vector}")
        return redirect(url_for('main.survey', vector=','.join(map(str, user_vector)), userid=user_id, surveyid=survey_id))
    
    logger.debug(f"Create vector page accessed by user {user_id}")
    return render_template('create_vector.html', subjects=subjects, user_id=user_id, survey_id=survey_id)

@main.route('/survey', methods=['GET', 'POST'])
def survey():
    """Handle the survey process."""
    user_id = get_required_param('userid')
    survey_id = get_required_param('surveyid')
    subjects = get_subjects(int(survey_id))
    
    if not subjects:
        logger.error(f"No subjects found for survey_id {survey_id}")
        abort(404, description="Survey not found or has no subjects")

    if request.method == 'GET':
        user_vector = list(map(int, request.args.get('vector', '').split(',')))
        logger.debug(f"Survey accessed by user {user_id} with vector: {user_vector}")
        if len(user_vector) != len(subjects) or sum(user_vector) != 100:
            logger.warning(f"Invalid vector in survey GET for user {user_id}: {user_vector}")
            return redirect(url_for('main.create_vector', userid=user_id, surveyid=survey_id))
        
        comparison_pairs = list(generate_user_example(tuple(user_vector), n=10))
        awareness_check = generate_awareness_check(user_vector)
        
        logger.info(f"Survey generated for user {user_id} with vector: {user_vector}")
        return render_template('survey.html', 
                               user_vector=user_vector,
                               comparison_pairs=comparison_pairs,
                               awareness_check=awareness_check,
                               subjects=subjects,
                               user_id=user_id,
                               survey_id=survey_id,
                               zip=zip)
    
    elif request.method == 'POST':
        data = request.form
        user_vector = list(map(int, data.get('user_vector').split(',')))
        logger.debug(f"Survey submission received from user {user_id}. User vector: {user_vector}")
        
        # Check awareness question
        awareness_answer = int(data.get('awareness_check', 0))
        if awareness_answer != 2:
            logger.warning(f"User {user_id} failed awareness check")
            flash(ERROR_MESSAGES['failed_awareness'], "error")
            return redirect(url_for('main.survey', vector=','.join(map(str, user_vector)), userid=user_id, surveyid=survey_id))

        try:
            # Check if user already exists
            if not user_exists(int(user_id)):
                create_user(int(user_id))
                logger.info(f"User created in database with ID: {user_id}")
            else:
                logger.info(f"User with ID {user_id} already exists")
            
            survey_response_id = create_survey_response(user_id, int(survey_id), user_vector)
            logger.info(f"Survey response created with ID: {survey_response_id}")

            for i in range(10):
                option_1 = list(map(int, data.get(f'option1_{i}', '').split(',')))
                option_2 = list(map(int, data.get(f'option2_{i}', '').split(',')))
                user_choice = int(data.get(f'choice_{i}'))
                comparison_pair_id = create_comparison_pair(survey_response_id, i+1, option_1, option_2, user_choice)
                logger.debug(f"Comparison pair created: ID {comparison_pair_id}, Pair {i+1}, Choice: {user_choice}")
            
            mark_survey_as_completed(survey_response_id)
            logger.info(f"Survey marked as completed for user {user_id}: {survey_response_id}")
        except Exception as e:
            logger.error(f"Error processing survey submission for user {user_id}: {str(e)}", exc_info=True)
            return render_template('error.html', message=ERROR_MESSAGES['survey_processing_error'])

        return redirect(url_for('main.thank_you'))

@main.route('/thank_you')
def thank_you():
    logger.info("Thank you page accessed")
    return render_template('thank_you.html')

@main.errorhandler(400)
def bad_request(e):
    return render_template('error.html', message=e.description), 400

@main.errorhandler(404)
def not_found(e):
    return render_template('error.html', message=e.description), 404