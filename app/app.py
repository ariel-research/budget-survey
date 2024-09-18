from flask import Flask
from app.routes import main as main_blueprint
from logging_config import setup_logging

def create_app():
    app = Flask(__name__)
    
    # Set up logging
    setup_logging()
    
    # Register the blueprint
    app.register_blueprint(main_blueprint)
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5001, debug=True)