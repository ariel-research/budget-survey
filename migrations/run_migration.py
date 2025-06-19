#!/usr/bin/env python3
import argparse
import logging
import os
import sys

import mysql.connector
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logging_config import setup_logging  # noqa: E402

# Set up the logging system
setup_logging()
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def read_sql_file(file_path):
    """Read SQL from file and split into statements"""
    with open(file_path, "r") as file:
        sql_content = file.read()

    # Split by semicolon but ignore semicolons inside comments
    statements = []
    current_statement = []
    in_comment = False

    for line in sql_content.splitlines():
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        # Handle comments
        if line.startswith("--"):
            continue

        current_statement.append(line)

        if line.endswith(";") and not in_comment:
            statements.append(" ".join(current_statement))
            current_statement = []

    # Add any remaining statement
    if current_statement:
        statements.append(" ".join(current_statement))

    return statements


def execute_migration(file_path, database_name):
    """Execute the SQL migration file on the specified database"""
    if not os.path.exists(file_path):
        logger.error(f"Migration file not found: {file_path}")
        return False

    try:
        # Connect to database
        conn = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST", "localhost"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            user=os.getenv("MYSQL_USER", "root"),
            password=os.getenv("MYSQL_PASSWORD", ""),
            database=database_name,
        )
        cursor = conn.cursor(dictionary=True)

        logger.info(f"Successfully connected to database {database_name}")

        # Read and execute SQL statements
        statements = read_sql_file(file_path)

        for statement in statements:
            if statement.strip():
                logger.info(f"Executing on {database_name}: {statement[:50]}...")
                cursor.execute(statement)

                # If the statement is a SELECT, fetch and display results
                if statement.strip().upper().startswith("SELECT"):
                    results = cursor.fetchall()
                    for row in results:
                        for key, value in row.items():
                            logger.info(f"{key}: {value}")

        # Commit changes
        conn.commit()
        logger.info(
            f"Migration {os.path.basename(file_path)} executed successfully "
            f"on {database_name}"
        )
        return True

    except mysql.connector.Error as err:
        logger.error(f"Database Error on {database_name}: {err}")
        if err.errno == 2003:
            logger.error(
                "Cannot connect to MySQL server. "
                "Please check if your MySQL server is running and "
                "the connection settings in your .env file are correct."
            )
            logger.error(
                f"Current connection settings: "
                f"Host={os.getenv('MYSQL_HOST', 'localhost')}:"
                f"{os.getenv('MYSQL_PORT', '3306')}, "
                f"User={os.getenv('MYSQL_USER', 'root')}, "
                f"Database={database_name}"
            )
        elif err.errno == 1049:  # Unknown database
            logger.warning(
                f"Database {database_name} does not exist. "
                f"Skipping migration for this database."
            )
            return True  # Don't treat this as a failure
        return False
    except Exception as e:
        logger.error(f"Error executing migration on {database_name}: {str(e)}")
        return False
    finally:
        if "conn" in locals() and conn.is_connected():
            cursor.close()
            conn.close()


def main():
    parser = argparse.ArgumentParser(description="Execute a SQL migration file")
    parser.add_argument("file", help="Path to the SQL migration file")

    # Add optional arguments for Docker connections
    parser.add_argument("--host", help="MySQL host (overrides MYSQL_HOST env variable)")
    parser.add_argument(
        "--port", type=int, help="MySQL port (overrides MYSQL_PORT env variable)"
    )
    parser.add_argument(
        "--main-only", action="store_true", help="Run migration only on main database"
    )
    parser.add_argument(
        "--test-only", action="store_true", help="Run migration only on test database"
    )

    args = parser.parse_args()

    # Override environment variables if command-line args are provided
    if args.host:
        os.environ["MYSQL_HOST"] = args.host
        logger.info(f"Using MySQL host from command line: {args.host}")

    if args.port:
        os.environ["MYSQL_PORT"] = str(args.port)
        logger.info(f"Using MySQL port from command line: {args.port}")

    # Define database names
    main_database = os.getenv("MYSQL_DATABASE", "survey")
    test_database = "test_survey"

    success = True

    # Run migration on main database
    if not args.test_only:
        logger.info("=" * 50)
        logger.info("RUNNING MIGRATION ON MAIN DATABASE")
        logger.info("=" * 50)
        success &= execute_migration(args.file, main_database)

    # Run migration on test database
    if not args.main_only:
        logger.info("=" * 50)
        logger.info("RUNNING MIGRATION ON TEST DATABASE")
        logger.info("=" * 50)
        success &= execute_migration(args.file, test_database)

    if success:
        logger.info("=" * 50)
        logger.info("ALL MIGRATIONS COMPLETED SUCCESSFULLY")
        logger.info("=" * 50)
    else:
        logger.error("=" * 50)
        logger.error("SOME MIGRATIONS FAILED")
        logger.error("=" * 50)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
