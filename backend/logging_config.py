import os
import logging
import logging.config

def setup_logging():
    """Configures the logging system with console and file handlers."""

    # Get the project's root directory
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    log_dir = os.path.join(project_root, 'logs')
    
    # Create the directory if it does not exist
    try:
        os.makedirs(log_dir, exist_ok=True)
        print(f"Log directory created/verified at: {log_dir}")
    except Exception as e:
        print(f"Error creating log directory: {e}")

    log_file = os.path.join(log_dir, 'app.log')

    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'default': {
                'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'default',
                'level': 'DEBUG',
            },
            'file': {
                'class': 'logging.FileHandler',
                'formatter': 'default',
                'filename': log_file,
                'level': 'DEBUG',
            },
        },
        'root': {
            'level': 'DEBUG',  # Set to DEBUG to capture all levels of logs
            'handlers': ['console', 'file']
        }
    })
