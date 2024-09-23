import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "survey")
    MYSQL_USER = os.getenv("MYSQL_USER", "survey")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
    # Modify to the current survey ID
    SURVEY_ID = 1
    DEBUG = os.getenv("FLASK_ENV", "development") == "development"


def get_config():
    return Config
