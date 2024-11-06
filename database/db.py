import logging

import mysql.connector
from flask import current_app as app
from mysql.connector import Error

logger = logging.getLogger(__name__)


def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host=app.config["MYSQL_HOST"],
            port=app.config["MYSQL_PORT"],
            database=app.config["MYSQL_DATABASE"],
            user=app.config["MYSQL_USER"],
            password=app.config["MYSQL_PASSWORD"],
        )
        logger.info("Database connection established")
        return connection
    except Error as e:
        logger.error(f"Error connecting to MySQL database: {e}")
        return None


def execute_query(query, params=None, fetch_one=False):
    """
    Executes a SQL query against the MySQL database.

    Args:
        query (str): The SQL query to execute.
        params (tuple, optional): Parameters to pass with the query.
        fetch_one (bool, optional): If True, returns only the first row for SELECT queries.

    Returns:
        dict or list or int or None:
            - For SELECT: Single row (dict) if fetch_one=True, list of rows otherwise
            - For INSERT: Last row ID (int)
            - For UPDATE/DELETE: Number of affected rows
            - None if an error occurs
    """
    logger.debug(f"Executing query: {query} with params: {params}")
    connection = get_db_connection()
    if connection is None:
        return None

    try:
        cursor = connection.cursor(dictionary=True)
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        # Handle different query types
        if query.strip().upper().startswith("SELECT"):
            if fetch_one:
                result = cursor.fetchone()  # Fetch single row
            else:
                result = cursor.fetchall()  # Fetch all rows
            logger.debug(f"Query result: {result}")
        else:
            connection.commit()  # Commit changes for INSERT/UPDATE/DELETE
            if query.strip().upper().startswith("INSERT"):
                result = cursor.lastrowid  # Return last inserted ID
            else:
                result = cursor.rowcount  # Return number of affected rows
            logger.debug(f"Query affected rows/last ID: {result}")

        return result
    except Error as e:
        logger.error(f"Error executing query: {e}")
        return None
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            logger.debug("Connection closed")
