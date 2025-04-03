import logging
from typing import Any, Dict, List, Optional, Union

import mysql.connector
from flask import current_app as app
from flask import g  # Flask's application context global
from mysql.connector import Error

logger = logging.getLogger(__name__)

# --- Connection Management using Flask's 'g' object ---


def get_db() -> Optional[mysql.connector.MySQLConnection]:
    """
    Opens a new database connection if there is none yet for the
    current application context ('g'). Adds the 'charset' parameter
    to ensure UTF-8 communication.
    """
    if "db" not in g:
        # First connection for this request
        try:
            g.db = mysql.connector.connect(
                host=app.config["MYSQL_HOST"],
                port=app.config["MYSQL_PORT"],
                database=app.config["MYSQL_DATABASE"],
                user=app.config["MYSQL_USER"],
                password=app.config["MYSQL_PASSWORD"],
                charset="utf8mb4",
                collation="utf8mb4_unicode_ci",
            )
            logger.debug("Database connection established for this request.")
        except Error as e:
            logger.error(f"Error connecting to MySQL database: {e}")
            g.db = None  # Store None in 'g' if connection failed
    return g.db


def close_db(e: Optional[Exception] = None) -> None:
    """
    Closes the database connection at the end of the request.
    This function is registered to run automatically by Flask.
    """
    db = g.pop(
        "db", None
    )  # Get connection from 'g' and removes the key or returns None if not exists

    if db is not None and db.is_connected():
        db.close()
        logger.debug("Database connection closed for this request.")


def init_app(flask_app) -> None:
    """
    Register database functions with the Flask app.
    This is called from the Flask app factory.
    """
    # Tells Flask to call 'close_db' when cleaning up after returning the response
    flask_app.teardown_appcontext(close_db)
    logger.info("Database teardown function registered.")


# --- Query Execution ---


def execute_query(
    query: str, params: Optional[tuple] = None, fetch_one: bool = False
) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]], int]]:
    """
    Executes a SQL query using the request-scoped database connection.

    Args:
        query (str): The SQL query string.
        params (tuple, optional): Parameters to bind to the query (prevents SQL injection).
        fetch_one (bool, optional): True to fetch only the first result row for SELECT.

    Returns:
        Optional[Union[Dict, List[Dict], int]]:
            - For SELECT: A single dict (fetch_one=True) or a list of dicts.
            - For INSERT: The last inserted row ID (int).
            - For UPDATE/DELETE: The number of affected rows (int).
            - None if an error occurs or the connection failed.
    """
    connection = get_db()  # Get the connection for *the current* request
    if not connection:
        logger.error("Cannot execute query, no database connection available.")
        return None

    logger.debug(f"Executing query: {query} | PARAMS: {params}")

    # Use a 'with' block for the cursor - ensures it's always closed automatically
    try:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(query, params if params else ())

            # Get the uppercase version of the query, stripped of leading/trailing whitespace,
            # to reliably check if it's a SELECT, INSERT, etc.
            query_upper = query.strip().upper()

            # Handle SELECT queries
            if query_upper.startswith("SELECT") or query_upper.startswith("SHOW"):
                if fetch_one:
                    result = cursor.fetchone()
                    logger.debug(f"Query result (one): {result}")
                else:
                    result = cursor.fetchall()
                    logger.debug(f"Query result (all): {len(result)} rows")
                return result

            # Handle INSERT/UPDATE/DELETE queries (require commit)
            else:
                connection.commit()  # Commit changes to the database
                if query_upper.startswith("INSERT"):
                    result = cursor.lastrowid
                    logger.debug(f"INSERT successful. Last row ID: {result}")
                else:
                    result = cursor.rowcount
                    logger.debug(f"UPDATE/DELETE successful. Affected rows: {result}")
                return result

    except Error as e:
        logger.error(f"Error executing query: {e}")
        return None
