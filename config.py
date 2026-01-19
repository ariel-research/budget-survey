import os
import secrets
from typing import Type

from dotenv import load_dotenv

load_dotenv()


class Config:
    # Database settings
    MYSQL_HOST: str = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT: int = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_DATABASE: str = os.getenv("MYSQL_DATABASE", "survey")
    MYSQL_USER: str = os.getenv("MYSQL_USER", "survey")
    MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD")

    # Application settings
    SURVEY_ID = int(os.getenv("SURVEY_ID", 1))
    PORT = 5001
    DEBUG: bool = os.getenv("FLASK_ENV", "development") == "development"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    PAGINATION_PER_PAGE: int = 10

    # Security settings
    SECRET_KEY = os.getenv(
        "FLASK_SECRET_KEY",
        secrets.token_hex(32),  # Generates a secure default key for development
    )

    # Language settings
    LANGUAGES: list[str] = ["he", "en"]
    DEFAULT_LANGUAGE: str = "he"

    # Panel4All settings
    PANEL4ALL = {
        "BASE_URL": "http://www.panel4all.co.il/survey_runtime/external_survey_status.php",
        "STATUS": {
            "COMPLETE": "finish",  # For users who completed the survey successfully
            "ATTENTION_FAILED": "attentionfilter",  # For users who faild the attention check
            "FILTEROUT": "filterout",  # For users who do not qualify for the survey
        },
        # "PTS": {
        #     "FIRST_AWARENESS": 7,  # User fails first awareness question
        #     "SECOND_AWARENESS": 10,  # User fails second awareness question
        # },
    }

    SURVEY_BASE_URL = os.getenv("SURVEY_BASE_URL", "http://localhost:5001")


class TestConfig(Config):
    """Test-specific configuration."""

    MYSQL_DATABASE: str = os.getenv("TEST_MYSQL_DATABASE", "test_survey")
    TESTING: bool = True


def get_config() -> Type[Config]:
    """
    Get appropriate configuration based on environment.

    Returns:
        Type[Config]: Configuration class to use
    """
    if os.getenv("FLASK_ENV") == "testing":
        return TestConfig
    return Config
