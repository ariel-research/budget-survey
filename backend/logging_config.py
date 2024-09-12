import logging
import logging.config

def setup_logging():
    """Configures the logging system with console and file handlers."""
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
                'filename': './logs/app.log',  # Log file location
            },
        },
        'root': {
            'level': 'DEBUG',  # Set the default logging level
            'handlers': ['console', 'file']
        }
    })
