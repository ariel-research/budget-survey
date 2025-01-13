import logging
from datetime import datetime

from flask import Blueprint, abort, render_template

from analysis.survey_choice_analysis import analyze_survey_choices
from analysis.utils.analysis_utils import load_data
from analysis.utils.visualization_utils import (
    create_choice_distribution_chart,
    visualize_overall_majority_choice_distribution,
    visualize_per_survey_answer_percentages,
    visualize_total_answer_percentage_distribution,
    visualize_user_survey_majority_choices,
)
from application.services.pair_generation.base import StrategyRegistry
from application.translations import get_translation
from database.queries import get_survey_pair_generation_config

logger = logging.getLogger(__name__)
dashboard_routes = Blueprint("dashboard", __name__)


@dashboard_routes.route("/dashboard/")
@dashboard_routes.route("/dashboard")
def dashboard():
    """Render the analytics dashboard with visualizations and metrics."""
    try:
        data = load_data()

        # Generate visualization charts
        charts = {
            "survey_percentages": visualize_per_survey_answer_percentages(
                data["summary"]
            ),
            "majority_choices": visualize_user_survey_majority_choices(
                data["optimization"]
            ),
            "overall_distribution": visualize_overall_majority_choice_distribution(
                data["summary"]
            ),
            "answer_distribution": visualize_total_answer_percentage_distribution(
                data["summary"]
            ),
        }

        # Calculate metrics
        total_row = data["summary"].loc[data["summary"]["survey_id"] == "Total"].iloc[0]
        metrics = {
            "total_surveys": len(data["summary"]) - 1,  # Exclude "Total" row
            "total_participants": total_row["total_survey_responses"],
            "completion_rate": round(
                (data["optimization"]["result"].count() / len(data["optimization"]))
                * 100,
                1,
            ),
            "last_update_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }

        # Pass translations using 'dashboard' section
        translations = {
            "title": get_translation("title", "dashboard"),
            "last_updated": get_translation("last_updated", "dashboard"),
            "refresh": get_translation("refresh", "dashboard"),
            "total_surveys": get_translation("total_surveys", "dashboard"),
            "total_participants": get_translation("total_participants", "dashboard"),
            "completion_rate": get_translation("completion_rate", "dashboard"),
            "survey_percentages": get_translation("survey_percentages", "dashboard"),
            "majority_choices": get_translation("majority_choices", "dashboard"),
            "overall_distribution": get_translation(
                "overall_distribution", "dashboard"
            ),
            "answer_distribution": get_translation("answer_distribution", "dashboard"),
            "expand": get_translation("expand", "dashboard"),
            "download": get_translation("download", "dashboard"),
        }

        return render_template(
            "dashboard.html", charts=charts, translations=translations, **metrics
        )

    except Exception as e:
        logger.error(f"Error rendering dashboard: {str(e)}", exc_info=True)
        abort(500, description=get_translation("messages.dashboard_error"))


@dashboard_routes.route("/analyze/<int:survey_id>")
def analyze_survey(survey_id: int):
    try:
        # Get survey configuration
        config = get_survey_pair_generation_config(survey_id)
        if not config:
            abort(404, description=get_translation("survey_not_found", "messages"))

        # Get strategy
        strategy = StrategyRegistry.get_strategy(config["strategy"])
        option_labels = strategy.get_option_labels()

        # Get analysis
        analysis = analyze_survey_choices(survey_id)

        # Generate chart
        chart = create_choice_distribution_chart(
            analysis["choice_distribution"], option_labels
        )

        return render_template(
            "analyze.html",
            survey_id=survey_id,
            analysis=analysis,
            chart=chart,
            option_labels=option_labels,
        )

    except Exception as e:
        logger.error(f"Error in survey analysis: {str(e)}")
        abort(500, description=get_translation("survey_retrieval_error", "messages"))
