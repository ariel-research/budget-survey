import os
import secrets
from typing import Type

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration with common settings."""

    # Database settings
    MYSQL_HOST: str = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT: int = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_DATABASE: str = os.getenv("MYSQL_DATABASE", "survey")
    MYSQL_USER: str = os.getenv("MYSQL_USER", "survey")
    MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD")

    # Application settings
    SURVEY_ID: int = 4
    PORT: int = 5001
    DEBUG: bool = os.getenv("FLASK_ENV", "development") == "development"

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
            "COMPLETE": "finish", 
            # "COMPLETE": "run",   # By request from Shaked 
            "ATTENTION_FAILED": "attentionfilter"
        },
    }

    # Survey base URL
    SURVEY_BASE_URL: str = (
        "http://127.0.0.1:5000"
        if os.getenv("FLASK_ENV") == "development"
        else "https://survey.csariel.xyz"
    )


class TestConfig(Config):
    """Test-specific configuration."""

    MYSQL_DATABASE: str = "test_survey"
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
