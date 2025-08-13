"""
Transitivity Analysis for Extreme Vectors Strategy

This module analyzes logical consistency in user preferences across different
percentile groups for the extreme vectors strategy. It checks if preferences
follow transitivity rules (if A>B and B>C, then A>C must hold).
"""

import logging
import re
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class TransitivityAnalyzer:
    """Analyzes transitivity in extreme vector preferences."""

    def __init__(self):
        """Initialize the analyzer with vector mappings."""
        self.vector_mapping = {
            "Extreme Vector 1": "A",
            "Extreme Vector 2": "B",
            "Extreme Vector 3": "C",
        }

    def extract_preferences_by_group(self, choices: List[Dict]) -> Dict[str, Dict]:
        """
        Extract preferences for each percentile group.

        Args:
            choices: List of user choices from database

        Returns:
            {
                'core': {'A_vs_B': 'A', 'A_vs_C': 'A', 'B_vs_C': 'B'},
                '25': {'A_vs_B': 'A', 'A_vs_C': 'A', 'B_vs_C': 'C'},
                '50': {...},
                '75': {...}
            }
        """
        groups = {"core": {}, "25": {}, "50": {}, "75": {}}

        for choice in choices:
            option1_strategy = choice.get("option1_strategy", "")
            option2_strategy = choice.get("option2_strategy", "")
            user_choice = choice.get("user_choice")

            if not option1_strategy or not option2_strategy or user_choice is None:
                continue

            # Determine which group this comparison belongs to
            group = self._identify_group(option1_strategy, option2_strategy)
            if not group:
                continue

            # Extract the vector identifiers
            vector1 = self._extract_vector_identifier(option1_strategy)
            vector2 = self._extract_vector_identifier(option2_strategy)

            if not vector1 or not vector2:
                continue

            # Determine preference
            preferred_vector = vector1 if user_choice == 1 else vector2
            comparison_key = f"{min(vector1, vector2)}_vs_{max(vector1, vector2)}"

            groups[group][comparison_key] = preferred_vector

        return groups

    def _identify_group(
        self, option1_strategy: str, option2_strategy: str
    ) -> Optional[str]:
        """Identify which percentile group a comparison belongs to."""
        if (
            "Extreme Vector" in option1_strategy
            and "Extreme Vector" in option2_strategy
        ):
            if (
                "Weighted" not in option1_strategy
                and "Weighted" not in option2_strategy
            ):
                return "core"

        for percentage in ["25%", "50%", "75%"]:
            if percentage in option1_strategy and percentage in option2_strategy:
                return percentage.replace("%", "")

        return None

    def _extract_vector_identifier(self, strategy: str) -> Optional[str]:
        """Extract vector identifier (A, B, C) from strategy string."""
        # Handle core extreme vectors
        if "Extreme Vector 1" in strategy:
            return "A"
        elif "Extreme Vector 2" in strategy:
            return "B"
        elif "Extreme Vector 3" in strategy:
            return "C"

        # Handle weighted averages
        patterns = [
            r"Weighted Average \(Extreme (\d+)\)",
            r"(\d+)% Weighted.*Extreme (\d+)",
            r"Extreme (\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, strategy)
            if match:
                vector_num = (
                    match.group(1) if len(match.groups()) == 1 else match.group(2)
                )
                vector_map = {"1": "A", "2": "B", "3": "C"}
                return vector_map.get(vector_num)

        return None

    def determine_preference_order(
        self, comparisons: Dict[str, str]
    ) -> Tuple[str, bool]:
        """
        Determine preference ordering from pairwise comparisons.

        Args:
            comparisons: {'A_vs_B': 'A', 'A_vs_C': 'A', 'B_vs_C': 'B'}

        Returns:
            ('A>B>C', True) if transitive
            ('A>B, B>C, C>A', False) if cycle detected (shows actual cycle)
        """
        if not comparisons or len(comparisons) < 3:
            return ("Incomplete", False)

        # Extract preferences
        prefs = {}
        for comparison, winner in comparisons.items():
            vectors = comparison.split("_vs_")
            if len(vectors) == 2:
                v1, v2 = vectors
                if winner == v1:
                    prefs[(v1, v2)] = True
                    prefs[(v2, v1)] = False
                else:
                    prefs[(v1, v2)] = False
                    prefs[(v2, v1)] = True

        # Check all possible orderings for transitivity
        vectors = ["A", "B", "C"]
        from itertools import permutations

        for perm in permutations(vectors):
            if self._is_order_consistent(perm, prefs):
                order_str = ">".join(perm)
                return (order_str, True)

        # If no consistent ordering found, show the actual preferences that
        # create the cycle
        return (self._format_intransitive_cycle(prefs), False)

    def _is_order_consistent(
        self, order: Tuple[str, str, str], prefs: Dict[Tuple[str, str], bool]
    ) -> bool:
        """Check if a given order is consistent with observed preferences."""
        for i in range(len(order)):
            for j in range(i + 1, len(order)):
                v1, v2 = order[i], order[j]
                # v1 should be preferred over v2 in this order
                if (v1, v2) in prefs and not prefs[(v1, v2)]:
                    return False
                if (v2, v1) in prefs and prefs[(v2, v1)]:
                    return False
        return True

    def _format_intransitive_cycle(self, prefs: Dict[Tuple[str, str], bool]) -> str:
        """
        Format the intransitive cycle to show actual conflicting preferences.

        Args:
            prefs: Dictionary of pairwise preferences

        Returns:
            String showing the cycle, e.g., "A>B, B>C, C>A"
        """
        # Extract the actual preferences that were observed
        preference_statements = []

        # Check each possible pair and add the preference to our list
        for v1, v2 in [("A", "B"), ("A", "C"), ("B", "C")]:
            if (v1, v2) in prefs and prefs[(v1, v2)]:
                preference_statements.append(f"{v1}>{v2}")
            elif (v2, v1) in prefs and prefs[(v2, v1)]:
                preference_statements.append(f"{v2}>{v1}")

        # If we have all three preferences, show them as a cycle
        if len(preference_statements) >= 3:
            return ", ".join(preference_statements)
        elif len(preference_statements) >= 2:
            return ", ".join(preference_statements)
        else:
            return "Intransitive"

    def analyze_group_transitivity(
        self, choices: List[Dict], percentile: Optional[int] = None
    ) -> Dict:
        """
        Analyze transitivity for specific group.

        Returns:
            {
                'is_transitive': True,
                'preference_order': 'A>B>C',
                'comparisons': {'A_vs_B': 'A', ...}
            }
        """
        groups = self.extract_preferences_by_group(choices)

        # Determine which group to analyze
        if percentile is None:
            group_key = "core"
        else:
            group_key = str(percentile)

        if group_key not in groups:
            return {
                "is_transitive": False,
                "preference_order": "No Data",
                "comparisons": {},
            }

        comparisons = groups[group_key]
        order, is_transitive = self.determine_preference_order(comparisons)

        return {
            "is_transitive": is_transitive,
            "preference_order": order,
            "comparisons": comparisons,
        }

    def _analyze_pairwise_consistency(self, groups: Dict[str, Dict]) -> Dict:
        """
        Analyze consistency for each pair across all groups.

        Args:
            groups: Dictionary with group data from
                   extract_preferences_by_group()

        Returns:
            Dictionary with pairwise consistency analysis
        """
        pairs = ["A_vs_B", "A_vs_C", "B_vs_C"]
        pairwise_results = {}

        for pair in pairs:
            preferences = []
            total_groups = 0

            # Collect preferences for this pair across all groups
            for group_key in ["core", "25", "50", "75"]:
                if group_key in groups and pair in groups[group_key]:
                    preferences.append(groups[group_key][pair])
                    total_groups += 1

            if preferences:
                # Find the most common preference
                from collections import Counter

                preference_counts = Counter(preferences)
                dominant_pref, count = preference_counts.most_common(1)[0]

                # Calculate consistency
                consistent_groups = count
                percentage = (
                    (consistent_groups / total_groups * 100)
                    if total_groups > 0
                    else 0.0
                )

                # Format dominant preference (e.g., "A" -> "A>B")
                pair_vectors = pair.split("_vs_")
                if dominant_pref == pair_vectors[0]:
                    dominant_preference = f"{pair_vectors[0]}>{pair_vectors[1]}"
                else:
                    dominant_preference = f"{pair_vectors[1]}>{pair_vectors[0]}"

                pairwise_results[pair] = {
                    "consistent_groups": consistent_groups,
                    "total_groups": total_groups,
                    "percentage": percentage,
                    "dominant_preference": dominant_preference,
                }

        return pairwise_results

    def get_full_transitivity_report(self, choices: List[Dict]) -> Dict:
        """
        Generate complete transitivity analysis across all groups.

        Returns:
            {
                'core': {'is_transitive': True, 'order': 'A>B>C'},
                '25': {'is_transitive': True, 'order': 'A>C>B'},
                '50': {'is_transitive': True, 'order': 'A>B>C'},
                '75': {'is_transitive': True, 'order': 'A>B>C'},
                'transitivity_rate': 100.0,  # percentage of transitive groups
                'order_stability_score': 75.0  # percentage with same order
            }
        """
        groups = self.extract_preferences_by_group(choices)
        report = {}

        # Analyze each group
        group_results = []
        orders = []

        for group_key in ["core", "25", "50", "75"]:
            if group_key in groups and groups[group_key]:
                order, is_transitive = self.determine_preference_order(
                    groups[group_key]
                )
                result = {
                    "is_transitive": is_transitive,
                    "order": order,
                    "comparisons": groups[group_key],
                }
                group_results.append(result)
                if is_transitive and order != "Incomplete":
                    orders.append(order)
            else:
                result = {"is_transitive": False, "order": "No Data", "comparisons": {}}
                group_results.append(result)

            report[group_key] = result

        # Calculate overall metrics
        transitive_count = sum(1 for r in group_results if r["is_transitive"])
        total_groups = len([r for r in group_results if r["order"] != "No Data"])

        transitivity_rate = (
            (transitive_count / total_groups * 100) if total_groups > 0 else 0.0
        )

        # Calculate order stability with proper edge case handling
        if not orders:
            order_stability = "N/A"  # No transitive groups
        elif len(set(orders)) == len(orders):
            order_stability = 0.0  # All orders unique - no consistency
        else:
            # At least some orders repeat
            most_common_order = max(set(orders), key=orders.count)
            order_stability = orders.count(most_common_order) / len(orders) * 100

        report["transitivity_rate"] = transitivity_rate
        report["order_stability_score"] = order_stability

        # Add pairwise consistency analysis
        pairwise_consistency = self._analyze_pairwise_consistency(groups)
        report["pairwise_consistency"] = pairwise_consistency

        return report
