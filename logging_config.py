import logging
import logging.config
import os
import traceback


def setup_logging(level="INFO"):
    """Configures the logging system with console and file handlers."""

    try:
        # Get the project's root directory
        project_root = os.path.dirname(os.path.abspath(__file__))
        log_dir = os.path.join(project_root, "logs")

        print(f"Attempting to create log directory at: {log_dir}")

        # Create the directory if it does not exist
        os.makedirs(log_dir, exist_ok=True)
        print(f"Log directory created/verified at: {log_dir}")

        log_file = os.path.join(log_dir, "app.log")
        print(f"Log file will be created at: {log_file}")

        logging.config.dictConfig(
            {
                "version": 1,
                "disable_existing_loggers": False,
                "formatters": {
                    "default": {
                        "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
                    },
                },
                "handlers": {
                    "console": {
                        "class": "logging.StreamHandler",
                        "formatter": "default",
                        "level": "DEBUG",
                    },
                    "file": {
                        "class": "logging.FileHandler",
                        "formatter": "default",
                        "filename": log_file,
                        "level": "DEBUG",
                    },
                },
                "root": {
                    "level": level,
                    "handlers": ["console", "file"],
                },
            }
        )

        # Silence specific loggers
        logging.getLogger("__init__").setLevel(logging.WARNING)
        logging.getLogger("weasyprint").setLevel(logging.WARNING)
        logging.getLogger("fontTools").setLevel(logging.WARNING)

    except Exception as e:
        print(f"Error setting up logging: {e}")
        print("Traceback:")
        traceback.print_exc()
