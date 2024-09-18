import logging
from flask import Blueprint, render_template, request, redirect, url_for, abort
from database.queries import create_user, create_survey_response, create_comparison_pair, mark_survey_as_completed
from utils.generate_examples import generate_user_example

main = Blueprint('main', __name__)

SUBJECTS = ["ביטחון", "חינוך", "בריאות"]

logger = logging.getLogger(__name__)

def get_required_param(param_name):
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
   
    if request.method == 'POST':
        user_vector = [int(request.form.get(subject, 0)) for subject in SUBJECTS]
        logger.debug(f"User {user_id} submitted vector: {user_vector}")
        
        if sum(user_vector) != 100 or any(v % 5 != 0 for v in user_vector):
            error_message = "הסכום חייב להיות 100 וכל מספר חייב להתחלק ב-5."
            logger.warning(f"Invalid vector submitted by user {user_id}: {user_vector}")
            return render_template('create_vector.html', error=error_message, subjects=SUBJECTS, user_id=user_id, survey_id=survey_id)
        
        logger.info(f"Valid vector created by user {user_id}: {user_vector}")
        return redirect(url_for('main.survey', vector=','.join(map(str, user_vector)), userid=user_id, surveyid=survey_id))
    
    logger.debug(f"Create vector page accessed by user {user_id}")
    return render_template('create_vector.html', subjects=SUBJECTS, user_id=user_id, survey_id=survey_id)

@main.route('/survey', methods=['GET', 'POST'])
def survey():
    """Handle the survey process."""
    user_id = get_required_param('userid')
    survey_id = get_required_param('surveyid')

    if request.method == 'GET':
        user_vector = tuple(map(int, request.args.get('vector', '').split(',')))
        logger.debug(f"Survey accessed by user {user_id} with vector: {user_vector}")
        if len(user_vector) != 3 or sum(user_vector) != 100:
            logger.warning(f"Invalid vector in survey GET for user {user_id}: {user_vector}")
            return redirect(url_for('main.create_vector', userid=user_id, surveyid=survey_id))
        
        edge_view = generate_user_example(user_vector, n=10)
        comparison_pairs = list(edge_view)
        logger.info(f"Survey generated for user {user_id} with vector: {user_vector}")
        return render_template('survey.html', 
                               user_vector=user_vector, 
                               comparison_pairs=comparison_pairs, 
                               subjects=SUBJECTS,
                               user_id=user_id,
                               survey_id=survey_id,
                               zip=zip)
    
    elif request.method == 'POST':
        data = request.form
        user_vector = list(map(int, data.get('user_vector').split(',')))
        logger.debug(f"Survey submission received from user {user_id}. User vector: {user_vector}")
        
        try:
            db_user_id = create_user(int(user_id))
            logger.info(f"User created in database with ID: {db_user_id}")
            
            survey_response_id = create_survey_response(db_user_id, int(survey_id), user_vector)
            logger.info(f"Survey response created with ID: {survey_response_id}")

            for i in range(10):
                option_1 = list(map(int, data.get(f'option1_{i}').split(',')))
                option_2 = list(map(int, data.get(f'option2_{i}').split(',')))
                user_choice = int(data.get(f'choice_{i}'))
                comparison_pair_id = create_comparison_pair(survey_response_id, i+1, option_1, option_2, user_choice)
                logger.debug(f"Comparison pair created: ID {comparison_pair_id}, Pair {i+1}, Choice: {user_choice}")
            
            mark_survey_as_completed(survey_response_id)
            logger.info(f"Survey marked as completed for user {user_id}: {survey_response_id}")
        except Exception as e:
            logger.error(f"Error processing survey submission for user {user_id}: {str(e)}", exc_info=True)
            return render_template('error.html', message="אירעה שגיאה במהלך עיבוד הסקר. אנא נסה שוב.")

        return redirect(url_for('main.thank_you'))

@main.route('/thank_you')
def thank_you():
    logger.info("Thank you page accessed")
    return render_template('thank_you.html')

@main.errorhandler(400)
def bad_request(e):
    return render_template('error.html', message=e.description), 400
