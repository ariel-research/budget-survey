from typing import Optional, Type

from dotenv import load_dotenv
from flask import Flask

from application.translations import get_current_language, get_translation
from config import Config, get_config
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

    # Register template utilities
    @app.context_processor
    def utility_processor() -> dict:
        """Make utility functions available to all templates."""
        return {
            "get_current_language": get_current_language,
            "get_translation": get_translation,
        }

    from application.routes.survey import survey_routes

    # from application.routes.report import report_routes
    from application.routes.utils import util_routes

    app.register_blueprint(survey_routes, url_prefix="/")
    # app.register_blueprint(report_routes, url_prefix='/report')
    app.register_blueprint(util_routes)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=app.config["PORT"], debug=app.config["DEBUG"])
