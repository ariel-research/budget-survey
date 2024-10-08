import os

from dotenv import load_dotenv
from flask import Flask

from application.routes import main as main_blueprint
from config import get_config
from logging_config import setup_logging

load_dotenv()


def create_app(config_class=None):
    app = Flask(
        __name__,
        template_folder="application/templates",
        static_folder="application/static",
    )
    setup_logging()

    # Load the configuration
    if config_class is None:
        app.config.from_object(get_config())
    else:
        app.config.from_object(config_class)

    app.secret_key = os.environ.get("FLASK_SECRET_KEY")
    app.register_blueprint(main_blueprint)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=app.config["PORT"], debug=app.config["DEBUG"])
