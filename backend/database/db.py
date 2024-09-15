from dotenv import load_dotenv
import os
import mysql.connector
from mysql.connector import Error
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
load_dotenv(dotenv_path)

def get_db_connection():  
    host = os.getenv('MYSQL_HOST', 'localhost')
    port = int(os.getenv('MYSQL_PORT', '3307'))
    database = os.getenv('MYSQL_DATABASE', 'survey_app_db')
    user = os.getenv('MYSQL_USER', 'survey_user')
    password = os.getenv('MYSQL_PASSWORD')

    try:
        connection = mysql.connector.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
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

        if query.strip().upper().startswith('SELECT'):
            result = cursor.fetchall()  # Fetch all rows if it's a SELECT query
            logger.info(f"Query result: {result}")
        else:
            connection.commit()  # Commit changes if it's an INSERT or UPDATE query
            result = cursor.lastrowid
            logger.info(f"Last inserted row ID: {result}")

        return result
    except Error as e:
        logger.error(f"Error executing query: {e}")
        return None
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            logger.debug("Connection closed")
