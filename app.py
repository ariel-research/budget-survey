from typing import Optional, Type

from dotenv import load_dotenv
from flask import Flask, render_template

from application.translations import get_current_language, get_translation
from config import Config, get_config
from database import db
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
        }

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
    app.register_blueprint(survey_routes, url_prefix="/")
    app.register_blueprint(report_routes)
    app.register_blueprint(dashboard_routes, url_prefix="/surveys")
    app.register_blueprint(responses_routes, url_prefix="/surveys")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=app.config["PORT"], debug=app.config["DEBUG"])
