"""Module for analyzing user choices in surveys."""

import logging
from typing import Any, Dict, Optional

from analysis.utils.analysis_utils import get_all_completed_survey_responses

logger = logging.getLogger(__name__)


def analyze_survey_choices(survey_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Analyze survey response choices.

    Args:
        survey_id: Optional survey ID to filter responses

    Returns:
        Dict containing analysis results:
        - user_choices: Table of user choices per survey
        - choice_distribution: Distribution of option 1 vs option 2 choices per pair
        - total_responses: Number of responses
    """
    try:
        # Get responses
        df = get_all_completed_survey_responses()
        if survey_id:
            df = df[df["survey_id"] == survey_id]

        # Process user choices
        user_choices = []
        # Initialize counters properly
        choice_distribution = {"option_1": 0, "option_2": 0}

        for _, row in df.iterrows():
            user_data = {
                "user_id": row["user_id"],
                "survey_id": row["survey_id"],
                "choices": [],
            }

            for comp in row["comparisons"]:
                choice = comp["user_choice"]
                user_data["choices"].append(choice)

                # Update distribution
                if choice == 1:
                    choice_distribution["option_1"] += 1
                else:
                    choice_distribution["option_2"] += 1

            user_choices.append(user_data)

        return {
            "user_choices": user_choices,
            "choice_distribution": choice_distribution,
            "total_responses": len(df),
        }

    except Exception as e:
        logger.error(f"Error analyzing survey choices: {str(e)}")
        raise
