"""
This module contains pure statistical and mathematical calculation functions.
"""

import json
import logging
import math
import re
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from analysis.utils.analysis_utils import is_sum_optimized

logger = logging.getLogger(__name__)

EXTREME_VECTOR_EXPECTED_PAIRS = 12


def get_summary_value(df: pd.DataFrame, column: str) -> float:
    """
    Retrieve a specific value from the 'Total' row of a summary DataFrame.

    Args:
        df (pd.DataFrame): The summary DataFrame containing a 'Total' row.
        column (str): The name of the column from which to retrieve the value.

    Returns:
        float: The value from the specified column in the 'Total' row.
    """
    logger.debug(f"Retrieving summary value for column: {column}")
    return df.loc[df["survey_id"] == "Total", column].values[0]


def calculate_user_consistency(
    optimization_stats: pd.DataFrame, consistency_threshold: float = 0.8
) -> tuple[float, int, int, int, int]:
    """
    Calculate user consistency percentage across surveys.

    Methodology:
    1. Determine min surveys required for analysis.
    2. Identify users who completed at least min_surveys (qualified users).
    3. For each qualified user, calculate consistency ratio:
       - Count occurrences of each unique result (sum/ratio/equal).
       - Divide max count by total surveys taken.
    4. Users with ratio >= threshold are consistent.
    5. Calculate percentage of consistent users among qualified.

    Args:
    optimization_stats: DataFrame with user survey results.
    consistency_threshold: Min ratio to be considered consistent (default: 0.8).

    Returns:
    tuple: (consistency_%, qualified_users, total_responses, min_surveys,
    total_surveys)
        - consistency_%: Percentage of users with consistent preferences.
        - qualified_users: # users completing min required surveys.
        - total_responses: Total number of survey responses in dataset.
        - min_surveys: Minimum surveys for consistency analysis.
        - total_surveys: Total unique surveys in dataset.
    """
    logger.info(f"Calculating user consistency (threshold {consistency_threshold})")

    total_surveys = optimization_stats["survey_id"].nunique()

    # Min surveys: max of 2 or half the total (rounded up)
    min_surveys = max(2, math.ceil(total_surveys / 2))

    # Count surveys per user
    survey_counts = optimization_stats.groupby("user_id")["survey_id"].nunique()

    # Filter users with at least min_surveys
    qualified_users = survey_counts[survey_counts >= min_surveys].index

    # Calculate consistency for qualified users
    user_consistency = (
        optimization_stats[optimization_stats["user_id"].isin(qualified_users)]
        .groupby("user_id")["result"]
        .agg(lambda x: x.value_counts().iloc[0] / len(x))
    )

    # Count users above the consistency threshold
    consistent_users = (user_consistency >= consistency_threshold).sum()
    total_qualified_users = len(qualified_users)

    # Calculate percentage of consistent users
    consistent_percentage = (
        (consistent_users / total_qualified_users) * 100
        if total_qualified_users > 0
        else 0
    )

    logger.info(
        f"Consistency: {consistent_percentage:.1f}% ({consistent_users}/"
        + f"{total_qualified_users} qualified users)"
    )
    return (
        consistent_percentage,
        total_qualified_users,
        len(survey_counts),
        min_surveys,
        total_surveys,
    )


def calculate_choice_statistics(
    choices: List[Dict], strategy: Optional[Any] = None
) -> Dict[str, float]:
    """
    Calculate optimization and answer choice statistics for a set of choices.

    Args:
        choices: List of choices for a single user's survey response.
                 Requires: optimal_allocation, option_1, option_2, user_choice
        strategy: Optional strategy instance to provide dynamic metric keys.

    Returns:
        Dict with percentages indexed by metric names from the strategy.
    """
    total_choices = len(choices)
    if total_choices == 0:
        stats = {
            "sum_percent": 0,
            "ratio_percent": 0,
            "option1_percent": 0,
            "option2_percent": 0,
            "total_choices": 0,
        }
        # Add strategy-specific metrics if available
        if strategy and hasattr(strategy, "metric_a"):
            stats[f"{strategy.metric_a.name}_percent"] = 0
            stats[f"{strategy.metric_b.name}_percent"] = 0
        return stats

    # Check for biennial strategy
    is_biennial = False
    if strategy and hasattr(strategy, "is_biennial") and strategy.is_biennial():
        is_biennial = True
    elif choices and "strategy_name" in choices[0]:
        strategy_name = choices[0]["strategy_name"]
        if strategy_name == "triangle_inequality_test":
            is_biennial = True
    elif choices:
        # Fallback: Check if vectors are 6 elements (biennial) vs 3 (single year)
        try:
            first_choice = choices[0]
            option_1 = json.loads(first_choice.get("option_1", "[]"))
            if len(option_1) == 6:
                # This is a biennial budget (2 years × 3 subjects = 6 elements)
                is_biennial = True
        except (json.JSONDecodeError, TypeError, KeyError):
            pass

    if is_biennial:
        # Only calculate option selection percentages
        # Strategy-specific metrics are calculated by
        # _calculate_triangle_inequality_metrics()
        option1_count = sum(1 for choice in choices if choice.get("user_choice") == 1)
        opt1_p = (option1_count / total_choices) * 100
        opt2_p = ((total_choices - option1_count) / total_choices) * 100
        return {
            "option1_percent": opt1_p,
            "option2_percent": opt2_p,
        }

    # Handle Rank-Based strategies dynamically
    if strategy and hasattr(strategy, "metric_a"):
        metric_a_name = strategy.metric_a.name
        metric_b_name = strategy.metric_b.name

        count_a = 0
        count_b = 0
        option1_count = 0

        for choice in choices:
            user_choice = choice["user_choice"]
            if user_choice == 1:
                option1_count += 1

            opt1_strat = choice.get("option1_strategy", "")

            # Identify which option corresponds to which metric
            # GenericRankStrategy._get_metric_name provides the descriptive strings
            # stored in optionX_strategy.
            metric_a_desc = strategy._get_metric_name(strategy.metric_a.metric_type)

            # Check if option 1 is Metric A
            if metric_a_desc in opt1_strat:
                chosen_metric_a = user_choice == 1
            else:
                # Option 2 must be Metric A
                chosen_metric_a = user_choice == 2

            if chosen_metric_a:
                count_a += 1
            else:
                count_b += 1

        return {
            f"{metric_a_name}_percent": (count_a / total_choices) * 100,
            f"{metric_b_name}_percent": (count_b / total_choices) * 100,
            "option1_percent": (option1_count / total_choices) * 100,
            "option2_percent": ((total_choices - option1_count) / total_choices) * 100,
            "total_choices": total_choices,
        }

    # Legacy fallback for L1 vs Leontief
    sum_optimized = 0
    option1_count = 0

    for choice in choices:
        optimal = json.loads(choice["optimal_allocation"])
        opt1 = json.loads(choice["option_1"])
        opt2 = json.loads(choice["option_2"])
        user_choice = choice["user_choice"]

        # Determine if choice optimizes sum or ratio
        is_sum = is_sum_optimized(optimal, opt1, opt2, user_choice)
        if is_sum:
            sum_optimized += 1

        # Count option choices
        if user_choice == 1:
            option1_count += 1

    return {
        "sum_percent": (sum_optimized / total_choices) * 100,
        "ratio_percent": ((total_choices - sum_optimized) / total_choices) * 100,
        "option1_percent": (option1_count / total_choices) * 100,
        "option2_percent": ((total_choices - option1_count) / total_choices) * 100,
    }


def deduce_rankings(choices: List[Dict]) -> Dict:
    """
    Processes 12 pairwise choices into a structured format of 4 ranked questions.

    Args:
        choices: A list of 12 choice dictionaries from a preference ranking survey.

    Returns:
        A dictionary containing deduced pairwise preferences, full rankings,
        and magnitude values.
    """
    # Extract metadata from strategy strings and choice data
    magnitudes_set = set()
    parsed_choices = []

    for choice in choices:
        # Extract magnitude, vector_type, and pair_type from the data structure
        # Since the preference ranking strategy encodes this information
        parsed_choice = parse_preference_ranking_choice(choice)
        if parsed_choice:
            parsed_choices.append(parsed_choice)
            magnitudes_set.add(parsed_choice["magnitude"])

    if len(magnitudes_set) != 2 or not parsed_choices:
        return None  # Invalid data

    magnitudes = sorted(list(magnitudes_set))
    x1_mag, x2_mag = magnitudes

    pairwise_preferences = {"A vs B": {}, "A vs C": {}, "B vs C": {}}
    for pair_type in pairwise_preferences:
        pairwise_preferences[pair_type] = {x1_mag: {}, x2_mag: {}}

    for parsed_choice in parsed_choices:
        pair_type = parsed_choice["pair_type"]
        magnitude = parsed_choice["magnitude"]
        vector_type = parsed_choice["vector_type"]
        user_choice = parsed_choice["user_choice"]

        op1, op2 = pair_type.split(" vs ")
        preference = f"{op1} > {op2}" if user_choice == 1 else f"{op2} > {op1}"

        # For negative questions, swap the preference direction
        if vector_type == "negative":
            # Swap the preference: "A > B" becomes "B > A"
            if " > " in preference:
                winner, loser = preference.split(" > ")
                preference = f"{loser} > {winner}"

        v_type_symbol = "+" if vector_type == "positive" else "–"

        pairwise_preferences[pair_type][magnitude][v_type_symbol] = preference

    rankings = {x1_mag: {}, x2_mag: {}}
    for mag in [x1_mag, x2_mag]:
        for v_type in ["+", "–"]:
            try:
                prefs = {
                    pt: pairwise_preferences[pt][mag][v_type]
                    for pt in ["A vs B", "A vs C", "B vs C"]
                }
                wins = {"A": 0, "B": 0, "C": 0}
                for p_str in prefs.values():
                    winner = p_str.split(" > ")[0]
                    wins[winner] += 1

                sorted_ranking = sorted(
                    wins.keys(), key=lambda k: wins[k], reverse=True
                )
                rankings[mag][v_type] = " > ".join(sorted_ranking)
            except KeyError:
                rankings[mag][v_type] = "Error"

    return {
        "magnitudes": (x1_mag, x2_mag),
        "pairwise": pairwise_preferences,
        "rankings": rankings,
    }


def parse_preference_ranking_choice(choice: Dict) -> Optional[Dict]:
    """
    Parse a preference ranking choice to extract metadata.

    Args:
        choice: Choice dictionary from database

    Returns:
        Dictionary with parsed metadata or None if parsing fails
    """
    try:
        # Get pair number - this tells us which question and pair type
        pair_number = choice.get("pair_number")
        if not isinstance(pair_number, int) or pair_number < 1 or pair_number > 12:
            return None

        # Get user choice
        user_choice = choice.get("user_choice")
        if user_choice not in (1, 2):
            return None

        # Load the ideal allocation
        try:
            ideal_allocation = (
                json.loads(choice["optimal_allocation"])
                if isinstance(choice["optimal_allocation"], str)
                else choice["optimal_allocation"]
            )
        except (json.JSONDecodeError, KeyError):
            return None

        # Determine question number (1-4) and pair type within question
        # Questions are organized as: Q1 (pairs 1-3), Q2 (pairs 4-6), Q3 (pairs 7-9), Q4 (pairs 10-12)
        question_number = ((pair_number - 1) // 3) + 1
        pair_index_in_question = ((pair_number - 1) % 3) + 1

        # Determine pair type based on position in question
        if pair_index_in_question == 1:
            pair_type = "A vs B"
        elif pair_index_in_question == 2:
            pair_type = "A vs C"
        else:  # pair_index_in_question == 3
            pair_type = "B vs C"

        # Determine magnitude and vector type from question number
        # Q1: X1 positive, Q2: X1 negative, Q3: X2 positive, Q4: X2 negative
        min_value = min(ideal_allocation)
        x1 = max(1, round(0.2 * min_value))
        x2 = max(1, round(0.4 * min_value))

        if question_number == 1:
            magnitude = x1
            vector_type = "positive"
        elif question_number == 2:
            magnitude = x1
            vector_type = "negative"
        elif question_number == 3:
            magnitude = x2
            vector_type = "positive"
        else:  # question_number == 4
            magnitude = x2
            vector_type = "negative"

        return {
            "pair_type": pair_type,
            "magnitude": magnitude,
            "vector_type": vector_type,
            "user_choice": user_choice,
            "question_number": question_number,
        }

    except Exception as e:
        logger.warning(f"Failed to parse preference ranking choice: {e}")
        return None


def extract_extreme_vector_preferences(
    choices: List[Dict],
) -> Tuple[
    List[List[int]],
    int,
    int,
    List[Tuple[int, int, Optional[str]]],
    Dict[int, Dict[str, List[int]]],
]:
    """
    Extract extreme vector preferences from user choices, and calculate
    consistency for weighted pairs.

    Args:
        choices: List of choice dictionaries

    Returns:
        Tuple containing:
        - counts_matrix: 3x3 grid of preference counts
        - processed_pairs: number of successfully processed pairs
        - expected_pairs: expected number of pairs
        - consistency_info: list of (matches, total, core_preference)
          for each group (A vs B, ...)
        - percentile_data: Dict mapping percentiles to group consistency data
    """
    # Extract the basic preference data
    (
        counts,
        core_preferences,
        weighted_answers,
        processed_pairs,
        percentile_data,
    ) = extract_preference_counts(choices)

    # Calculate consistency metrics between core preferences and weighted answers
    consistency_info = calculate_consistency_metrics(core_preferences, weighted_answers)

    return (
        counts,
        processed_pairs,
        EXTREME_VECTOR_EXPECTED_PAIRS,
        consistency_info,
        percentile_data,
    )


def extract_preference_counts(
    choices: List[Dict],
) -> Tuple[
    List[List[int]],
    List[Optional[str]],
    List[List[str]],
    int,
    Dict[int, Dict[str, List[int]]],
]:
    """
    Extract core preference counts and organize data for consistency analysis.

    Args:
        choices: List of choice dictionaries

    Returns:
        Tuple containing:
        - counts_matrix: 3x3 grid of preference counts
        - core_preferences: List of core preferences (A/B/C) for each group
        - weighted_answers: List of lists containing weighted pair preferences
          for each group
        - processed_pairs: Number of successfully processed pairs
        - percentile_data: Dict mapping percentiles to group consistency data
    """
    index_to_name = {0: "A", 1: "B", 2: "C"}
    name_to_index = {"A": 0, "B": 1, "C": 2}
    group_names = [("A", "B"), ("A", "C"), ("B", "C")]

    # Initialize counts for the 3x3 grid
    counts = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
    processed_pairs = 0

    # Store for each group: core_preference, list of weighted answers
    core_preferences = [None, None, None]  # 0: A vs B, 1: A vs C, 2: B vs C
    weighted_answers = [
        [],
        [],
        [],
    ]  # Each is a list of user choices for weighted pairs

    # Initialize percentile tracking
    percentile_data = {
        25: {"A_vs_B": [0, 0], "A_vs_C": [0, 0], "B_vs_C": [0, 0]},
        50: {"A_vs_B": [0, 0], "A_vs_C": [0, 0], "B_vs_C": [0, 0]},
        75: {"A_vs_B": [0, 0], "A_vs_C": [0, 0], "B_vs_C": [0, 0]},
    }

    for choice in choices:
        try:
            opt1_str = choice.get("option1_strategy", "")
            opt2_str = choice.get("option2_strategy", "")
            user_choice = choice["user_choice"]  # 1 or 2

            # Determine if this is a core extreme pair or a weighted pair
            is_core = opt1_str.startswith("Extreme Vector") and opt2_str.startswith(
                "Extreme Vector"
            )
            is_weighted = (
                "Weighted Average" in opt1_str and "Weighted Average" in opt2_str
            )

            idx1 = extract_vector_index(opt1_str)
            idx2 = extract_vector_index(opt2_str)

            if idx1 is None or idx2 is None:
                logger.debug(f"Skipping non-extreme pair: {opt1_str} vs {opt2_str}")
                continue
            if idx1 not in index_to_name or idx2 not in index_to_name:
                logger.warning(f"Invalid extreme index found: {idx1}, {idx2}")
                continue

            # Get the corresponding names
            name1 = index_to_name[idx1]
            name2 = index_to_name[idx2]

            # Which group is this? (A vs B, A vs C, B vs C)
            group_idx = None
            for i, (g1, g2) in enumerate(group_names):
                if set([name1, name2]) == set([g1, g2]):
                    group_idx = i
                    break
            if group_idx is None:
                continue

            # Process the comparison and update counts
            (
                comparison_type,
                preferred_name,
            ) = determine_comparison_and_preference(name1, name2, user_choice)
            if comparison_type is None or preferred_name is None:
                continue
            if preferred_name not in name_to_index:
                logger.error(f"Invalid preferred name: {preferred_name}")
                continue
            preferred_index = name_to_index[preferred_name]

            # Increment the corresponding cell count
            counts[comparison_type][preferred_index] += 1
            processed_pairs += 1

            # Store for consistency calculation
            if is_core:
                # Core pair: store the user's preference for this group
                core_preferences[group_idx] = preferred_name
            elif is_weighted:
                # Weighted pair: store user's answer (A/B/C) for this group
                weighted_answers[group_idx].append(preferred_name)

                # Extract percentile from strategy string
                percentile = None
                if "25%" in opt1_str or "25%" in opt2_str:
                    percentile = 25
                elif "50%" in opt1_str or "50%" in opt2_str:
                    percentile = 50
                elif "75%" in opt1_str or "75%" in opt2_str:
                    percentile = 75

                if percentile is not None:
                    group_key = (
                        f"{group_names[group_idx][0]}_vs_"
                        f"{group_names[group_idx][1]}"
                    )
                    # matches[0] is total, matches[1] is matches
                    if core_preferences[group_idx] is not None:
                        percentile_data[percentile][group_key][0] += 1
                        if preferred_name == core_preferences[group_idx]:
                            percentile_data[percentile][group_key][1] += 1

        except Exception as e:
            logger.error(f"Error processing extreme choice: {e}", exc_info=True)
            continue

    return (
        counts,
        core_preferences,
        weighted_answers,
        processed_pairs,
        percentile_data,
    )


def calculate_consistency_metrics(
    core_preferences: List[Optional[str]],
    weighted_answers: List[List[str]],
) -> List[Tuple[int, int, Optional[str]]]:
    """
    Calculate consistency metrics between core and weighted preferences.

    Args:

        core_preferences: List of core preferences (A/B/C) for each group
        weighted_answers: List of lists containing weighted pair preferences
          for each group

    Returns:
        List of tuples (matches, total, core_preference) for each group
    """
    consistency_info = []

    for i in range(len(core_preferences)):
        core = core_preferences[i]
        weighted = weighted_answers[i]

        if core is not None and weighted:
            matches = sum(1 for w in weighted if w == core)
            total = len(weighted)
        else:
            matches = 0
            total = 0

        consistency_info.append((matches, total, core))

    return consistency_info


def extract_vector_index(strategy_string: str) -> Optional[int]:
    """
    Extract the vector index from a strategy string.

    Args:
        strategy_string: String describing the vector strategy

    Returns:
        int: Extracted index (0-based) or None if not found
    """
    # Extract extreme vector index from strategy string
    # Handles formats:
    #   "Extreme Vector 1" (core extremes)
    #   "75% Weighted Average (Extreme 1)" (weighted averages)
    pattern = r"Extreme (?:Vector )?(\d+)|Extreme\s+(\d+)"
    match = re.search(pattern, strategy_string)

    if not match:
        return None

    # Get the first non-None captured group
    idx_str = next((g for g in match.groups() if g is not None), None)

    if idx_str is None:
        return None

    # Convert to 0-based index (A=0, B=1, C=2)
    return int(idx_str) - 1


def determine_comparison_and_preference(
    name1: str, name2: str, user_choice: int
) -> Tuple[Optional[int], Optional[str]]:
    """
    Determine the comparison type and preferred option.

    Args:
        name1: Name of the first option (A, B, or C)
        name2: Name of the second option (A, B, or C)
        user_choice: User's choice (1 or 2)

    Returns:
        tuple: (comparison_type, preferred_name)
            - comparison_type: 0 for A vs B, 1 for A vs C, 2 for B vs C
            - preferred_name: The preferred option name (A, B, or C)
    """
    # Determine comparison type and preferred category
    comparison_type = None  # 0: AvsB, 1: AvsC, 2: BvsC
    preferred_name = None

    pair_set = {name1, name2}
    if pair_set == {"A", "B"}:
        comparison_type = 0
        preferred_name = name1 if user_choice == 1 else name2
    elif pair_set == {"A", "C"}:
        comparison_type = 1
        preferred_name = name1 if user_choice == 1 else name2
    elif pair_set == {"B", "C"}:
        comparison_type = 2
        preferred_name = name1 if user_choice == 1 else name2
    else:
        # Should not happen if indices are valid
        logger.error(f"Unexpected pair set: {pair_set}")

    return comparison_type, preferred_name


def calculate_cyclic_shift_group_consistency(choices: List[Dict]) -> Dict[str, float]:
    """
    Calculate group-level consistency for cyclic shift strategy using binary
    metric.

    Binary consistency: A group is 100% consistent only if all 3 choices match,
    otherwise 0% consistent.

    Args:
        choices: List of choices for a single user's survey response using the
                component_symmetry_test strategy.

    Returns:
        Dict containing binary consistency (0% or 100%) for each group (1-4)
        and overall percentage of consistent groups.
        Format: {"group_1": 100.0, "group_2": 0.0, "group_3": 100.0,
                 "group_4": 0.0, "overall": 50.0}
    """
    # Initialize group data - each group should have 3 pairs
    groups = {1: [], 2: [], 3: [], 4: []}

    # Analyze each choice and assign to appropriate group
    for choice in choices:
        option1_strategy = choice.get("option1_strategy", "")
        option2_strategy = choice.get("option2_strategy", "")
        user_choice = choice["user_choice"]

        # Extract shift information from strategy names
        # Expected format: "Cyclic Pattern A (shift X)" or
        # "Cyclic Pattern B (shift X)"
        shift_amount = None
        chosen_pattern = None

        if "shift" in option1_strategy:
            try:
                shift_part = option1_strategy.split("shift ")[1].split(")")[0]
                shift_amount = int(shift_part)
                chosen_pattern = "A" if user_choice == 1 else "B"
            except (IndexError, ValueError):
                continue
        elif "shift" in option2_strategy:
            try:
                shift_part = option2_strategy.split("shift ")[1].split(")")[0]
                shift_amount = int(shift_part)
                chosen_pattern = "B" if user_choice == 2 else "A"
            except (IndexError, ValueError):
                continue

        if shift_amount is not None and chosen_pattern:
            # Determine group based on pair index (0-11 maps to groups 1-4)
            # Each group has 3 pairs: Group 1: pairs 0-2, Group 2: pairs 3-5
            pair_number = choice.get("pair_number", 0)
            if pair_number > 0:  # pair_number is 1-indexed
                group_number = ((pair_number - 1) // 3) + 1
                if 1 <= group_number <= 4:
                    groups[group_number].append(chosen_pattern)

    # Calculate binary consistency for each group
    group_consistencies = {}
    consistent_groups = 0
    total_groups_with_data = 0

    for group_num, patterns in groups.items():
        if len(patterns) != 3:
            # Incomplete group - mark as 0% consistent
            group_consistencies[f"group_{group_num}"] = 0.0
            if len(patterns) > 0:
                total_groups_with_data += 1
            continue

        total_groups_with_data += 1

        # Binary consistency: all 3 must match
        if len(set(patterns)) == 1:  # All patterns are identical
            group_consistencies[f"group_{group_num}"] = 100.0
            consistent_groups += 1
        else:
            group_consistencies[f"group_{group_num}"] = 0.0

    # Calculate overall consistency as percentage of consistent groups
    if total_groups_with_data > 0:
        overall_consistency = (consistent_groups / total_groups_with_data) * 100
        group_consistencies["overall"] = round(overall_consistency, 1)
    else:
        group_consistencies["overall"] = 0.0

    return group_consistencies


def calculate_linear_symmetry_group_consistency(
    choices: List[Dict],
) -> Dict[str, float]:
    """
    Calculate group-level consistency for linear symmetry strategy.

    Linear symmetry means making the same relative choice between vectors v1
    and v2 regardless of whether they're applied as positive or negative
    distances.

    For each group:
    - Pair A (positive): (ideal + v1) vs (ideal + v2)
    - Pair B (negative): (ideal - v1) vs (ideal - v2)
    - Consistency = 100% if user chooses same vector in both pairs, 0%
      otherwise

    Args:
        choices: List of choices for a single user's survey response using the
                sign_symmetry_test strategy.

    Returns:
        Dict containing consistency percentages for each group (1-6) and
        overall average.
        Example: {"group_1": 100.0, "group_2": 0.0, ..., "overall": 66.7}
    """
    # Initialize group data - each group should have 2 pairs (+ and -)
    groups = {1: {}, 2: {}, 3: {}, 4: {}, 5: {}, 6: {}}

    # Parse each choice and extract group, sign, and vector choice
    for choice in choices:
        option1_strategy = choice.get("option1_strategy", "")
        option2_strategy = choice.get("option2_strategy", "")
        user_choice = choice["user_choice"]  # 1 or 2

        # Extract group number, sign (+/-), and which vector user chose
        group_num, sign, vector_choice = parse_linear_pattern_strategy(
            option1_strategy, option2_strategy, user_choice
        )

        if group_num is not None and sign is not None and vector_choice is not None:
            if 1 <= group_num <= 6:
                # Store which vector (1 for v, 2 for w) user chose for
                # this sign
                groups[group_num][sign] = vector_choice

    # Calculate consistency for each group
    group_consistencies = {}
    for group_num in range(1, 7):
        group_data = groups[group_num]

        if len(group_data) == 2 and "+" in group_data and "-" in group_data:
            # We have both positive and negative pairs for this group
            positive_choice = group_data["+"]  # 1 (v) or 2 (w)
            negative_choice = group_data["-"]  # 1 (v) or 2 (w)

            # Linear symmetry: same relative choice regardless of sign
            is_consistent = positive_choice == negative_choice
            consistency_percentage = 100.0 if is_consistent else 0.0

            group_consistencies[f"group_{group_num}"] = consistency_percentage
        else:
            # Incomplete data for this group (missing + or - pair)
            group_consistencies[f"group_{group_num}"] = 0.0

    # Calculate overall consistency as average of valid group consistencies
    # Only consider groups that have complete data (both + and - pairs)
    valid_consistencies = [
        group_consistencies[f"group_{i}"] for i in range(1, 7) if len(groups[i]) == 2
    ]

    if valid_consistencies:
        overall_consistency = sum(valid_consistencies) / len(valid_consistencies)
        group_consistencies["overall"] = round(overall_consistency, 1)
    else:
        group_consistencies["overall"] = 0.0

    return group_consistencies


def parse_linear_pattern_strategy(
    option1_strategy: str, option2_strategy: str, user_choice: int
) -> Tuple[Optional[int], Optional[str], Optional[int]]:
    """
    Parse linear pattern strategy strings to extract group, sign, and vector choice.

    Expected format: "Linear Pattern + (v1)" or "Linear Pattern - (w2)"

    Args:
        option1_strategy: Strategy description for option 1
        option2_strategy: Strategy description for option 2
        user_choice: User's choice (1 or 2)

    Returns:
        Tuple of (group_number, sign, vector_choice) where:
        - group_number: 1-6 (extracted from strategy)
        - sign: '+' or '-' (extracted from strategy)
        - vector_choice: 1 if user chose v vector, 2 if user chose w vector
    """
    import re

    # Regex pattern to match: "Linear Pattern [+/-] ([v/w][group_number])"
    pattern = r"Linear Pattern ([+-]) \(([vw])(\d+)\)"

    match1 = re.search(pattern, option1_strategy)
    match2 = re.search(pattern, option2_strategy)

    if not match1 or not match2:
        logger.debug(
            f"Failed to parse linear pattern: '{option1_strategy}' vs "
            f"'{option2_strategy}'"
        )
        return None, None, None

    sign1, vector1, group1 = match1.groups()
    sign2, vector2, group2 = match2.groups()

    # Validate that both options are from the same group and sign
    if group1 != group2 or sign1 != sign2:
        logger.debug(
            f"Mismatched group/sign: group1={group1}, group2={group2}, "
            f"sign1={sign1}, sign2={sign2}"
        )
        return None, None, None

    group_num = int(group1)
    sign = sign1

    # Determine which vector the user chose
    if user_choice == 1:
        chosen_vector = vector1  # 'v' or 'w'
    elif user_choice == 2:
        chosen_vector = vector2  # 'v' or 'w'
    else:
        logger.debug(f"Invalid user_choice: {user_choice}")
        return None, None, None

    # Convert to numeric: v=1, w=2
    vector_choice = 1 if chosen_vector == "v" else 2

    return group_num, sign, vector_choice


def calculate_temporal_preference_metrics(choices: List[Dict]) -> Dict[str, float]:
    """
    Calculate temporal preference metrics for a single user's response.

    Args:
        choices: List of choices for a single user's temporal preference survey

    Returns:
        Dict containing calculated metrics:
        - ideal_this_year_percent: Percentage choosing "Ideal This Year" (Option 1)
        - ideal_next_year_percent: Percentage choosing "Ideal Next Year" (Option 2)
        - consistency_percent: Max(ideal_this_year_count, ideal_next_year_count) * 10
    """
    if not choices:
        return {
            "ideal_this_year_percent": 0.0,
            "ideal_next_year_percent": 0.0,
            "consistency_percent": 0.0,
        }

    total_choices = len(choices)
    ideal_this_year_count = 0

    for choice in choices:
        user_choice = choice.get("user_choice")
        if user_choice == 1:  # Option 1 is "Ideal This Year"
            ideal_this_year_count += 1

    ideal_next_year_count = total_choices - ideal_this_year_count

    # Calculate percentages
    ideal_this_year_percent = (ideal_this_year_count / total_choices) * 100
    ideal_next_year_percent = (ideal_next_year_count / total_choices) * 100

    # Consistency is max(X, Y) * 10 where X+Y=10
    consistency_percent = max(ideal_this_year_count, ideal_next_year_count) * 10

    return {
        "ideal_this_year_percent": ideal_this_year_percent,
        "ideal_next_year_percent": ideal_next_year_percent,
        "consistency_percent": consistency_percent,
    }


def calculate_dynamic_temporal_metrics(choices: List[Dict]) -> Dict[str, float]:
    """
    Calculate dynamic temporal preference metrics for a single user's response.

    Args:
        choices: List of choices for a single user's dynamic temporal survey (12 choices)

    Returns:
        Dict containing calculated metrics for each sub-survey:
        - sub1_ideal_y1_percent: % choosing Ideal Year 1 in Sub-Survey 1 (Simple Discounting)
        - sub2_ideal_y2_percent: % choosing Ideal Year 2 in Sub-Survey 2 (Second-Year Choice)
        - sub3_ideal_y1_percent: % choosing Ideal Year 1 in Sub-Survey 3 (First-Year Choice)
    """
    if not choices or len(choices) != 12:
        return {
            "sub1_ideal_y1_percent": 0.0,
            "sub2_ideal_y2_percent": 0.0,
            "sub3_ideal_y1_percent": 0.0,
        }

    # Initialize counters for each sub-survey
    sub1_ideal_count = 0  # Sub-Survey 1: Simple Discounting (pairs 1-4)
    sub2_ideal_count = 0  # Sub-Survey 2: Second-Year Choice (pairs 5-8)
    sub3_ideal_count = 0  # Sub-Survey 3: First-Year Choice (pairs 9-12)

    for choice in choices:
        pair_number = choice.get("pair_number", 0)
        user_choice = choice.get("user_choice")

        if 1 <= pair_number <= 4:
            # Sub-Survey 1: Simple Discounting
            # Option 1 = (Ideal, Random), Option 2 = (Random, Ideal)
            # Choosing Option 1 means preferring Ideal Year 1
            if user_choice == 1:
                sub1_ideal_count += 1
        elif 5 <= pair_number <= 8:
            # Sub-Survey 2: Second-Year Choice
            # Option 1 = (B, Ideal), Option 2 = (B, C)
            # Choosing Option 1 means preferring Ideal Year 2
            if user_choice == 1:
                sub2_ideal_count += 1
        elif 9 <= pair_number <= 12:
            # Sub-Survey 3: First-Year Choice
            # Option 1 = (Ideal, B), Option 2 = (C, B)
            # Choosing Option 1 means preferring Ideal Year 1
            if user_choice == 1:
                sub3_ideal_count += 1

    # Calculate percentages (4 questions per sub-survey)
    sub1_ideal_y1_percent = (sub1_ideal_count / 4) * 100
    sub2_ideal_y2_percent = (sub2_ideal_count / 4) * 100
    sub3_ideal_y1_percent = (sub3_ideal_count / 4) * 100

    return {
        "sub1_ideal_y1_percent": sub1_ideal_y1_percent,
        "sub2_ideal_y2_percent": sub2_ideal_y2_percent,
        "sub3_ideal_y1_percent": sub3_ideal_y1_percent,
    }


def calculate_sub_survey_consistency_metrics(
    choices: List[Dict], sub_survey_num: int
) -> Dict[str, float]:
    """
    Calculate consistency metrics for a specific sub-survey of the dynamic temporal preference test.

    Args:
        choices: List of choices for a single user's dynamic temporal survey (12 choices)
        sub_survey_num: Sub-survey number (1, 2, or 3)

    Returns:
        Dict containing calculated metrics for the specific sub-survey:
        - ideal_percent: Percentage choosing the ideal option
        - alternative_percent: Percentage choosing the alternative option
        - consistency_percent: Max(ideal_count, alternative_count) * 25 (since 4 questions per sub-survey)
    """
    if not choices or len(choices) != 12:
        return {
            "ideal_percent": 0.0,
            "alternative_percent": 0.0,
            "consistency_percent": 0.0,
        }

    # Filter choices for the specific sub-survey
    if sub_survey_num == 1:
        # Sub-Survey 1: Simple Discounting (pairs 1-4)
        sub_choices = [c for c in choices if 1 <= c.get("pair_number", 0) <= 4]
    elif sub_survey_num == 2:
        # Sub-Survey 2: Second-Year Choice (pairs 5-8)
        sub_choices = [c for c in choices if 5 <= c.get("pair_number", 0) <= 8]
    elif sub_survey_num == 3:
        # Sub-Survey 3: First-Year Choice (pairs 9-12)
        sub_choices = [c for c in choices if 9 <= c.get("pair_number", 0) <= 12]
    else:
        return {
            "ideal_percent": 0.0,
            "alternative_percent": 0.0,
            "consistency_percent": 0.0,
        }

    if len(sub_choices) != 4:
        return {
            "ideal_percent": 0.0,
            "alternative_percent": 0.0,
            "consistency_percent": 0.0,
        }

    # Count ideal choices (Option 1 in all sub-surveys represents the ideal choice)
    ideal_count = sum(1 for choice in sub_choices if choice.get("user_choice") == 1)
    alternative_count = 4 - ideal_count

    # Calculate percentages
    ideal_percent = (ideal_count / 4) * 100
    alternative_percent = (alternative_count / 4) * 100

    # Consistency is max(ideal_count, alternative_count) * 25 (since max is 4, and 4*25=100)
    consistency_percent = max(ideal_count, alternative_count) * 25

    return {
        "ideal_percent": ideal_percent,
        "alternative_percent": alternative_percent,
        "consistency_percent": consistency_percent,
    }


def calculate_final_consistency_score(deduced_data: Dict) -> int:
    """Calculates the final consistency score from deduced ranking data."""
    if not deduced_data or "pairwise" not in deduced_data:
        return 0

    magnitudes = deduced_data["magnitudes"]
    x1_mag, x2_mag = magnitudes
    pairwise_prefs = deduced_data["pairwise"]
    final_cons_score = 0
    for pt in pairwise_prefs:
        prefs = [
            pairwise_prefs[pt][x1_mag]["+"],
            pairwise_prefs[pt][x1_mag]["–"],
            pairwise_prefs[pt][x2_mag]["+"],
            pairwise_prefs[pt][x2_mag]["–"],
        ]
        if len(set(prefs)) == 1:
            final_cons_score += 1
    return final_cons_score


def calculate_single_peaked_metrics(choices: List[Dict]) -> Dict[str, float]:
    """
    Calculate multi-dimensional single-peaked metrics for a user's responses.

    Determines how often respondents selected the vector closer to their peak
    (near vector) versus the further vector, and derives consistency levels.
    """
    if not choices:
        return {
            "near_vector_count": 0,
            "far_vector_count": 0,
            "near_vector_percent": 0.0,
            "far_vector_percent": 0.0,
            "consistency_percent": 0.0,
            "total_pairs": 0,
        }

    near_count = 0
    far_count = 0

    for choice in choices:
        try:
            optimal_raw = choice.get("optimal_allocation")
            option1_raw = choice.get("option_1")
            option2_raw = choice.get("option_2")
            user_choice = choice.get("user_choice")

            if user_choice not in (1, 2):
                continue

            if isinstance(optimal_raw, (list, tuple)):
                optimal = [int(v) for v in optimal_raw]
            else:
                optimal = list(json.loads(optimal_raw))

            if isinstance(option1_raw, (list, tuple)):
                option_1 = [int(v) for v in option1_raw]
            else:
                option_1 = list(json.loads(option1_raw))

            if isinstance(option2_raw, (list, tuple)):
                option_2 = [int(v) for v in option2_raw]
            else:
                option_2 = list(json.loads(option2_raw))

            if not (optimal and option_1 and option_2):
                continue
            if len(optimal) != len(option_1) or len(optimal) != len(option_2):
                continue

            dist_1 = sum(abs(o1 - opt) for o1, opt in zip(option_1, optimal))
            dist_2 = sum(abs(o2 - opt) for o2, opt in zip(option_2, optimal))

            if dist_1 == dist_2:
                # Ambiguous pair; skip to avoid misclassification
                continue

            near_option = 1 if dist_1 < dist_2 else 2

            if user_choice == near_option:
                near_count += 1
            else:
                far_count += 1
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            logger.debug("Failed to process MDSP choice for metrics: %s", exc)
            continue

    total_pairs = near_count + far_count
    if total_pairs == 0:
        return {
            "near_vector_count": 0,
            "far_vector_count": 0,
            "near_vector_percent": 0.0,
            "far_vector_percent": 0.0,
            "consistency_percent": 0.0,
            "total_pairs": 0,
        }

    near_percent = (near_count / total_pairs) * 100
    far_percent = (far_count / total_pairs) * 100

    return {
        "near_vector_count": near_count,
        "far_vector_count": far_count,
        "near_vector_percent": round(near_percent, 1),
        "far_vector_percent": round(far_percent, 1),
        "consistency_percent": round(max(near_percent, far_percent), 1),
        "total_pairs": total_pairs,
    }


def calculate_triangle_inequality_metrics(choices: List[Dict]) -> Dict[str, float]:
    """
    Calculate triangle inequality test metrics for a single user's response.

    Analyzes whether users prefer concentrated changes (entire deviation in one year)
    or distributed changes (deviation split across two years).

    Args:
        choices: List of 12 choices for triangle inequality survey

    Returns:
        Dict with:
            - concentrated_count: Number of times user chose concentrated
            - distributed_count: Number of times user chose distributed
            - concentrated_percent: Percentage choosing concentrated
            - distributed_percent: Percentage choosing distributed
            - consistency_percent: Consistency score (how often user made same choice type)
    """
    if not choices or len(choices) != 12:
        return {
            "concentrated_count": 0,
            "distributed_count": 0,
            "concentrated_percent": 0.0,
            "distributed_percent": 0.0,
            "consistency_percent": 0.0,
        }

    concentrated_count = 0
    distributed_count = 0

    for choice in choices:
        chosen_option = choice.get("user_choice")
        option1_strategy = choice.get("option1_strategy", "")
        option2_strategy = choice.get("option2_strategy", "")

        # Determine what type was chosen
        if chosen_option == 1:
            chosen_strategy = option1_strategy
        else:
            chosen_strategy = option2_strategy

        if "Concentrated" in chosen_strategy:
            concentrated_count += 1
        elif "Distributed" in chosen_strategy:
            distributed_count += 1

    total = concentrated_count + distributed_count
    if total == 0:
        concentrated_percent = 0.0
        distributed_percent = 0.0
        consistency_percent = 0.0
    else:
        concentrated_percent = (concentrated_count / total) * 100
        distributed_percent = (distributed_count / total) * 100

        # Consistency: percentage of most frequent choice
        consistency_percent = max(concentrated_percent, distributed_percent)

    return {
        "concentrated_count": concentrated_count,
        "distributed_count": distributed_count,
        "concentrated_percent": round(concentrated_percent, 1),
        "distributed_percent": round(distributed_percent, 1),
        "consistency_percent": round(consistency_percent, 1),
    }


def calculate_rank_consistency_metrics(
    choices: List[Dict], keyword_a: str = "sum", keyword_b: str = "ratio"
) -> Dict[str, float]:
    """
    Calculate per-user consistency.
    Now accepts dynamic keywords (e.g., 'l1', 'leontief') to match against the DB.
    """
    if not choices:
        return {
            "metric_a_count": 0,
            "metric_b_count": 0,
            "metric_a_percent": 0.0,
            "metric_b_percent": 0.0,
            "consistency_percent": 0.0,
        }

    count_a = 0
    count_b = 0

    # Convert to string and lower case for safe matching
    kw_a = str(keyword_a).lower()
    kw_b = str(keyword_b).lower()

    for choice in choices:
        chosen_option = choice.get("user_choice")
        # Get the stored strategy string (e.g., "l1" or "leontief")
        option1_strategy = str(choice.get("option1_strategy", "")).lower()
        option2_strategy = str(choice.get("option2_strategy", "")).lower()

        # Determine which string the user actually chose
        chosen_strategy = option1_strategy if chosen_option == 1 else option2_strategy

        # Simple containment check
        if kw_a in chosen_strategy:
            count_a += 1
        elif kw_b in chosen_strategy:
            count_b += 1

    total = count_a + count_b
    if total == 0:
        return {
            "metric_a_count": 0,
            "metric_b_count": 0,
            "metric_a_percent": 0.0,
            "metric_b_percent": 0.0,
            "consistency_percent": 0.0,
        }

    percent_a = (count_a / total) * 100
    percent_b = (count_b / total) * 100

    return {
        "metric_a_count": count_a,
        "metric_b_count": count_b,
        "metric_a_percent": round(percent_a, 1),
        "metric_b_percent": round(percent_b, 1),
        "consistency_percent": round(max(percent_a, percent_b), 1),
    }
