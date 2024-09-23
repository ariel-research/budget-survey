# Budget Survey Application

## Table of Contents
- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Running the Application](#running-the-application)
- [Endpoints](#endpoints)
- [Database](#database)
- [Modifying the Survey](#modifying-the-survey)
- [Algorithm](#algorithm)
- [Development](#development)

## Overview
This project aims to collect data for developing an algorithm for optimal budget calculations, considering the votes of many users. Users allocate money among a few subjects, creating their optimal allocation. They then compare ten pairs of options, optimizing for difference and ratio against their optimal allocation.

## Prerequisites
- Python 3.8+
- MySQL 8.0+
- pip
- virtualenv

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

## Running the Application

1. Activate the virtual environment (if not already activated)

2. Run the Flask application:
   ```
   python app.py
   ```

3. Access the application at `http://localhost:5001`

The live version of the application can be accessed at:
https://survey.csariel.xyz/?userid=105&surveyid=1

Notes: 

- Both 'userid' and 'surveyid' parameters are required in the URL.

- The 'userid' parameter is used to obtain the user_id for tracking and data collection purposes.

- While the 'surveyid' parameter is required in the URL, it is not actually used by the application. Instead, the survey ID is hardcoded in the config file.

## Endpoints
- `/`: Index page
- `/create_vector`: Page for creating budget allocation
- `/survey`: Main survey page
- `/thank_you`: Thank you page after survey completion

## Database
The application uses a MySQL database. Here's the schema:

![Database Schema](docs/db_schema_diagram.png)

## Modifying the Survey

### Changing the Active Survey
To modify the survey that users will get, you need to manually update the `SURVEY_ID` value in the `config.py` file. Look for the following line and change the number to the desired survey ID:

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

## Development
- Use the provided `.pre-commit-config.yaml` for code formatting and linting
- Run tests using `pytest`
- Logs are stored in the `logs` directory
