# Identity Asymmetry Strategy - High Level Design

## 1. Overview
The "Identity Asymmetry" strategy is an experimental condition designed to isolate "Project Identity Bias" from "Magnitude Bias". It tests whether users consistently prefer one subject over another when their starting budget allocations are mathematically identical.

## 2. Class Design

### 2.1. `IdentityAsymmetryStrategy`
*   **Inheritance**: `PairGenerationStrategy`
*   **File**: `application/services/pair_generation/identity_asymmetry_strategy.py`

#### Methods:
1.  `get_strategy_name() -> str`: Returns `"identity_asymmetry"`.
2.  `get_option_labels() -> Tuple[str, str]`: Returns labels for the options: `"favor_subject_index_{i}"` (generic key to be mapped to "Favor {Subject Name}").
3.  `generate_pairs(user_vector, n, vector_size) -> List[Dict]`:
    *   Validates vector suitability (helper method).
    *   Identifies the target pair (Subject A, Subject B) with equal values $\ge 10$.
    *   **Selection Rule**: If multiple equal pairs exist, pick the pair with the **largest value**. (e.g., for `[20, 20, 30, 30]`, pick the 30s).
    *   Calculates `step_size = value / 10`.
    *   Generates 10 pairs where magnitude scales from Step 1 to 10.
    *   Constructs metadata for analysis.

#### Helper Method: `_find_largest_equal_pair(vector)`
*   **Input**: User vector (tuple of ints).
*   **Logic**:
    *   Iterate through all unique pairs `(i, j)`.
    *   Identify pairs where `vector[i] == vector[j]` AND `vector[i] >= 10`.
    *   If no pairs found, raise `UnsuitableForStrategyError`.
    *   If multiple pairs found, select the one with the highest value.
    *   If tie in value, select the one with lowest indices (deterministic).
*   **Output**: Tuple `(index_a, index_b)` and `value`.

### 2.2. Validation Updates
*   **File**: `application/services/survey_service.py`
*   **Function**: `_validate_vector_suitability`
    *   Add check for `min_equal_value_pair` if strategy is `identity_asymmetry`.

## 3. Data Flow

### 3.1. Generation Phase (Refined)
1.  **Input**: User Vector `[30, 30, 40]`.
2.  **Selection**: Pair (0, 1) selected (Value 30).
3.  **Calculation (Math Integrity)**:
    *   `target_value` = 30.
    *   `step_size` = 3.0.
    *   For `i` from 1 to 10:
        *   `m_float = (target_value / 10.0) * i`
        *   `magnitude = max(1, int(round(m_float)))`
        *   **Option 1 (Favors B)**: A loses `magnitude`, B gains `magnitude`.
            *   `vec_1[a] = user_vector[a] - magnitude`
            *   `vec_1[b] = user_vector[b] + magnitude`
        *   **Option 2 (Favors A)**: B loses `magnitude`, A gains `magnitude`.
            *   `vec_2[a] = user_vector[a] + magnitude`
            *   `vec_2[b] = user_vector[b] - magnitude`
4.  **Metadata Construction**:
    ```json
    {
      "pair_type": "identity_test",
      "subject_a_idx": 0,  // The first subject in the equal pair
      "subject_b_idx": 1,  // The second subject in the equal pair
      "step_number": 1,
      "magnitude": 3,
      "option_1_favors_idx": 1, // Option 1 gave the money to Subject B (Index 1)
      "option_2_favors_idx": 0  // Option 2 gave the money to Subject A (Index 0)
    }
    ```

### 3.2. Analysis Phase
*   **File**: `analysis/logic/stats_calculators.py`
*   **Function**: `calculate_identity_asymmetry_metrics`
*   **Logic**:
    *   Iterate through user choices.
    *   Extract `option_1_favors_idx` and `option_2_favors_idx` from metadata.
    *   Determine `chosen_subject_idx`.
    *   Count choices for Subject A vs Subject B.
    *   **Identity Consistency Score**: `Max(Wins_for_A, Wins_for_B) / Total_Questions`.
        *   Example: Health wins 9/10, Education wins 1/10 -> Score = 90%.
    *   **Pain Curve Data**: Map `step_number` -> `chosen_subject_idx`.

### 3.3. Visualization Phase
*   **File**: `analysis/presentation/html_renderers.py`
*   **Components**:
    *   **Heatmap**: Table rows = Users, Cols = Metrics (Consistency, Preferred Subject).
    *   **Pain Curve**: Detailed view for single user, showing choice at each step.

## 4. Implementation Details

### 4.1. Translation Keys
*   **New Keys** in `application/translations.py` (under `answers` or appropriate section):
    *   `favor_subject_index_0`: "Favor {subject_0}" / "מעדיף את {subject_0}"
    *   `favor_subject_index_1`: "Favor {subject_1}" / "מעדיף את {subject_1}"
    *   ... (or a generic formatter handled in code).
    *   *Refinement*: The backend will produce keys like `favor_option` and the frontend/renderer will interpolate the subject name.
    *   **Agreed Pattern**: `Favor {Subject Name}`.

### 4.2. File Modifications
1.  `application/services/pair_generation/identity_asymmetry_strategy.py` (New)
2.  `application/services/pair_generation/__init__.py` (Register strategy)
3.  `application/services/survey_service.py` (Validation)
4.  `application/translations.py` (Strings)
5.  `analysis/logic/stats_calculators.py` (Metrics)
6.  `analysis/presentation/html_renderers.py` (Visuals)
7.  `analysis/report_service.py` (Report integration)

## 5. Decisions & Refinements
1.  **Option Labels**: Use "Favor {Subject Name}".
2.  **Multiple Equal Pairs**: Always pick the pair with the **largest value**.
3.  **Math Integrity**: Calculate float magnitude first, then round, then apply to start values.
4.  **Metadata**: Explicitly map `option_X_favors_idx`.
5.  **Consistency**: Defined as `Max(Wins_A, Wins_B) / Total`.
