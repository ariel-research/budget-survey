import logging

from analysis.analysis_utils import process_data_to_dataframe, process_survey_responses
from app import create_app
from database.queries import retrieve_completed_survey_responses

logger = logging.getLogger(__name__)

app = create_app()


def get_all_completed_survey_responses():
    """
    Retrieves and processes all completed survey responses.

    Returns:
        list: A list of dictionaries containing processed survey response data.
    """
    try:
        with app.app_context():
            raw_results = retrieve_completed_survey_responses()
        processed_results = process_survey_responses(raw_results)
        logger.info(
            f"Successfully retrieved and processed {len(processed_results)} survey responses"
        )
        return processed_results
    except Exception as e:
        logger.error(f"Error in get_all_completed_survey_responses: {e}")
        raise


if __name__ == "__main__":
    try:
        results = get_all_completed_survey_responses()
        df = process_data_to_dataframe(results, "data/results.csv")
        print(df.head())
        logger.info("Survey processing completed successfully")
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
