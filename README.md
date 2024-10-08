# Budget Survey Application

## Table of Contents

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Database Setup](#database-setup)
  - [Method 1: Manual Setup using MySQL Client](#method-1-manual-setup-using-mysql-client)
  - [Method 2: Using Docker Compose](#method-2-using-docker-compose)
- [Running the Application](#running-the-application)
- [Endpoints](#endpoints)
- [Screen Text Locations](#screen-text-locations)
- [Database](#database)
- [Modifying the Survey](#modifying-the-survey)
  - [Changing the Active Survey](#changing-the-active-survey)
  - [Adding or Modifying Surveys](#adding-or-modifying-surveys)
- [Algorithm](#algorithm)
- [Analysis](#analysis)
  - [Running the Analysis](#running-the-analysis)
  - [Main Functions](#main-functions)
  - [Generated Tables](#generated-tables)
  - [Table Explanations](#table-explanations)
- [Testing](#testing)
  - [Unit Tests](#unit-tests)
  - [Database Integration Tests](#database-integration-tests)
  - [API Tests](#api-tests)
  - [Load Testing](#load-testing)
- [Development](#development)

## Overview
This project aims to collect data to develop an algorithm for optimal budget calculations, considering the votes of many users. Users allocate money among a few subjects, creating their optimal allocation. They then compare ten pairs of options, optimizing for difference and ratio against their optimal allocation.

## Prerequisites
- Python 3.8+
- MySQL 8.0+
- pip
- virtualenv
- Docker (optional, only if you prefer to use Docker for database setup)

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/ariel-research/budget-survey
   cd budget-survey
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up the MySQL database (see Database section below)

5. Create a `.env` file in the project root and add the necessary environment variables (see `.env.example` for reference)

## Database Setup

You can set up the database using one of two methods:

### Method 1: Manual Setup using MySQL Client

1. Connect to your MySQL server using the MySQL client.

2. Create a new database:

   ```sql
   CREATE DATABASE survey;
   ```

3. Use the newly created database:

   ```sql
   USE survey;
   ```

4. Run the SQL commands from the database/schema.sql file to create the necessary tables and structure.

### Method 2: Using Docker Compose

1. Ensure you have Docker and Docker Compose installed on your system.

2. Navigate to the project root directory where the docker-compose.yml file is located.

3. Run the following command to start the MySQL container and set up the database:

   ```
   docker-compose up -d db
   ```

This will create a MySQL container, create the database, and run the initialization script (`database/schema.sql`) to set up the necessary tables and structure.

Note: Make sure your .env file is properly configured with the correct database connection details before running either method.

## Running the Application

1. Activate the virtual environment (if not already activated)

2. Run the Flask application:
   ```
   python app.py
   ```

3. Access the application at `http://localhost:5001`

The live version of the application can be accessed at:
https://survey.csariel.xyz/?userid=...&surveyid=...

Notes: 

- Both 'userid' and 'surveyid' parameters are required in the URL.
- The 'userid' parameter is used to obtain the user_id.
- While the 'surveyid' parameter is required in the URL, it is not used by the application. Instead, the survey ID is hardcoded in the config file.

## Endpoints
- `/`: The first survey page, shows an introduction to the survey and consent form. 
- `/create_vector`: second survey page, asks the user for his ideal budget.
- `/survey`: The third survey page, asks the user to compare pairs of non-ideal budgets.
- `/thank_you`: Thank you page, shown after survey completion.

## Screen Text Locations
To modify the text displayed on each screen of the application, here's a guide to which files contain the text for each screen:
1. **Index Page (Introduction and Consent)**
   - File: `application/templates/index.html`
   - This file contains the introductory text on the first page of the survey.
2. **Create Vector Page (Ideal Budget Input)**
   - File: `application/templates/create_vector.html`
   - This file includes the text and instructions for users to input their ideal budget allocation.
3. **Survey Page (Budget Comparison)**
   - File: `application/templates/survey.html`
   - Contains the text for the main survey page where users compare pairs of budget allocations.
4. **Thank You Page**
   - File: `application/templates/thank_you.html`
   - Includes the text shown on the completion page after the survey is finished.
5. **Error Page**
   - File: `application/templates/error.html`
   - Contains text displayed when an error occurs during the survey process.
     
Note: Some dynamic error messages are defined in:

- `application/messages.py`: Contains error messages used throughout the application.

**Important**: The survey name and subjects are dynamically loaded from the `surveys` table in the database. These are not hardcoded in any template file but are retrieved and displayed based on the current survey ID.

## Database
The application uses a MySQL database. Here's the schema:

![Database Schema](docs/db_schema_diagram.png)

## Modifying the Survey

### Changing the Active Survey
To modify the survey that users will get, you need to manually update the `SURVEY_ID` value in the file [`config.py`](config.py). Look for the following line and change the number to the desired survey ID:

```python
SURVEY_ID = 1  # Change this to the desired survey ID
```

### Adding or Modifying Surveys
To add new surveys or modify existing ones, follow these steps:

1. Connect to the database on the remote server using MySQL Workbench via SSH:
   - Create a new connection
   - Choose "Standard TCP/IP over SSH" as the connection method
   - SSH Hostname: [your_server_address]
   - SSH Username: [your_ssh_username]
   - SSH Password: [your_ssh_password] (or use SSH Key File)
   - MySQL Hostname: 127.0.0.1
   - MySQL Server Port: 3306
   - Username: [your_mysql_username]
   - Password: [your_mysql_password]

2. Once connected, you can run SQL queries to add or modify surveys. Here are some example queries:

   Add a new survey:
   ```sql
   INSERT INTO surveys (name, description, subjects, active)
   VALUES ('Budget Survey 2024', 'Annual budget allocation survey', '["Health", "Education", "Defense", "Welfare"]', TRUE);
   ```

   Modify an existing survey:
   ```sql
   UPDATE surveys
   SET name = 'Updated Budget Survey 2024',
       description = 'Revised annual budget allocation survey',
       subjects = '["Health", "Education", "Defense", "Infrastructure"]'
   WHERE id = 1;
   ```

   Deactivate a survey:
   ```sql
   UPDATE surveys
   SET active = FALSE
   WHERE id = 1;
   ```

Remember to update the `SURVEY_ID` in `config.py` after adding or modifying surveys to ensure the application uses the correct survey.

## Algorithm
The core algorithm of this application is implemented in the `generate_user_example` function. The function generates a graph based on the user's optimal budget allocation, creating comparison pairs that optimize for both difference and ratio.

## Analysis

The project includes an 'analysis' package that processes the collected survey data and generates insightful statistics. This package is crucial for understanding user responses and deriving meaningful conclusions from the survey data.

### Running the Analysis

To run the survey analysis, use the following command from the project root directory:

```
python -m analysis.survey_analysis
```

### Main Functions

The analysis package contains several key functions:

1. `get_all_completed_survey_responses()`: Retrieves and processes all completed survey responses from the database.
2. `generate_survey_optimization_stats(df)`: Generates optimization statistics for all survey responses.
3. `summarize_stats_by_survey(df)`: Summarizes statistics by survey ID, including a total summary row.

### Generated Tables

The analysis script generates three CSV files, all saved in the `data` directory:

1. **all_completed_survey_responses.csv**
   - Location: `data/all_completed_survey_responses.csv`
   - Content: Raw data of all completed survey responses, including user choices for each comparison pair.
   - Use: Provides a comprehensive view of all survey data for detailed analysis.

2. **survey_optimization_stats.csv**
   - Location: `data/survey_optimization_stats.csv`
   - Content: Optimization statistics for each survey response, including the number of sum-optimized and ratio-optimized choices.
   - Use: Helps in understanding individual user tendencies towards sum or ratio optimization.

3. **summarize_stats_by_survey.csv**
   - Location: `data/summarize_stats_by_survey.csv`
   - Content: Aggregated statistics for each survey, including total responses, optimization percentages, and a summary row for overall statistics.
   - Use: Provides a high-level overview of survey results and overall optimization trends.

### Table Explanations

1. **All Completed Survey Responses**
   - Each row represents a single comparison pair from a completed survey.
   - Includes survey ID, user ID, optimal allocation, and details of each comparison pair.
   - Useful for in-depth analysis of individual responses and patterns.

2. **Survey Optimization Stats**
   - Each row represents a completed survey response.
   - Shows the number of sum-optimized and ratio-optimized choices for each response.
   - Helps identify whether users tend to optimize for sum differences or ratios.

3. **Summarize Stats by Survey**
   - Each row represents aggregate data for a single survey, with a final row summarizing across all surveys.
   - Includes metrics such as unique users, total answers, and percentages of sum/ratio optimized choices.
   - Provides a quick overview of survey performance and user tendencies across different surveys.

Remember to regularly run the analysis script to keep these statistics up-to-date as new survey responses are collected.

## Testing

The project includes various types of tests to ensure the reliability and performance of the application. To run the tests, make sure you have activated your virtual environment and installed the required dependencies.

### Unit Tests

To run the unit tests, use the following command:

```
pytest tests/unit
```

These tests cover individual components and functions of the application.

### Database Integration Tests

To run the database integration tests, use the following command:

```
pytest tests/database/test_database_integration.py
```

These tests verify the interaction between the application and the database, ensuring that database operations work as expected.

### API Tests

To run the API tests, use the following command:

```
pytest tests/api/test_routes.py
```

These tests check the functionality of the application's API endpoints.

### Load Testing

For load testing, we use Locust. Before running the load test, ensure that your application server is up and running.

To run the load test, follow these steps:

1. Start your application server if it's not already running.

2. Run Locust in headless mode using the following command:

```
locust -f tests/performance/load_test.py --headless -u 100 -r 2 -t 1m --host=[your host]
```

Replace `[your host]` with the appropriate host address (e.g., `http://localhost:5001`).

This command does the following:
- `-f tests/performance/load_test.py`: Specifies the Locust file to use
- `--headless`: Runs Locust in headless mode (no web UI)
- `-u 100`: Simulates 100 users
- `-r 10`: Spawns 2 users per second
- `-t 5m`: Runs the test for 1 minute
- `--host=[your host]`: Specifies the host to load test

3. Locust will run the test and output the results to the console. You'll see real-time statistics including request counts, response times, and failure rates.

4. After the test is completed, Locust will generate a summary of the test results in the console output.

Note: It's crucial to have your application server running before starting the Locust test. The load test will attempt to interact with your live application, so an active server is necessary for accurate results.

## Development
- Use the provided `.pre-commit-config.yaml` for code formatting and linting
- Run tests using `pytest`
- Logs are stored in the `logs` directory
