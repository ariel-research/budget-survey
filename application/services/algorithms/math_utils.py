import math
from typing import Generator, Tuple

import numpy as np


def simplex_points(
    num_variables: int,
    side_length: int = 100,
    step: int = 5,
    min_value: int = 0,
) -> Generator[Tuple[int, ...], None, None]:
    """
    Generate lattice points on a discrete simplex grid.

    Args:
        num_variables: Number of coordinates per vector.
        side_length: The total sum required across all coordinates (e.g., 100).
        step: The increment between allowed values; coordinates will be
            multiples of this step.
        min_value: Minimum allowed value per coordinate (rounded up to step).

    Yields:
        Tuples representing valid coordinate combinations that sum exactly
        to side_length.
    """
    if num_variables <= 0:
        raise ValueError("num_variables must be positive")
    if side_length % step != 0:
        raise ValueError(
            f"side_length ({side_length}) must be divisible by step ({step})"
        )

    total_steps = side_length // step
    min_steps_per_var = math.ceil(min_value / step)

    if num_variables * min_steps_per_var > total_steps:
        return

    def generate(
        vars_left: int, remaining_steps: int
    ) -> Generator[Tuple[int, ...], None, None]:
        if vars_left == 1:
            yield (remaining_steps * step,)
            return

        min_needed_for_rest = (vars_left - 1) * min_steps_per_var
        start = min_steps_per_var
        end = remaining_steps - min_needed_for_rest

        for steps_taken in range(start, end + 1):
            value = steps_taken * step
            for rest in generate(vars_left - 1, remaining_steps - steps_taken):
                yield (value,) + rest

    yield from generate(num_variables, total_steps)


def rankdata(a: np.ndarray, method: str = "average") -> np.ndarray:
    """
    Assign ranks to data, handling ties appropriately.

    This is a minimal implementation equivalent to scipy.stats.rankdata
    with method='average'.

    Args:
        a: Array of values to rank
        method: Method for handling ties ('average' supported)

    Returns:
        Array of ranks (1-based, same shape as input)
    """
    arr = np.asarray(a)
    sorter = np.argsort(arr)
    inv = np.empty(sorter.size, dtype=np.intp)
    inv[sorter] = np.arange(sorter.size, dtype=np.intp)

    if method == "average":
        # For average method, we need to handle ties
        arr_sorted = arr[sorter]
        obs = np.r_[True, arr_sorted[1:] != arr_sorted[:-1]]
        dense = obs.cumsum()[inv]

        # Count occurrences of each unique value
        count = np.r_[np.nonzero(obs)[0], len(obs)]

        # Calculate average ranks for tied values
        ranks = np.zeros(len(arr))
        for i in range(len(count) - 1):
            start_rank = count[i] + 1
            end_rank = count[i + 1]
            avg_rank = (start_rank + end_rank) / 2
            ranks[dense == (i + 1)] = avg_rank

        return ranks
    else:
        # Default ordinal ranking
        return inv.astype(float) + 1
