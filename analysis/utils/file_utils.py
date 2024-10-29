import logging
import os

import pandas as pd

logger = logging.getLogger(__name__)


def ensure_directory_exists(file_path: str) -> None:
    """
    Ensure that the directory for the given file path exists.
    If it doesn't exist, create it.

    Args:
        file_path: The full path of the file, including filename.
    """
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
        logger.info(f"Created directory: {directory}")


def save_dataframe_to_csv(df: pd.DataFrame, csv_filename: str) -> None:
    """
    Save a pandas DataFrame to a CSV file.

    Args:
        df: A pandas DataFrame to be saved.
        csv_filename: The filename (including path) where the CSV will be saved.

    Raises:
        ValueError: If the DataFrame is empty.
    """
    if df.empty:
        logger.error("Input DataFrame is empty")
        raise ValueError("Input DataFrame is empty")

    try:
        ensure_directory_exists(csv_filename)
        logger.info(f"Writing DataFrame to {csv_filename}")
        df.to_csv(csv_filename, index=False)
        logger.info(f"Successfully wrote data to {csv_filename}")
    except Exception as e:
        logger.error(f"Error occurred while saving DataFrame to CSV: {e}")
        raise
