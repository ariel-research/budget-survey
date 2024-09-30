import logging

import pandas as pd

from analysis.analysis_utils import process_survey_responses, save_dataframe_to_csv
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


def main() -> None:
    """
    Main function to run the survey processor process.
    """
    try:
        all_completed_survey_responses = get_all_completed_survey_responses()
        df = pd.DataFrame(all_completed_survey_responses)
        save_dataframe_to_csv(df, "data/all_completed_survey_responses.csv")
        print(df.head())
        logger.info("Survey processing completed successfully")
    except Exception as e:
        logger.error(f"Error in main execution: {e}")


if __name__ == "__main__":
    main()
