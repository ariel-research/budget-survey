# Budget Survey Application

A research tool for collecting data on budget allocation preferences using multiple algorithmic strategies. Users create ideal budget allocations, then compare pairs of alternatives to understand decision-making patterns.

**🚀 [Try it live](https://survey.csariel.xyz)**

---

**Documentation:**
- See the `docs/threshold_detection_research/` directory for research papers and supporting materials related to threshold detection and survey methodology.

---

## Quick Start

### Just want to run it?
```bash
git clone https://github.com/ariel-research/budget-survey
cd budget-survey
./scripts/deploy.sh dev
```
→ Open http://localhost:5000

### Just want to understand it?
1. **Users allocate** a 100-unit budget across subjects (e.g., Health: 60, Education: 25, Defense: 15)
2. **System generates** 10 comparison pairs using research algorithms 
3. **Users choose** their preference from each pair
4. **Data reveals** decision-making patterns and algorithmic preferences

---

## Table of Contents

### 👋 Getting Started
- [What's This?](#whats-this)
- [Prerequisites](#prerequisites)
- [Installation](#installation)

### 🚀 Running & Using
- [Running the Application](#running-the-application)
- [Common Commands](#common-commands)
- [Endpoints](#endpoints)
- [Live Application Endpoints](#live-application-endpoints)

### 🔬 For Researchers
- [Modifying the Survey](#modifying-the-survey)
- [Analysis](#analysis)
- [Algorithm](#algorithm)

### 🛠 For Developers
- [Features](#features)
- [Database](#database)
- [Docker Guide](#docker-guide)
- [Testing](#testing)
- [Development](#development)

---

## What's This?

This is a **research application** for studying budget allocation preferences. It's designed for academic research into algorithmic decision-making and preference revelation.

**The Process:**
1. 📝 **Budget Creation**: Users allocate 100 units across subjects (e.g., government ministries)
2. 🔄 **Pair Generation**: System creates comparison pairs using one of 9 research strategies
3. 🎯 **Preference Collection**: Users choose between alternatives in each pair
4. 📊 **Analysis**: Data reveals patterns in decision-making and strategy effectiveness

**Key Features:**
- 9 research-validated pair generation strategies
- Hebrew/English bilingual support with RTL/LTR layouts  
- Quality control via attention checks and user blacklisting
- Comprehensive analysis and PDF report generation
- Production-ready Docker deployment

**Use Cases:**
- Academic research on preference revelation
- Policy research on budget allocation
- Algorithm testing and validation
- User experience studies

## Prerequisites

### Local Development
- Python 3.8+
- MySQL 8.0+
- pip
- virtualenv

### Docker Development (Recommended)
- Docker 20.10+
- Docker Compose 2.0+
- Git

## Installation

### Local Development

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

### Docker Development

1. Clone the repository:
   ```bash
   git clone https://github.com/ariel-research/budget-survey
   cd budget-survey
   ```

2. Copy environment file and configure:
   ```bash
   cp .env.example .env
   # Edit .env with your preferred settings
   ```

3. Start the development environment:
   ```bash
   # Using deployment script (Recommended)
   ./scripts/deploy.sh dev

   # Or manual command (use 'docker compose' for v2 or 'docker-compose' for v1)
   docker compose -f docker-compose.dev.yml up -d
   ```

4. Access the application at: http://localhost:5000

## Running the Application

1. Activate the virtual environment (if not already activated)

2. Run the Flask application using either of these commands:
   ```
   python app.py
   ```
   This will run the application on port 5001.

   or
   ```
   flask run
   ```
   This will run the application on port 5000.

3. Access the application based on the command used:
   - If using `python app.py`: http://localhost:5001
   - If using `flask run`: http://localhost:5000

## Common Commands

```bash
# Development
./scripts/deploy.sh dev                              # Start everything (recommended)
docker compose -f docker-compose.dev.yml logs -f app # View application logs
docker compose -f docker-compose.dev.yml exec app bash # Access application shell
docker compose -f docker-compose.dev.yml down       # Stop everything

# Analysis & Reports
python -m analysis.survey_analysis                  # Run survey analysis
python -m analysis.survey_report_generator_pdf      # Generate PDF report  
open https://survey.csariel.xyz/report              # View live report

# Testing
pytest                                               # Run all tests
pytest tests/services/                               # Test strategies
pytest tests/analysis/                               # Test analysis
pytest tests/api/                                    # Test endpoints

# Configuration
SURVEY_ID = 4                                        # Change active survey (edit config.py)
curl http://localhost:5001/health                    # Check application health
docker compose -f docker-compose.dev.yml ps         # View application status
```

## Features

### Automatic Budget Rescaling
The application includes an automatic rescaling feature that helps users create valid budget allocations:

- **Purpose**: Helps users adjust their budget allocations to:
  - Sum to exactly 100
  - Ensure all numbers are divisible by 5
  - Maintain relative proportions between departments

- **How it works**:
  1. Proportionally adjusts non-zero values to sum to 100
  2. Rounds each value to the nearest multiple of 5
  3. Makes final adjustments to ensure the total remains exactly 100
  4. Maintains a minimum value of 5 for any non-zero allocation
  5. Preserves zero allocations (does not rescale them)

- **Button States**:
  The "Rescale" button becomes disabled when:
  - The total sum is already exactly 100
  - All values are zero
  - Any input contains invalid numbers
  - The total is zero

- **Constraints**:
  - Requires at least two departments with non-zero allocations
  - Maintains relative proportions between original values as closely as possible while satisfying the constraints

Users can trigger rescaling at any time using the "Rescale" button in the budget allocation interface.

### Pair Generation Strategies

The application uses the Strategy pattern to support multiple pair generation algorithms. Each survey can be configured with its own pair generation strategy.

#### Available Strategies

1. **L1 vs. Leontief Comparison**
   - Strategy name: `l1_vs_leontief_comparison`
   - Generates pairs that force users to choose between minimizing sum of differences and maximizing minimal ratio
   - Each pair contains two non-ideal allocations where one is better in terms of sum of differences while the other is better in terms of minimal ratio
   - Parameters:
     - `num_pairs`: Number of pairs to generate (default: 10)
   - Example:
     ```python
     # User's ideal: (60, 20, 20)
     # Option 1: (40, 30, 30)  Better minimal ratio (0.67) but worse sum of differences (40)
     # Option 2: (70, 15, 15)  Better sum of differences (20) but worse minimal ratio (0.75)
     ```

2. **Single-Peaked Preference Test**
   - Strategy name: `single_peaked_preference_test`
   - Generates pairs by combining user's ideal vector with random vectors using weighted averages
   - Each pair contains:
     - A random vector different from user's ideal allocation
     - A weighted combination of the random vector and user's ideal allocation
   - Weighting pattern:
     - Starts with 10% user vector, 90% random vector
     - Gradually increases user vector weight by 10% each round
     - Includes two pairs at 50-50 weight
     - Ends with 100% user vector weight
   - Parameters:
     - `num_pairs`: Number of pairs to generate (default: 10)
   - Example:
     ```python
     # For user_vector = [20, 30, 50]:
     # Round 1: x=0.1, y=0.9
     # - Random vector: [40, 40, 20]
     # - Weighted result: [38, 39, 23] (40*0.9 + 20*0.1, 40*0.9 + 30*0.1, 20*0.9 + 50*0.1)
     ```

3. **Single-Peaked Preference Test (Rounded)**
   - Strategy name: `single_peaked_preference_test_rounded`
   - Extends the Weighted Vector Strategy to ensure all allocations are multiples of 5
   - Each pair contains:
     - A random vector different from user's ideal allocation (in multiples of 5)
     - A weighted combination rounded to multiples of 5
   - Maintains all weighting patterns from the parent strategy
   - Parameters:
     - `num_pairs`: Number of pairs to generate (default: 10)
   - Example:
     ```python
     # For user_vector = [60, 25, 15]:
     # With x_weight = 0.3:
     # - Random vector: [30, 45, 25]
     # - Before rounding: [39, 39, 22] (30*0.7 + 60*0.3, 45*0.7 + 25*0.3, 25*0.7 + 15*0.3)
     # - After rounding to multiples of 5: [40, 40, 20]
     ```

4. **L1 vs. L2 Comparison**
   - Strategy name: `l1_vs_l2_comparison`
   - Compares root of sum of squared differences vs regular sum of differences
   - Each pair contains two non-ideal allocations where one is better in terms of root sum squared differences while the other is better in terms of regular sum of differences
   - Parameters:
     - `num_pairs`: Number of pairs to generate (default: 10)
   - Example:
     ```python
     # User's ideal: (50, 25, 25)
     # Option 1: (25, 70, 5)  Better root sum squared (55.23) but worse sum differences (90)
     # Option 2: (10, 25, 65)  Better sum differences (80) but worse root sum squared (56.57)
     ```

5. **L2 vs. Leontief Comparison**
   - Strategy name: `l2_vs_leontief_comparison`
   - Compares root of sum of squared differences vs minimal ratio
   - Each pair contains two non-ideal allocations where one is better in terms of root sum squared differences while the other is better in terms of minimal ratio
   - Parameters:
     - `num_pairs`: Number of pairs to generate (default: 10)
   - Example:
     ```python
     # User's ideal: (60, 25, 15)
     # Option 1: (50, 30, 20)  Better minimal ratio (0.83) but worse root sum squared (12.25)
     # Option 2: (65, 25, 10)  Better root sum squared (7.07) but worse minimal ratio (0.67)
     ```

6. **Peak-Linearity Test**
   - Strategy name: `peak_linearity_test`
   - Tests user preferences between extreme allocations and their weighted combinations with the ideal vector
   - Generates two types of pairs:
     - Extreme vector pairs: Each extreme vector allocates 100% to one department
     - Weighted average pairs: Combines user's ideal vector with extreme vectors using weights of 25%, 50%, and 75%
   - Parameters:
     - `num_pairs`: Number of pairs to generate (default: 9)
   - Example:
     ```python
     # For vector_size=3 and user_vector = [70, 20, 10]:
     
     # Extreme pairs:
     # [100, 0, 0] vs [0, 100, 0]
     # [100, 0, 0] vs [0, 0, 100]
     # [0, 100, 0] vs [0, 0, 100]
     
     # Weighted average pairs (50% weight):
     # [85, 10, 5] vs [35, 60, 5] (weighted averages with [100,0,0] and [0,100,0])
     ```
   - Purpose: Tests the hypothesis that if a user prefers extreme vector A over extreme vector B, they will also prefer weighted averages that incorporate extreme vector A over those with extreme vector B

   - **Analysis Features**:
     - Core Preference Analysis: Shows the user's fundamental preferences between extreme vectors (A vs B, A vs C, B vs C)
     - Percentile Breakdown Table: Displays consistency metrics for different weight percentiles (25%, 50%, 75%)
       - Shows how well user choices align with their core preferences at different weight levels
       - Helps identify if consistency varies with the "extremeness" of the choices
       - Provides separate consistency scores for each comparison group (A vs B, A vs C, B vs C)
       - Includes an "All Percentiles" summary row with overall consistency metrics

#### Transitivity Analysis

For peak_linearity_test surveys, the system analyzes logical consistency:

- **Groups analyzed**: Core vectors, 25%, 50%, 75% weighted
- **Transitivity check**: If A>B and B>C, then A>C must hold
- **Metrics**:
  - Preference order per group (e.g., A>B>C)
  - Transitivity status (✓/✗)
  - Overall transitivity rate (0-100%)
  - Order Consistency score (consistency of order across groups)

Note: '>' represents observed choice, which may include cases of user indifference.

7. **Component Symmetry Test**
   - Strategy name: `component_symmetry_test`
   - Generates 12 comparison pairs organized into 4 groups using cyclic shifts of difference vectors
   - **Algorithm Overview**:
     - Creates 4 groups of 3 pairs each (total 12 pairs)
     - Each group starts with two independent random difference vectors that sum to zero
     - Applies cyclic shifts (0, 1, 2 positions) to these difference vectors
     - Adds the shifted differences to the user's ideal vector to create comparison options
   - **Difference Vector Generation**:
     - Generates two independent random difference vectors
     - Both vectors sum to zero to maintain budget constraints
     - Ensures vectors are canonically different (sorted patterns differ)
     - Each vector must have at least one meaningful difference (|diff| >= 5)
     - Validates that resulting budget allocations remain within [0, 100] range
   - **Validation Improvements**:
     - Uses absolute canonical form validation to prevent degenerate pairs
     - Ensures difference vectors are not absolute canonical identical
     - Maintains research validity by avoiding equivalent patterns
     - Guarantees perfect mathematical relationships without rounding approximations
   - **Cyclic Shift Logic**:
     - Applies right shifts of 0, 1, and 2 positions to create 3 pairs per group
     - Each shift moves difference elements to the right by the specified positions
     - Elements that exceed array bounds wrap around to the beginning
   - **Special Handling**:
     - Automatically detects when user's ideal allocation contains zero values
     - Throws `UnsuitableForStrategyError` if zeros are present, as cyclic shifts could create invalid budget allocations
     - Ensures all generated allocations maintain valid budget constraints
     - Applies multiples-of-5 rounding when appropriate
   - Parameters:
     - `num_pairs`: Number of pairs to generate (default: 12, always generates exactly 12)
   - Example:
     ```python
     # For user_vector = [20, 30, 50]:
     
     # Group 1 - Generate two independent difference vectors:
     # diff1 = [-10, +5, +5], diff2 = [+20, -25, +5]
     
     # Pair 1 (shift 0): Apply differences directly
     # Option A: [20, 30, 50] + [-10, +5, +5] = [10, 35, 55]
     # Option B: [20, 30, 50] + [+20, -25, +5] = [40, 5, 55]
     
     # Pair 2 (shift 1): Shift differences right by 1 position
     # diff1_shifted = [+5, -10, +5], diff2_shifted = [+5, +20, -25]
     # Option A: [20, 30, 50] + [+5, -10, +5] = [25, 20, 55]
     # Option B: [20, 30, 50] + [+5, +20, -25] = [25, 50, 25]
     
     # Pair 3 (shift 2): Shift differences right by 2 positions
     # diff1_shifted = [+5, +5, -10], diff2_shifted = [-5, +15, +10]
     # Option A: [20, 30, 50] + [+5, +5, -10] = [25, 35, 40]
     # Option B: [20, 30, 50] + [-5, +15, +10] = [15, 45, 60]
     
     # Groups 2-4 repeat this process with different random difference vectors
     ```

8. **Sign Symmetry Test**
   - Strategy name: `sign_symmetry_test`
   - Generates 12 comparison pairs organized into 6 groups to test linear symmetry hypothesis
   - **Core Hypothesis**: Tests whether users treat positive and negative distances from their ideal allocation as equivalent
   - **Algorithm Overview**:
     - Creates 6 groups of 2 pairs each (total 12 pairs)
     - Each group generates two distance vectors v1 and v2 that sum to zero
     - Creates pair A: (ideal + v1) vs (ideal + v2)
     - Creates pair B: (ideal - v1) vs (ideal - v2)
   - **Distance Vector Generation**:
     - Generates two independent distance vectors that sum to zero
     - Neither vector can be all zeros
     - Vectors must be different from each other
     - Each vector must have at least one meaningful difference (|diff| >= 5)
     - Validates that both addition and subtraction produce valid budget allocations within [0, 100]
   - **Validation Improvements**:
     - Uses absolute canonical form validation to prevent degenerate pairs
     - Ensures distance vectors are not absolute canonical identical
     - Maintains research validity by avoiding equivalent patterns
     - Guarantees perfect mathematical symmetry without rounding approximations
   - **Linear Symmetry Logic**:
     - Tests if users view distance D and distance -D as equivalent
     - If symmetry hypothesis holds, users should show similar preference patterns for both pairs in each group
     - Positive distances (ideal + v) represent movement in one direction from ideal
     - Negative distances (ideal - v) represent movement in opposite direction
   - **Special Handling**:
     - Automatically detects when user's ideal allocation contains zero values
     - Throws `UnsuitableForStrategyError` if zeros are present, as distance calculations could create invalid budget allocations
     - Ensures all generated allocations maintain valid budget constraints
     - Applies multiples-of-5 rounding when appropriate
   - Parameters:
     - `num_pairs`: Number of pairs to generate (default: 12, always generates exactly 12)
   - Example:
     ```python
     # For user_vector = [40, 30, 30]:
     # v1 = [15, -10, -5], v2 = [-10, 5, 5]
     
     # Group 1:
     # Pair A (positive distances): [55, 20, 25] vs [30, 35, 35]  (ideal + v1 vs ideal + v2)
     # Pair B (negative distances): [25, 40, 35] vs [50, 25, 25]  (ideal - v1 vs ideal - v2)
     
     # Groups 2-6 repeat this process with different distance vectors
     ```
   - **Analysis Features**:
     - Linear Consistency Analysis: Measures how consistently users treat positive and negative distances
     - Group-level consistency metrics showing symmetry adherence
     - Helps identify if users have directional biases in budget allocation preferences

9. **Asymmetric Loss Distribution Strategy**
   - Strategy name: `asymmetric_loss_distribution`
   - Tests user preferences between concentrated vs. distributed budget changes using a calibrated-magnitude approach.
   - **Algorithm Overview**:
     - Generates 12 pairs based on a "calibrated-magnitude" approach.
     - `base_unit = max(1, round(min(ideal_budget) / 10))`
     - Four magnitude levels are tested for each of the 3 budget categories.
   - **Comparison Types**:
     - **Type A (Primary)**: Concentrated loss vs. Distributed loss.
     - **Type B (Fallback)**: Concentrated funding vs. Distributed funding.
   - **Special Handling**:
     - Throws `UnsuitableForStrategyError` if the user's ideal budget contains any zero values.
   - **Analysis Features**:
     - Preference Consistency: Measures overall preference for distributed vs. concentrated changes.
     - Magnitude Sensitivity: Analyzes how the magnitude of the change affects user preferences.
     - Type A vs. Type B Patterns: Compares user choices in the primary test vs. the fallback scenario.

10. **Preference Ranking Survey Strategy**
    - Strategy name: `preference_ranking_survey`
    - Tests user preference order through forced-ranking methodology instead of pairwise comparisons
    - **Algorithm Overview**:
      - Generates 4 forced-ranking questions (5 questions including 1 awareness check at position 3)
      - Each question presents 3 budget options that users rank from most to least preferred
      - Converts rankings to 12 comparison pairs for analysis (4 questions × 3 pairs each)
      - Uses two magnitude levels: X1 = max(1, round(0.2 × min(user_vector))), X2 = max(1, round(0.4 × min(user_vector)))
    - **Question Generation**:
      - Creates base difference vectors: Positive (+2X, -X, -X) and Negative (-2X, +X, +X)
      - Generates 3 options per question using base vector and 2 cyclic shifts
      - 4 questions test: X1_positive, X1_negative, X2_positive, X2_negative
    - **Special Handling**:
      - Ranking-based interface: Users rank 3 options instead of choosing between 2
      - Includes awareness check at position 3 where user's ideal allocation is Option B
      - Throws `UnsuitableForStrategyError` if user's ideal budget contains any zero values
      - Only supports 3-subject budget allocations (vector_size=3)
    - Parameters:
      - `num_pairs`: Number of pairs to generate (default: 12, always generates exactly 12)
    - Example:
      ```python
      # For user_vector = [60, 25, 15]:
      # X1 = max(1, round(0.2 × 15)) = 3, X2 = max(1, round(0.4 × 15)) = 6
      
      # Question 1 (X1_positive): base_diff = [6, -3, -3]
      # Option A: [60, 25, 15] + [6, -3, -3] = [66, 22, 12]
      # Option B: [60, 25, 15] + [-3, 6, -3] = [57, 31, 12] (shift 1)
      # Option C: [60, 25, 15] + [-3, -3, 6] = [57, 22, 21] (shift 2)
      # User ranks: A > B > C (creates 3 pairs: A vs B, A vs C, B vs C)
      ```
    - **Core Hypothesis**: User's underlying preference order will be consistently revealed across all ranking questions, providing insights into stable budget allocation priorities

11. **Temporal Preference Test**
    - Strategy name: `temporal_preference_test`
    - Tests temporal discounting hypothesis: users prefer receiving their ideal budget allocation this year over receiving it next year
    - **Algorithm Overview**:
      - Generates 10 pairs comparing user's ideal vector against random vectors
    - **Core Hypothesis**: Users exhibit temporal discounting by preferring their ideal allocation sooner rather than later
    - **Analysis Features**:
      - Temporal Preference Summary: Shows percentage of "Ideal This Year" vs "Ideal Next Year" choices
      - Consistency Analysis: Measures how consistently users choose immediate vs delayed preferences
    - Parameters:
      - `num_pairs`: Number of pairs to generate (default: 10)
    - Example:
      ```python
      # For user_vector = [60, 30, 10]:
      # Pair 1: [60, 30, 10] vs [45, 25, 30]  (ideal vs random)
      # Pair 2: [60, 30, 10] vs [20, 50, 30]  (ideal vs random)
      # ...10 pairs total
      # User choosing Option 1 implies preference for (ideal_now, random_later)
      # User choosing Option 2 implies preference for (random_now, ideal_later)
      ```

#### Adding New Strategies

To add a new pair generation strategy:

1. Create a new file in `application/services/pair_generation/` (e.g., `new_strategy.py`):
```python
from application.services.pair_generation.base import PairGenerationStrategy

class NewStrategy(PairGenerationStrategy):
    def generate_pairs(self, user_vector: tuple, n: int, vector_size: int):
        # Implement your pair generation logic here
        pass
        
    def get_strategy_name(self):
        return "new_strategy_name"
        
    def get_option_labels(self):
        return ("Option Type A", "Option Type B")
        
    def get_table_columns(self):
        """Define custom column definitions for response tables"""
        return {
            "column1": {
                "name": "First Metric", 
                "type": "percentage",
                "highlight": True
            },
            "column2": {
                "name": "Second Metric", 
                "type": "percentage",
                "highlight": True
            }
        }
```

2. Register the strategy in `application/services/pair_generation/__init__.py`:
```python
from .new_strategy import NewStrategy
StrategyRegistry.register(NewStrategy)
```

Each strategy can define its own table columns for displaying survey response statistics by implementing the `get_table_columns()` method. This allows the system to dynamically generate strategy-specific tables based on the strategy used for each survey.

For examples of how to configure surveys to use different strategies, see the [Adding or Modifying Surveys](#adding-or-modifying-surveys) section.

### Language Support
The application provides comprehensive bilingual support:

- **Available Languages**:
  - Hebrew (default)
  - English

- **Key Features**:
  - Language switcher in the UI header
  - Automatic RTL layout for Hebrew
  - LTR layout for English
  - Language preference persistence across sessions
  - Fallback to Hebrew for missing translations

- **Translation Coverage**:
  - User interface elements
  - Error messages
  - Survey questions and instructions
  - Survey subjects (e.g., ministry names)
  - System messages and alerts
  - Button labels and tooltips
  - Form validations
  - Success/failure notifications

- **How to Switch Languages**:
  - Via UI: Click the language toggle in the top-right corner
  - Via URL: Add 'lang' parameter to the URL
    - For Hebrew: `?lang=he`
    - For English: `?lang=en`
    - Example: `https://survey.csariel.xyz/?userID=abc&surveyID=123&lang=en`
  - Selection is remembered for future visits
  - Can be changed at any point during the survey

All translations are managed through the translations system, making it easy to maintain and update content in both languages.

### Attention Check Handling
The application includes an attention check mechanism to ensure survey quality:

- **Purpose**: Validate user attention during survey completion
- **Implementation**:
  - Two attention check questions mixed within comparison pairs
  - Validates that users recognize their own optimal allocation
  - Failed checks are recorded and do not allow retries

- **Panel4All Integration**:
  - Sends "attentionfilter" status for failed attention checks
  - Sends "finish" status for successful completions
  - Allows proper handling by survey management system

- **Data Storage**:
  - Failed checks are stored with `attention_check_failed` flag
  - Maintains data for analysis while excluding from main results
  - Supports research on survey response quality

### User Blacklist
The application includes a user blacklist feature to automatically enforce quality control in survey responses.

- **Purpose**: Enhance data quality by preventing participation from users who fail to meet attention standards
- **Implementation**:
  - Users who fail attention checks are automatically blacklisted from taking future surveys
  - Blacklist status is checked during survey eligibility verification
  - Blacklisted users are redirected to a dedicated explanation page
  - System records which survey triggered the blacklist

- **Data Storage**:
  - Blacklist information is stored in the users table:
    - `blacklisted` flag indicates blacklist status
    - `blacklisted_at` records when user was blacklisted
    - `failed_survey_id` identifies which survey triggered the blacklist
  - Indexed for efficient lookups during eligibility checks


### Demo Mode
The application includes a 'Demo Mode' feature that allows users to explore the survey functionality without affecting the actual data.

- **Purpose**: Provides a sandbox environment for users to familiarize themselves with the survey process.
- **How it works**:
  1. Users can enable 'Demo Mode'.
  2. In 'Demo Mode', all interactions are simulated, and no data is stored permanently.
  3. Users can navigate through the survey, make allocations, and submit responses as they would in a real survey.
  4. The system provides feedback and results based on the simulated data.

- **Limitations**:
  - Data generated in 'Demo Mode' is not saved to the database.
  - Some features may be restricted to prevent misuse.

This feature is ideal for training sessions and demonstrations, allowing users to experience the full functionality of the application without impacting real survey data.

### User Participation Overview
The application provides a comprehensive dashboard showing participation statistics for all users who have completed surveys.

- **Purpose**: Monitor user engagement and survey completion patterns
- **Key Features**:
  - Shows successful and failed survey counts per user
  - Color-coded clickable survey IDs (green for successful, red for failed)
  - Sortable by User ID or Last Activity
  - Accessible via dashboard metric card or direct URL: `/surveys/users`
  - Full bilingual support with RTL/LTR layouts
  - Navigation to Performance Matrix for detailed metrics

- **Data Displayed**: User IDs, survey counts, last activity timestamps, and direct links to individual responses

### User-Survey Performance Matrix
The application provides a detailed matrix view showing strategy-specific performance metrics for each user-survey combination.

- **Purpose**: Analyze user performance patterns across different survey strategies
- **Key Features**:
  - Matrix format with users as rows and surveys as columns
  - Strategy-specific metric labels (e.g., "Random / Weighted Average", "Sum / Ratio")
  - Sticky User ID column for easy navigation
  - Full bilingual support with RTL/LTR layouts
  - Accessible via direct URL: `/surveys/users/matrix`

- **Data Displayed**: Performance metrics for each user-survey combination, with "-" indicating no participation

## Database

The application uses a MySQL database with multilingual support. Here's the schema:

![Database Schema](docs/db_schema_diagram.png)

### Database Setup

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

4. Run the SQL commands from the database/schema.sql file to create the necessary tables and structure:


  ```
  
  ```

### Method 2: Using Docker Compose

1. Ensure you have Docker and Docker Compose installed on your system.

2. Navigate to the project root directory.

3. Start the database using the development environment:

   ```bash
   # Start full development environment (recommended)
   ./scripts/deploy.sh dev
   
   # Or just the database
   docker compose -f docker-compose.dev.yml up -d db
   ```

This will create a MySQL container, create the database, and run the initialization script (`database/schema.sql`) to set up the necessary tables and structure.

Note: Make sure your .env file is properly configured with the correct database connection details before running either method.

## Docker Guide

> **Note**: This guide uses `docker compose` (v2) syntax. If you have the older standalone `docker-compose` (v1), replace `docker compose` with `docker-compose` in the commands below. The deployment script automatically detects and uses the correct version.

### Development Setup

1. **Copy environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Start development environment:**
   ```bash
   ./scripts/deploy.sh dev
   ```

3. **Common development commands:**
   ```bash
   # View logs
   docker compose -f docker-compose.dev.yml logs -f app

   # Run tests
   docker compose -f docker-compose.dev.yml exec app pytest

   # Access shell
   docker compose -f docker-compose.dev.yml exec app bash

   # Stop
   docker compose -f docker-compose.dev.yml down
   ```

### Production Deployment (AWS EC2)

**Prerequisites:**
- Ubuntu 20.04+ EC2 instance
- Domain name
- Docker installed

**Installation:**
```bash
# Install Docker on EC2
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose v2 (recommended)
# Docker Compose v2 comes built-in with Docker Desktop
# For Ubuntu/Debian server installations:
sudo apt-get install docker-compose-plugin
sudo reboot
```

**Deployment:**
```bash
# Clone and configure
git clone https://github.com/ariel-research/budget-survey
cd budget-survey
cp .env.example .env

# Edit .env with production settings:
# FLASK_ENV=production
# FLASK_SECRET_KEY=your-secret-key
# MYSQL_PASSWORD=secure-password
# SURVEY_BASE_URL=https://your-domain.com

# Setup SSL
sudo apt install certbot
sudo certbot certonly --standalone -d your-domain.com
mkdir -p ssl
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ssl/cert.pem
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem ssl/key.pem
sudo chown $USER:$USER ssl/*

# Deploy
./scripts/deploy.sh prod
```

**Management:**
```bash
# Update application
git pull && docker compose -f docker-compose.prod.yml up -d --build

# View logs
docker compose -f docker-compose.prod.yml logs -f

# Backup database
docker compose -f docker-compose.prod.yml exec db mysqldump -u root -p survey > backup.sql
```

### Environment Configuration

Create `.env` file with these required variables:

```bash
# Application
FLASK_ENV=development|production
FLASK_SECRET_KEY=your-secret-key
APP_PORT=5001

# Database
MYSQL_HOST=db  # Use 'db' for Docker, 'localhost' for local
MYSQL_DATABASE=survey
MYSQL_USER=survey_user
MYSQL_PASSWORD=secure_password

# Survey
SURVEY_BASE_URL=http://localhost:5001|https://your-domain.com
```

### Troubleshooting

**Common issues:**

```bash
# Container won't start
docker compose logs [service_name]

# Database connection issues
docker compose logs db
docker compose restart db

# Port already in use
sudo lsof -i :5001
# Change APP_PORT in .env

# Permission issues
sudo chown -R $USER:$USER .
```

**Health check:**
```bash
curl http://localhost:5001/health
```

## Endpoints

### Main Routes
1. Dashboard (Main Landing Page)
   - `/` - Analytics dashboard (Main landing page)
   
2. Survey Taking
   - `/take-survey/?userID=...&surveyID=...` - Take survey (with default survey ID)
   - `/take-survey/?userID=...&surveyID=...&internalID=N` - Take survey with specific internal ID
   - `/take-survey/create_vector` - Create budget allocation
   - `/take-survey/survey` - Compare budget pairs
   - `/take-survey/thank_you` - Survey completion page
   - `/take-survey/?userID=...&surveyID=...&demo=true` - Take survey in Demo Mode

3. Analysis & Reports
   - `/report` - View survey analysis report (PDF)
     * Automatically refreshes based on latest data
     * Updates CSVs and PDF as needed
     * Shows PDF in browser with download option
   - `/dev/report` - Development report for testing
     * Always generates fresh report
     * Useful for testing template changes
     * Creates 'survey_analysis_report_dev.pdf'

4. Survey Results
   - `/surveys/responses` - All survey responses
   - `/surveys/{survey_id}/responses` - Responses for specific survey
     * With filtering: `/surveys/{survey_id}/responses?view_filter=v_users_preferring_weighted_vectors`
     * Other filters: `v_users_preferring_rounded_weighted_vectors`, `v_users_preferring_any_weighted_vectors`
   - `/surveys/users` - User Participation Overview
     * Sortable by User ID or Last Activity
     * Shows successful/failed survey counts per user
     * Color-coded clickable survey IDs
   - `/surveys/users/matrix` - User-Survey Performance Matrix
     * Shows strategy-specific metrics for each user-survey combination
     * Displays performance data across all surveys in a matrix format
   - `/surveys/users/{user_id}/responses` - All responses from specific user
   - `/surveys/{survey_id}/users/{user_id}/responses` - User's response to specific survey
   - `/surveys/comments` - All user comments
   - `/surveys/{survey_id}/comments` - Comments for specific survey

### API Endpoints
- `/get_messages` - Returns JSON dictionary of error messages

Notes: 
- For survey taking endpoints, both 'userID' and 'surveyID' parameters are required
- The 'surveyID' parameter in the URL is required but not used internally
- The survey ID is determined by either:
  1. Custom internal survey ID via `internalID` parameter
  2. Default survey ID from config file

## Live Application Endpoints

1. Dashboard
   - Dashboard (Main landing page): https://survey.csariel.xyz/

2. Survey Taking
   - Default survey: <https://survey.csariel.xyz/take-survey/?userID=...&surveyID=...>
   - Custom survey: <https://survey.csariel.xyz/take-survey/?userID=...&surveyID=...&internalID=N>
   - Demo mode: <https://survey.csariel.xyz/take-survey/?userID=...&surveyID=...&demo=true>

3. Analysis & Reports
   - Survey Report: https://survey.csariel.xyz/report
   - Development Report: https://survey.csariel.xyz/dev/report

4. Survey Results
   - All Responses: https://survey.csariel.xyz/surveys/responses
   - Survey Responses: https://survey.csariel.xyz/surveys/{survey_id}/responses
     * With filtering: https://survey.csariel.xyz/surveys/{survey_id}/responses?view_filter=v_users_preferring_weighted_vectors
     * Other filters: v_users_preferring_rounded_weighted_vectors, v_users_preferring_any_weighted_vectors
   - User Participation Overview: https://survey.csariel.xyz/surveys/users
     * Sortable by User ID or Last Activity
     * Shows successful/failed survey counts per user
     * Color-coded clickable survey IDs
   - User-Survey Performance Matrix: https://survey.csariel.xyz/surveys/users/matrix
     * Shows strategy-specific metrics for each user-survey combination
     * Displays performance data across all surveys in a matrix format
   - User Responses: https://survey.csariel.xyz/surveys/users/{user_id}/responses
   - User Survey Response: https://survey.csariel.xyz/surveys/{survey_id}/users/{user_id}/responses
   - All Comments: https://survey.csariel.xyz/surveys/comments
   - Survey Comments: https://survey.csariel.xyz/surveys/{survey_id}/comments

Notes:
- URL parameters required for survey taking:
  * userID: Required for user identification
  * surveyID: Required but not used internally
  * internalID: Optional, overrides default survey ID from config

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

   First, add a new story (if needed):
   ```sql
   INSERT INTO stories (
       code,
       title,
       description,
       subjects
   )
   VALUES (
       'budget_2024',
       JSON_OBJECT(
           'he', 'סקר תקציב 2024',
           'en', 'Budget Survey 2024'
       ),
       JSON_OBJECT(
           'he', 'סקר שנתי להקצאת תקציב',
           'en', 'Annual budget allocation survey'
       ),
       JSON_ARRAY(
           JSON_OBJECT('he', 'בריאות', 'en', 'Health'),
           JSON_OBJECT('he', 'חינוך', 'en', 'Education'),
           JSON_OBJECT('he', 'ביטחון', 'en', 'Defense')
       )
   );
   ```

   Then, add a new survey that uses this story:
   ```sql
   INSERT INTO surveys (
       story_code,
       active,
       pair_generation_config
   )
   VALUES (
       'budget_2024',
       TRUE,
       JSON_OBJECT(
           'strategy', 'temporal_preference_test',
           'params', JSON_OBJECT('num_pairs', 10),
           'pair_instructions', JSON_OBJECT(
               'he', 'עליכם לקבוע את התקציב עבור שתי שנים עוקבות: השנה הנוכחית, והשנה הבאה. איזה מבין שני התקציבים הבאים תעדיפו שיהיה התקציב בשנה הנוכחית? התקציב שלא תבחרו יהיה התקציב בשנה הבאה.',
               'en', 'You need to set the budget for two consecutive years: the current year and next year. Which of the following two budgets would you prefer to be the current year''s budget? The budget you don''t choose will be next year''s budget.'
           )
       )
   );
   ```

   Modify an existing story's content:
   ```sql
   UPDATE stories
   SET title = JSON_OBJECT(
           'he', 'סקר תקציב מעודכן 2024',
           'en', 'Updated Budget Survey 2024'
       ),
       description = JSON_OBJECT(
           'he', 'סקר שנתי מעודכן להקצאת תקציב',
           'en', 'Revised annual budget allocation survey'
       ),
       subjects = JSON_ARRAY(
           JSON_OBJECT('he', 'בריאות', 'en', 'Health'),
           JSON_OBJECT('he', 'חינוך', 'en', 'Education'),
           JSON_OBJECT('he', 'ביטחון', 'en', 'Defense')
       )
   WHERE code = 'budget_2024';
   ```

   Update just the pair generation strategy for a survey:
   ```sql
   UPDATE surveys
   SET pair_generation_config = JSON_OBJECT(
       'strategy', 'l1_vs_leontief_comparison',
       'params', JSON_OBJECT('num_pairs', 10)
   )
   WHERE id = 1;
   ```

   Deactivate a survey:
   ```sql
   UPDATE surveys
   SET active = FALSE
   WHERE id = 1;
   ```

Remember to:
- Use valid strategy names as defined in the pair generation strategies
- Include all required parameters for the chosen strategy
- Update the `SURVEY_ID` in `config.py` after adding or modifying surveys
- Ensure that story codes are unique across the stories table

### Customizing Pair Instructions

Surveys can include custom instructions for specific strategies. These instructions are stored in the `pair_instructions` field within the `pair_generation_config` JSON object and support both Hebrew and English languages. If no custom instructions are provided, the system will not display any instructions for that survey.

#### Adding Custom Instructions to a New Survey

```sql
INSERT INTO surveys (
    story_code,
    active,
    pair_generation_config
)
VALUES (
    'my_custom_survey',
    TRUE,
    JSON_OBJECT(
        'strategy', 'temporal_preference_test',
        'params', JSON_OBJECT('num_pairs', 10),
        'pair_instructions', JSON_OBJECT(
            'he', 'הוראות מותאמות אישית בעברית',
            'en', 'Custom personalized instructions in English'
        )
    )
);
```

#### Updating Instructions for Existing Surveys

```sql
UPDATE surveys
SET pair_generation_config = JSON_SET(
    pair_generation_config,
    '$.pair_instructions',
    JSON_OBJECT(
        'he', 'הוראות מעודכנות בעברית',
        'en', 'Updated instructions in English'
    )
)
WHERE id = 1;
```

#### Removing Custom Instructions

To fall back to no instructions being displayed:

```sql
UPDATE surveys
SET pair_generation_config = JSON_REMOVE(
    pair_generation_config,
    '$.pair_instructions'
)
WHERE id = 1;
```

**Note**: The `pair_instructions` field is optional. If omitted or set to `NULL`, no instructions will be displayed for that survey. This allows for flexible customization of the user experience.

### Changing Strategy Names and Colors

To change a strategy's name or color, you'll need to update both code and database references.

#### Changing a Strategy Name

1. **Update the Strategy Class**:
   - Open the strategy file in `application/services/pair_generation/` (e.g., `optimization_metrics_vector.py`)
   - Modify the `get_strategy_name()` method:
     ```python
     def get_strategy_name(self) -> str:
         """Get the unique identifier for this strategy."""
         return "new_strategy_name"  # Changed from original name
     ```

2. **Update the Database**:
   - Update all surveys using this strategy with this SQL query:
     ```sql
     UPDATE surveys 
     SET pair_generation_config = JSON_REPLACE(
         pair_generation_config, 
         '$.strategy', 
         'new_strategy_name'
     ) 
     WHERE id = 1;  # Replace with the survey ID
     ```
   - To update multiple surveys:
     ```sql
     UPDATE surveys 
     SET pair_generation_config = JSON_REPLACE(
         pair_generation_config, 
         '$.strategy', 
         'new_strategy_name'
     ) 
     WHERE id IN (1, 4, 6);  # List all affected survey IDs
     ```

#### Changing a Strategy Color

Strategy badge colors are defined in CSS:

1. Open `application/static/css/dashboard_style.css`
2. Find the Strategy Badge Colors section:
   ```css
   .strategy-badge[data-strategy="l1_vs_leontief_comparison"] { 
       background: var(--color-primary);
   }
   ```
3. Modify the color using predefined variables or custom colors:
   ```css
   /* Using predefined colors */
   .strategy-badge[data-strategy="new_strategy_name"] { 
       background: var(--color-purple);  /* Choose from available colors */
   }
   
   /* OR using custom HEX color */
   .strategy-badge[data-strategy="new_strategy_name"] { 
       background: #4A5568;  /* Custom gray color */
   }
   ```

4. Available color variables include:
   - `--color-primary` (Blue)
   - `--color-success` (Green)
   - `--color-purple` (Purple)
   - `--color-orange` (Orange)
   - `--color-teal` (Teal)
   - `--color-indigo` (Indigo)
   - `--color-rose` (Rose)
   - `--color-amber` (Amber)

### Modifying Awareness Questions

To modify the awareness check questions in the survey:

1. **Change the Question Text**:
   - Open `application/translations.py`
   - Locate and modify the awareness question text in both languages:
     ```python
     "awareness_question": {
         "he": "בחר באפשרות מספר 1. זוהי שאלת בדיקת תשומת לב.",
         "en": "Please select option 1. This is an attention check question.",
     },
     ```

2. **Change the Answer Options or Expected Answers**:
   - Open `application/services/awareness_check.py`
   - Modify the `generate_awareness_questions` function to change how options are created
   - Open `application/schemas/validators.py`
   - Update the validation logic in the `SurveySubmission.validate()` method:
     ```python
     # Change which answers are expected
     if (
         len(self.awareness_answers) != 2
         or self.awareness_answers[0] != 1  # First check must be 1
         or self.awareness_answers[1] != 2  # Second check must be 2
     ):
     ```

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

### Test Structure
```python
tests/
├── analysis/                     # Data analysis and reporting tests
│   ├── utils/
│   │   ├── test_analysis_utils.py
│   │   ├── test_file_utils.py
│   │   └── test_visualization_utils.py
│   ├── test_report_content_generators.py
│   ├── test_survey_analysis.py
│   └── test_survey_report_generator.py
├── api/                         # API endpoint tests
│   └── test_routes.py
├── database/                    # Database integration tests
│   └── test_database_integration.py
├── performance/                 # Load and performance tests
│   └── load_test.py
├── services/                    # Service layer tests
│   ├── pair_generation/             # Pair generation strategy tests
│   │   ├── test_cyclic_shift_strategy.py      # Comprehensive validation for all 171 valid vectors
│   │   ├── test_linear_symmetry_strategy.py   # Mathematical relationship verification
│   │   └── test_*.py            # Other strategy tests
│   └── test_survey_vector_generator.py
├── UI/                         # Frontend/UI tests
│   └── test_client_side.py
```

### Running Tests

#### Quick Start
Run all tests:
```bash
pytest
```

#### Automated Testing (CI/CD)
GitHub Actions automatically runs the full test suite on every push and pull request:
- ✅ Builds Docker containers with all dependencies
- ✅ Runs complete test suite across all categories
- ✅ Validates production build compatibility
- 📊 View results at: [Actions tab](../../actions)

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

##### Service Tests
**Description:** Core algorithms and pair generation strategies
```bash
pytest tests/services/
```

Key features:
- **Comprehensive validation**: Tests all 171 valid budget vectors for algorithmic completeness
- **Mathematical verification**: Ensures perfect cyclic shifts and linear symmetry relationships
- **Performance testing**: Validates sub-3-second generation times

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

### Development Setup & Workflow
- Use the provided `.pre-commit-config.yaml` for code formatting and linting
- Run tests using `pytest` before committing changes
- Database migrations are stored in `migrations/` directory
- Follow timestamp-based naming convention (e.g., `20250216_add_attention_check_column.sql`)

### Important Directories
- **Logs**: Stored in the `logs` directory
- **Data**: Analysis outputs stored in `data` directory  
- **Migrations**: Database changes in `migrations/` directory
- **Tests**: All tests in `tests/` with category-based organization

### Live Application Updates
To update the live application after code changes:
- Log into the server
- Inside the `app` folder: `git pull`
- Check service status: `sudo myservice status`
- Restart service: `sudo myservice restart`

### Screen Text Locations
To modify displayed text:
- **Translations**: `application/translations.py` (Hebrew/English)
- **Templates**: `templates/` directory with translation key usage
- **Dynamic content**: Loaded from database based on user language preference
