"""Test suite for Asymmetric Loss Distribution strategy."""

import time

import pytest

from application.exceptions import UnsuitableForStrategyError
from application.services.pair_generation.asymmetric_loss_distribution import (
    AsymmetricLossDistributionStrategy,
)

# Test constants
EXPECTED_VALID_VECTORS = 171
MAX_GENERATION_TIME = 3.0
PERFORMANCE_TIMEOUT = 10.0


def enumerate_all_valid_vectors():
    """Enumerate all valid 3D budget vectors."""
    valid_vectors = []
    for a in range(5, 96, 5):
        for b in range(5, 96, 5):
            c = 100 - a - b
            if 5 <= c <= 95 and c % 5 == 0:
                valid_vectors.append((a, b, c))
    return valid_vectors


def validate_pair_structure(pair, pair_index):
    """Validate basic pair structure and properties."""
    if "Concentrated Changes" not in pair or "Distributed Changes" not in pair:
        return f"Pair {pair_index} missing required vector keys"

    for key, value in pair.items():
        if isinstance(value, tuple):
            if not (
                len(value) == 3
                and sum(value) == 100
                and all(0 <= v <= 100 for v in value)
            ):
                return f"Invalid vector in pair {pair_index}: {value}"
    return None


@pytest.fixture
def strategy():
    """Fixture for AsymmetricLossDistributionStrategy."""
    return AsymmetricLossDistributionStrategy()


def test_strategy_name(strategy):
    """Test if strategy name is correct."""
    assert strategy.get_strategy_name() == "asymmetric_loss_distribution"


def test_generates_exactly_12_pairs(strategy):
    """Test that the strategy generates exactly 12 pairs."""
    user_vector = (35, 35, 30)
    pairs = strategy.generate_pairs(user_vector)
    assert len(pairs) == 12


def test_rejects_users_with_zero_values(strategy):
    """Test that the strategy rejects users with zeros in their budget."""
    with pytest.raises(UnsuitableForStrategyError):
        strategy.generate_pairs((50, 50, 0))


def test_comprehensive_algorithm_validation(strategy):
    """
    Comprehensive validation for all valid vectors.
    Ensures the algorithm works for 100% of the valid input space,
    generates 12 unique pairs, and performs within time limits.
    """
    print("\n=== COMPREHENSIVE ALGORITHM VALIDATION ===")
    valid_vectors = enumerate_all_valid_vectors()
    assert (
        len(valid_vectors) == EXPECTED_VALID_VECTORS
    ), f"Expected {EXPECTED_VALID_VECTORS} vectors, got {len(valid_vectors)}"

    failed_vectors = []
    timing_results = []

    for i, user_vector in enumerate(valid_vectors, 1):
        print(f"Testing vector {i}/{len(valid_vectors)}: {user_vector}", end=" ... ")
        try:
            start_time = time.time()
            pairs = strategy.generate_pairs(user_vector, n=12, vector_size=3)
            elapsed = time.time() - start_time
            timing_results.append(elapsed)

            if len(pairs) != 12:
                failed_vectors.append(
                    (user_vector, f"Generated {len(pairs)} pairs, expected 12")
                )
                print("FAIL (count)")
                continue

            pair_tuples = set()
            for j, pair in enumerate(pairs):
                error = validate_pair_structure(pair, j)
                if error:
                    failed_vectors.append((user_vector, error))
                    print("FAIL (structure)")
                    break

                vectors = tuple(
                    sorted(v for k, v in pair.items() if isinstance(v, tuple))
                )
                pair_tuples.add(vectors)

            if len(pair_tuples) != 12:
                failed_vectors.append(
                    (
                        user_vector,
                        f"Generated {len(pair_tuples)} unique pairs, expected 12",
                    )
                )
                print("FAIL (uniqueness)")
                continue

            print(f"✓ ({elapsed:.3f}s)")
        except Exception as e:
            failed_vectors.append((user_vector, str(e)))
            print(f"FAIL (exception: {type(e).__name__})")

    if failed_vectors:
        print(f"\n❌ ALGORITHM FAILURES ({len(failed_vectors)}):")
        for vec, err in failed_vectors[:5]:
            print(f"  {vec}: {err}")
        if len(failed_vectors) > 5:
            print(f"  ... and {len(failed_vectors) - 5} more")

    assert (
        not failed_vectors
    ), f"Strategy failed for {len(failed_vectors)}/{len(valid_vectors)} vectors"

    avg_time = sum(timing_results) / len(timing_results)
    assert (
        avg_time < MAX_GENERATION_TIME
    ), f"Average time {avg_time:.2f}s exceeds performance limit"

    print("✅ COMPREHENSIVE VALIDATION COMPLETE")
