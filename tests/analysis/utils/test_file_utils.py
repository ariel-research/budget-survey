from unittest.mock import patch

import pandas as pd
import pytest

from analysis.utils.file_utils import ensure_directory_exists, save_dataframe_to_csv


def test_ensure_directory_exists_new_directory():
    """Test directory creation when it doesn't exist."""
    with patch("os.path.exists") as mock_exists, patch("os.makedirs") as mock_makedirs:
        mock_exists.return_value = False
        ensure_directory_exists("/path/to/file.csv")
        mock_makedirs.assert_called_once_with("/path/to")


def test_ensure_directory_exists_existing_directory():
    """Test no directory creation when it already exists."""
    with patch("os.path.exists") as mock_exists, patch("os.makedirs") as mock_makedirs:
        mock_exists.return_value = True
        ensure_directory_exists("/path/to/file.csv")
        mock_makedirs.assert_not_called()


def test_save_dataframe_to_csv_success():
    """Test successful saving of DataFrame to CSV."""
    df = pd.DataFrame({"name": ["Alice", "Bob"], "age": [30, 25]})
    filename = "test_output.csv"

    with (
        patch("analysis.utils.file_utils.ensure_directory_exists") as mock_ensure_dir,
        patch("pandas.DataFrame.to_csv") as mock_to_csv,
    ):
        save_dataframe_to_csv(df, filename)
        mock_ensure_dir.assert_called_once_with(filename)
        mock_to_csv.assert_called_once_with(filename, index=False)


def test_save_dataframe_to_csv_empty_dataframe():
    """Test error handling when saving empty DataFrame."""
    df = pd.DataFrame()
    with pytest.raises(ValueError, match="Input DataFrame is empty"):
        save_dataframe_to_csv(df, "test.csv")


def test_save_dataframe_to_csv_io_error():
    """Test handling of IO errors during save."""
    df = pd.DataFrame({"col1": [1, 2]})
    with (
        patch("analysis.utils.file_utils.ensure_directory_exists"),
        patch("pandas.DataFrame.to_csv", side_effect=IOError("Mock IO Error")),
        pytest.raises(IOError, match="Mock IO Error"),
    ):
        save_dataframe_to_csv(df, "test.csv")
