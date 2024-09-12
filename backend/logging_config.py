import os
import logging
import logging.config

def setup_logging():
    """Configures the logging system with console and file handlers."""

    # Get the project's root directory
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    log_dir = os.path.join(project_root, 'logs')
    
    # Create the directory if it does not exist
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

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
            },
            'file': {
                'class': 'logging.FileHandler',
                'formatter': 'default',
                'filename': os.path.join(log_dir, 'app.log'),  # Log file location
            },
        },
        'root': {
            'level': 'DEBUG',  # Set the default logging level
            'handlers': ['console', 'file']
        }
    })
