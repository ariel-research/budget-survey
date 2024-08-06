# Budget Survey

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

## Usage Example
```python
from generate_examples import generate_user_example

user_vector = (10, 20, 70)
generate_user_example(user_vector, n=15, save_txt=True)
```