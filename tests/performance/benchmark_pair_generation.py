import os
import sys
import time


def _ensure_repo_on_path() -> None:
    """
    Ensure repo root is on sys.path when running as a standalone script.
    """
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)


def test_pair_generation_performance() -> None:
    """
    Benchmarks the L1VsLeontiefRankStrategy for N=5 surveys (worst-case scenario).
    Ensures that pair generation remains below the 1.0s threshold to prevent regressions.
    """
    _ensure_repo_on_path()

    from application.services.pair_generation.rank_strategies import (
        L1VsLeontiefRankStrategy,
    )

    # Use a high-concentration vector that forces a full pool scan
    extreme_user_vector = (95, 5, 0, 0, 0)
    target_pair_count = 10
    vector_dimension = 5

    strategy = L1VsLeontiefRankStrategy(grid_step=None)

    print(
        f"Executing performance benchmark (N={vector_dimension}, vector={extreme_user_vector})..."
    )

    start_time = time.perf_counter()
    pairs = strategy.generate_pairs(
        user_vector=extreme_user_vector,
        n=target_pair_count,
        vector_size=vector_dimension,
    )
    execution_time = time.perf_counter() - start_time

    print(f"Benchmark Result: Generated {len(pairs)} pairs in {execution_time:.3f}s.")

    # Assert performance stays within acceptable bounds (< 1.0s)
    performance_threshold = 1.0
    assert execution_time < performance_threshold, (
        f"Performance regression: Expected < {performance_threshold}s, "
        f"got {execution_time:.3f}s"
    )
    print("Verification Successful: Performance is within limits.")


if __name__ == "__main__":
    test_pair_generation_performance()
