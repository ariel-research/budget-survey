import os
import sys

# Add the parent directory to the system path to allow importing from the backend module.
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

import pytest

from utils.analyzer_utils import is_sum_optimized


def test_is_sum_optimized():
    # Test case 1: User optimizes for sum difference
    assert is_sum_optimized((50, 30, 20), (40, 35, 25), (45, 30, 25), 1)

    # Test case 2: User does not optimize for sum difference
    assert not is_sum_optimized((50, 30, 20), (40, 35, 25), (45, 30, 25), 2)

    # Test case 3: User does not optimize for sum difference
    assert not is_sum_optimized((50, 30, 20), (45, 30, 25), (40, 35, 25), 1)


def test_is_sum_optimized_invalid_input():
    # Test case 4: Invalid user choice
    with pytest.raises(ValueError):
        is_sum_optimized((50, 30, 20), (40, 35, 25), (45, 30, 25), 3)
