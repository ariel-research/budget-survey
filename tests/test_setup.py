import sys
from pathlib import Path
from typing import Any


def setup_test_environment() -> Any:
    """
    Setup test environment and return create_app function.

    Returns:
        Any: The create_app function
    """
    # Add project root to path
    project_root = str(Path(__file__).parent.parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from app import create_app

    return create_app
