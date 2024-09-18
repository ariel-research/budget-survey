from flask import Flask
from logging_config import setup_logging
import logging

def create_app():
    setup_logging()
    app = Flask(__name__)
     
    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app