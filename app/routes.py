import logging
from flask import Blueprint, render_template, request, redirect, url_for
from database.queries import create_user, create_survey_response, create_comparison_pair, mark_survey_as_completed
from utils.generate_examples import generate_user_example

main = Blueprint('main', __name__)

SUBJECTS = ["ביטחון", "חינוך", "בריאות"]
SURVEY_ID = 1

logger = logging.getLogger(__name__)

@main.route('/')
def index():
    """
    Render the index page.
    
    This function checks for a userid in the URL parameters.
    If not present, it renders an error page.
    """
    userid = request.args.get('userid')
    if not userid:
        logger.warning("Index page accessed without userid")
        return render_template('error.html', message="מזהה המשתמש אינו נמצא. צור קשר לקבלת לינק תקין, אשר מכיל את מזהה המשתמש.")
    logger.info(f"Index page accessed by userid {userid}")
    return render_template('index.html', userid=userid)

@main.route('/create_vector', methods=['GET', 'POST'])
def create_vector():
    """
    Handle the creation of a budget vector.
    
    GET: Render the create_vector page.
    POST: Process the submitted vector, validate it, and redirect to the survey.
    """
    userid = request.args.get('userid')
    if not userid:
        logger.warning("Attempt to access create_vector without userid")
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        # Extract the user vector from the form data
        user_vector = [int(request.form.get(f'subject_{i}', 0)) for i in range(3)]
        logger.debug(f"User {userid} submitted vector: {user_vector}")
        
        if sum(user_vector) != 100 or any(v % 5 != 0 for v in user_vector):
            error_message = "הסכום חייב להיות 100 וכל מספר חייב להתחלק ב-5."
            logger.warning(f"Invalid vector submitted by user {userid}: {user_vector}")
            return render_template('create_vector.html', error=error_message, subjects=SUBJECTS, userid=userid)
        
        logger.info(f"Valid vector created by user {userid}: {user_vector}")
        # Redirect to survey page with user's vector and ID in URL parameters
        return redirect(url_for('main.survey', vector=','.join(map(str, user_vector)), userid=userid))
    
    logger.debug(f"Create vector page accessed by user {userid}")
    return render_template('create_vector.html', subjects=SUBJECTS, userid=userid)

@main.route('/survey', methods=['GET', 'POST'])
def survey():
    """
    Handle the survey process.
    
    GET: Generate and display survey questions based on the user's vector.
    POST: Process and store the survey responses.
    """
    userid = request.args.get('userid')
    if not userid:
        logger.warning("Attempt to access survey without userid")
        return redirect(url_for('main.index'))

    if request.method == 'GET':
        # Converts the vector back into a tuple of integers
        user_vector = tuple(map(int, request.args.get('vector', '').split(',')))
        logger.debug(f"Survey accessed by user {userid} with vector: {user_vector}")
        if len(user_vector) != 3 or sum(user_vector) != 100:
            logger.warning(f"Invalid vector in survey GET for user {userid}: {user_vector}")
            return redirect(url_for('main.create_vector', userid=userid))
        
        # Generate survey questions based on the user's vector
        edge_view = generate_user_example(user_vector, n=10)
        comparison_pairs = list(edge_view)
        logger.info(f"Survey generated for user {userid} with vector: {user_vector}")
        return render_template('survey.html', 
                               user_vector=user_vector, 
                               comparison_pairs=comparison_pairs, 
                               subjects=SUBJECTS,
                               userid=userid,
                               zip=zip)
    
    elif request.method == 'POST':
        data = request.form
        user_vector = list(map(int, data.get('user_vector').split(',')))
        logger.debug(f"Survey submission received from user {userid}. User vector: {user_vector}")
        
        try:
            # Store survey data in the database
            db_user_id = create_user(int(userid))
            logger.info(f"User created in database with ID: {db_user_id}")
            
            survey_response_id = create_survey_response(db_user_id, SURVEY_ID, user_vector)
            logger.info(f"Survey response created with ID: {survey_response_id}")

            for i in range(10):
                option_1 = list(map(int, data.get(f'option1_{i}').split(',')))
                option_2 = list(map(int, data.get(f'option2_{i}').split(',')))
                user_choice = int(data.get(f'choice_{i}'))
                comparison_pair_id = create_comparison_pair(survey_response_id, i+1, option_1, option_2, user_choice)
                logger.debug(f"Comparison pair created: ID {comparison_pair_id}, Pair {i+1}, Choice: {user_choice}")
            
            mark_survey_as_completed(survey_response_id)
            logger.info(f"Survey marked as completed for user {userid}: {survey_response_id}")
        except Exception as e:
            logger.error(f"Error processing survey submission for user {userid}: {str(e)}", exc_info=True)
            return render_template('error.html', message="אירעה שגיאה במהלך עיבוד הסקר. אנא נסה שוב.")

        return redirect(url_for('main.thank_you'))

@main.route('/thank_you')
def thank_you():
    logger.info("Thank you page accessed")
    return render_template('thank_you.html')