import os
import sys
import time


def _ensure_repo_on_path() -> None:
    """
    Ensure repo root is on sys.path when running as:
        python tests/performance/reproduce_issue.py
    """
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)


def main() -> None:
    _ensure_repo_on_path()

    from application.services.pair_generation.rank_strategies import (
        L1VsLeontiefRankStrategy,
    )

    # Worst-case-ish extreme vector for N=5, step=5.
    user_vector = (95, 5, 0, 0, 0)

    # Defaults: grid_step=5 inside GenericRankStrategy; min_component configured in strategy.
    strategy = L1VsLeontiefRankStrategy(grid_step=None)

    start = time.perf_counter()
    pairs = strategy.generate_pairs(user_vector=user_vector, n=10, vector_size=5)
    elapsed = time.perf_counter() - start

    print(
        f"Generated {len(pairs)} pairs in {elapsed:.3f}s for user_vector={user_vector}"
    )

    assert elapsed < 1.0, f"Performance regression: expected < 1.0s, got {elapsed:.3f}s"


if __name__ == "__main__":
    main()
