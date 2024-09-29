import logging

from app import create_app
from database.db import get_db_connection

logger = logging.getLogger(__name__)

app = create_app()


def db_connection(app):
    with app.app_context():
        conn = get_db_connection()
        yield conn
        if conn:
            conn.close()


# is_sum_optimized(optimal_vector, option_1, option_2, user_choice)
