import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "survey")
    MYSQL_USER = os.getenv("MYSQL_USER", "survey")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
    SURVEY_ID = 1
    PORT = 5001
    DEBUG = os.getenv("FLASK_ENV", "development") == "development"


class TestConfig(Config):
    MYSQL_DATABASE = "test_survey"
    TESTING = True


def get_config():
    if os.getenv("FLASK_ENV") == "testing":
        return TestConfig
    return Config
