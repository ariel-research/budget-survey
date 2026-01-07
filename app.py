import hashlib
from typing import Optional, Type

from dotenv import load_dotenv
from flask import Flask, render_template

from application.translations import get_current_language, get_translation
from config import Config, get_config
from database import db
from database.queries import get_survey_instructions
from logging_config import setup_logging

load_dotenv()


def create_app(config_class: Optional[Type[Config]] = None) -> Flask:
    """
    Create and configure the Flask application.

    Args:
        config_class: Optional configuration class to use instead of default

    Returns:
        Configured Flask application instance
    """
    app = Flask(
        __name__,
        template_folder="application/templates",
        static_folder="application/static",
    )
    setup_logging()

    # Load configuration
    if config_class is None:
        app.config.from_object(get_config())
    else:
        app.config.from_object(config_class)

    app.secret_key = app.config["SECRET_KEY"]

    db.init_app(app)  # Initialize database handling (registers close_db)

    # Register template utilities
    @app.context_processor
    def utility_processor() -> dict:
        """Make utility functions available to all templates."""
        return {
            "get_current_language": get_current_language,
            "get_translation": get_translation,
            "get_survey_instructions": get_survey_instructions,
        }

    @app.template_filter("strategy_color")
    def strategy_color_filter(strategy_name: str) -> str:
        """
        Generates a deterministic HSL color based on the strategy name.

        This ensures that a specific strategy always appears with the same color
        across the application, without needing manual CSS maintenance.

        Args:
            strategy_name (str): The raw strategy identifier (e.g. "Triangle Test")

        Returns:
            str: A CSS HSL color string (e.g. "hsl(120, 65%, 40%)")
        """
        if not strategy_name:
            return "#6366F1"  # Default Indigo fallback

        # 1. Normalize input: Remove whitespace and force lowercase.
        # This prevents "Test Strategy" and "test_strategy" from having different colors.
        normalized_name = strategy_name.strip().lower()

        # 2. Create a consistent hash
        hash_obj = hashlib.md5(normalized_name.encode("utf-8"))
        hash_int = int(hash_obj.hexdigest(), 16)

        # 3. Calculate Hue (0-360)
        # We multiply by 137 (an approximation of the Golden Angle) to ensure
        # that similar string names result in visually distinct colors.
        hue = (hash_int * 137) % 361

        # 4. Return HSL
        # Saturation: 65% -> High enough to be vibrant, low enough to look professional.
        # Lightness: 40% -> Kept low (dark) to ensure WCAG AA contrast compliance with white text.
        return f"hsl({hue}, 65%, 40%)"

    # Register error handlers
    @app.errorhandler(400)
    def bad_request(e):
        """Handle 400 Bad Request errors."""
        return (
            render_template(
                "error.html",
                message=e.description,
            ),
            400,
        )

    @app.errorhandler(404)
    def not_found(e):
        """Handle 404 Not Found errors."""
        return (
            render_template(
                "error.html",
                message=e.description,
            ),
            404,
        )

    @app.errorhandler(500)
    def internal_server_error(e):
        """Handle 500 Internal Server Error."""
        return (
            render_template(
                "error.html",
                message=e.description,
            ),
            500,
        )

    from application.routes.dashboard import dashboard_routes
    from application.routes.report import report_routes
    from application.routes.survey import survey_routes
    from application.routes.survey_responses import responses_routes
    from application.routes.utils import util_routes

    app.register_blueprint(util_routes)
    app.register_blueprint(dashboard_routes, url_prefix="/")
    app.register_blueprint(survey_routes, url_prefix="/take-survey")
    app.register_blueprint(report_routes)
    app.register_blueprint(responses_routes, url_prefix="/surveys")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=app.config["PORT"], debug=app.config["DEBUG"])
