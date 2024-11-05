# Budget Survey Application

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Database Setup](#database-setup)
  - [Method 1: Manual Setup using MySQL Client](#method-1-manual-setup-using-mysql-client)
  - [Method 2: Using Docker Compose](#method-2-using-docker-compose)
- [Running the Application](#running-the-application)
- [Endpoints](#endpoints)
  - [Main Routes](#main-routes)
  - [API Endpoints](#api-endpoints)
- [Screen Text Locations](#screen-text-locations)
- [Database](#database)
- [Modifying the Survey](#modifying-the-survey)
  - [Changing the Active Survey](#changing-the-active-survey)
  - [Adding or Modifying Surveys](#adding-or-modifying-surveys)
- [Algorithm](#algorithm)
- [Analysis](#analysis)
  - [Running the Analysis](#running-the-analysis)
  - [Generating the Survey Report](#generating-the-survey-report)
  - [Key Components and Functions](#key-components-and-functions)
  - [Generated Files](#generated-files)
  - [Table Explanations](#table-explanations)
- [Testing](#testing)
  - [Test Structure](#test-structure)
  - [Running Tests](#running-tests)
    - [Quick Start](#quick-start)
    - [Test Categories](#test-categories)
      - [Analysis Tests](#analysis-tests)
      - [API Tests](#api-tests)
      - [Database Tests](#database-tests)
      - [Unit Tests](#unit-tests)
      - [UI Tests](#ui-tests)
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
https://survey.csariel.xyz/?userID=...&surveyID=...

Notes: 

- Both 'userID' and 'surveyID' parameters are required in the URL.
- The 'userID' parameter is used to obtain the user_id.
- While the 'surveyID' parameter is required in the URL, it is not used by the application. Instead, the survey ID is hardcoded in the config file.

## Endpoints

### Main Routes
- `/`: The first survey page, shows an introduction to the survey and consent form. 
- `/create_vector`: second survey page, asks the user for his ideal budget.
- `/survey`: The third survey page, asks the user to compare pairs of non-ideal budgets.
- `/thank_you`: Thank you page, shown after survey completion.
- `/report`: Displays the survey analysis report in PDF format. This endpoint:
  - Automatically ensures the report is up-to-date with the latest survey data
  - Shows the PDF directly in the browser
  - Allows downloading the report
- `/dev/report`: Development endpoint for testing report modifications. This endpoint:
  - Always generates a fresh PDF report regardless of database state
  - Creates the report as 'survey_analysis_report_dev.pdf'
  - Useful for testing report template changes without affecting the production report
  - Does not implement the automatic refresh mechanism of the main `/report` endpoint

Note: The `/report` endpoint includes an automatic refresh mechanism that:
1. Checks if the CSV files are up-to-date with the database
2. Regenerates CSVs if they're outdated or missing
3. Checks if the PDF report is up-to-date with the CSVs
4. Regenerates the PDF if needed
This ensures that the report always reflects the most recent survey data without manual intervention.

For development purposes, use the `/dev/report` endpoint when making changes to report templates or generation logic, as it will always create a fresh report without caching considerations.

### API Endpoints
- `/get_messages`: Returns a JSON dictionary of all error messages used in the application. This endpoint is used by the frontend to display localized error messages to users.

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

The project includes an 'analysis' package that processes the collected survey data and generates insightful statistics and reports. This package is crucial for understanding user responses and deriving meaningful conclusions from the survey data.

### Running the Analysis

To run the survey analysis, use the following command from the project root directory:

```
python -m analysis.survey_analysis
```

### Generating the Survey Report

To generate a comprehensive PDF report of the survey results, use the following command from the project root directory:

```
python -m analysis.survey_report_generator_pdf
```

This command will create a PDF report named 'survey_analysis_report.pdf' in the 'data' directory. The report includes:

- Executive summary
- Overall survey participation statistics
- Visualizations of algorithm preferences:
  - Per-survey answer percentages
  - User survey majority choices
  - Overall majority choice distribution
  - Total answer percentage distribution
- Detailed survey-wise analysis
- Individual participant analysis
- Key findings and conclusions
- Methodology description

### Key Components and Functions

The analysis package consists of several key components:

1. Data Retrieval and Processing:
   - `get_all_completed_survey_responses()`: Retrieves and processes all completed survey responses from the database.

2. Statistical Analysis:
   - `generate_survey_optimization_stats(df)`: Generates optimization statistics for all survey responses.
   - `summarize_stats_by_survey(df)`: Summarizes statistics by survey ID, including a total summary row.

3. Report Generation:
   - `generate_report()`: Orchestrates the entire report generation process, including data loading, analysis, visualization, and PDF creation.
   - Various functions for generating specific report sections (e.g., executive summary, survey analysis, visualizations).

4. Visualization:
   - Multiple functions for creating charts and graphs to visualize survey results and trends.

For a complete list of functions and their descriptions, please refer to the source code in the `analysis` directory.
### Generated Files

The analysis scripts generate the following files in the `data` directory:

1. **all_completed_survey_responses.csv**: Raw data of all completed survey responses.
2. **survey_optimization_stats.csv**: Optimization statistics for each survey response.
3. **summarize_stats_by_survey.csv**: Aggregated statistics for each survey and overall summary.
4. **survey_analysis_report.pdf**: Comprehensive PDF report of survey results and analysis.

### Table Explanations

1. **All Completed Survey Responses**
   - Each row represents a single comparison pair from a completed survey.
   - Includes survey ID, user ID, optimal allocation, and details of each comparison pair.

2. **Survey Optimization Stats**
   - Each row represents a completed survey response.
   - Shows the number of sum-optimized and ratio-optimized choices for each response.

3. **Summarize Stats by Survey**
   - Each row represents aggregate data for a single survey, with a final row summarizing across all surveys.
   - Includes metrics such as unique users, total answers, and percentages of sum/ratio optimized choices.

Remember to regularly run both the analysis script and the report generator to keep these statistics and reports up-to-date as new survey responses are collected.

## Testing

The project includes comprehensive test coverage across multiple testing domains. All tests are located in the `tests/` directory.


## Testing

The project includes comprehensive test coverage across multiple testing domains. All tests are located in the `tests/` directory.

### Test Structure
```python
tests/
├── analysis/                  # Data analysis and reporting tests
│   ├── utils/                
│   │   ├── test_analysis_utils.py
│   │   ├── test_file_utils.py
│   │   └── test_visualization_utils.py
│   ├── test_report_content_generators.py
│   ├── test_survey_analysis.py
│   └── test_survey_report_generator.py
├── api/                      # API endpoint tests
│   └── test_routes.py
├── database/                 # Database integration tests
│   └── test_database_integration.py
├── performance/              # Load and performance tests
│   └── load_test.py
├── UI/                      # Frontend/UI tests
│   └── test_client_side.py
└── unit/                    # Core functionality tests
    ├── test_generate_examples.py
    └── test_survey_utils.py
```

### Running Tests

#### Quick Start
Run all tests:
```bash
pytest
```

#### Test Categories

##### Analysis Tests
**Description:** Data processing and reporting
```bash
pytest tests/analysis/
```

##### API Tests
**Description:** Endpoint functionality and error handling
```bash
pytest tests/api/
```

##### Database Tests
**Description:** Data persistence and integrity
```bash
pytest tests/database/
```

##### Unit Tests
**Description:** Core algorithms and utilities
```bash
pytest tests/unit/
```

##### UI Tests
**Description:** Frontend functionality
```bash
pytest tests/UI/
```

##### Load Testing
**Description:** Performance and scalability testing
We use Locust for performance testing. The load tests simulate realistic user behavior patterns.

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
