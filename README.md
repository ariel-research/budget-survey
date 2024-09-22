# Budget Survey

## Website

https://survey.csariel.xyz/thank_you

## Prerequisites

- python >= 3.8
- pip
- virtualenv 

## Installation

1. **Clone the repository and navigate to the project folder**:
    ```bash
    git clone https://github.com/ariel-research/budget-survey
    cd budget-survey
    ```

2. **Create a virtual environment and activate it**:
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```

3. **Install the required packages**:
    ```bash
    pip install -r requirements.txt
    ```

## Database Schema

Below is the image showing the tables and their relationships in the project:

![Database Schema](docs/db_schema_diagram.png)

## Usage Example
Open the python shell in the project folder and execute the following commands:

Here's the corrected and structured phrasing for your documentation:

### Generate Examples for a Specific User

```python
>>> from generate_examples import generate_user_example
>>> user_vector = (10, 20, 70)
>>> examples = generate_user_example(user_vector, plot=True, save_txt=True)
>>> print(examples)
```

### Generate Surveys for Multiple Users

```python
>>> from generate_random_survey import n_surveys
>>> surveys = n_surveys(2, html=True)
>>> print(surveys)
```