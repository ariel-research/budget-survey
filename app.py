from flask import Flask
from app.routes import main as main_blueprint
from logging_config import setup_logging

def create_app():
    app = Flask(__name__, 
                template_folder='app/templates',
                static_folder='app/static')
    setup_logging()
    app.register_blueprint(main_blueprint)
    
    return app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)