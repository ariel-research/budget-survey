from flask import Flask
from dotenv import load_dotenv
import os

from application.routes import main as main_blueprint
from logging_config import setup_logging

load_dotenv()

def create_app():
    app = Flask(__name__, 
                template_folder='application/templates',
                static_folder='application/static')
    setup_logging()
    app.secret_key = os.environ.get('FLASK_SECRET_KEY')
    app.register_blueprint(main_blueprint)
    
    return app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)