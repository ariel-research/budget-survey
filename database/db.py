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


def execute_query(query, params=None):
    """
    Executes a SQL query against the MySQL database.

    Args:
        query (str): The SQL query to execute.
        params (tuple, optional): Parameters to pass with the query.

    Returns:
        list or int or None: Query results if a SELECT statement, last row ID if an INSERT statement, or None if an error occurs.
    """
    logger.debug(f"Executing query: {query} with params: {params}")
    connection = get_db_connection()
    if connection is None:
        return None

    try:
        cursor = connection.cursor(dictionary=True)
        if params:
            cursor.execute(query, params)  # Execute query with parameters if provided
        else:
            cursor.execute(query)

        if query.strip().upper().startswith("SELECT"):
            result = cursor.fetchall()  # Fetch all rows if it's a SELECT query
            logger.debug(f"Query result: {result}")
        else:
            connection.commit()  # Commit changes if it's an INSERT or UPDATE query
            result = cursor.lastrowid
            logger.debug(f"Last inserted row ID: {result}")

        return result
    except Error as e:
        logger.error(f"Error executing query: {e}")
        return None
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            logger.debug("Connection closed")
