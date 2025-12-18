import numpy as np
import pytest

from application.services.algorithms.metrics import L1Metric, L2Metric, LeontiefMetric


def test_l1_metric_calculation():
    metric = L1Metric()
    user_vec = (50, 50)
    candidate_a = (60, 40)
    candidate_b = (70, 30)

    # |50-60| + |50-40| = 10 + 10 = 20
    assert metric.calculate(user_vec, candidate_a) == -20.0
    # |50-70| + |50-30| = 20 + 20 = 40
    assert metric.calculate(user_vec, candidate_b) == -40.0


def test_l2_metric_calculation():
    metric = L2Metric()
    user_vec = (50, 50)
    # distance = sqrt(10^2 + (-10)^2) = sqrt(200) ≈ 14.142
    candidate_a = (40, 60)
    candidate_b = (50, 50)  # distance 0

    assert pytest.approx(metric.calculate(user_vec, candidate_a)) == -np.sqrt(200)
    assert metric.calculate(user_vec, candidate_b) == 0.0

    # Another 3D case: (40, 30, 30) to (50, 25, 25)
    # diff: (10, -5, -5) -> L2: sqrt(100 + 25 + 25) = sqrt(150)
    user_vec_2 = (40, 30, 30)
    candidate_c = (50, 25, 25)
    assert pytest.approx(metric.calculate(user_vec_2, candidate_c)) == -np.sqrt(150)


def test_leontief_metric_calculation():
    metric = LeontiefMetric()
    user_vec = (10, 90)
    candidate_a = (5, 95)  # Ratios: 5/10=0.5, 95/90=1.05 -> min 0.5
    candidate_b = (2, 98)  # Ratios: 2/10=0.2, 98/90=1.08 -> min 0.2

    assert pytest.approx(metric.calculate(user_vec, candidate_a)) == 0.5
    assert pytest.approx(metric.calculate(user_vec, candidate_b)) == 0.2


def test_high_dimensional_vectors():
    """Test metrics with 5D vectors summing to 100."""
    user_vec = (20, 20, 20, 20, 20)
    candidate = (25, 15, 20, 10, 30)

    # L1: |5| + |-5| + |0| + |-10| + |10| = 30
    assert L1Metric().calculate(user_vec, candidate) == -30.0

    # L2: sqrt(5^2 + (-5)^2 + 0^2 + (-10)^2 + 10^2) = sqrt(250)
    assert pytest.approx(L2Metric().calculate(user_vec, candidate)) == -np.sqrt(250)

    # Leontief: min(25/20, 15/20, 20/20, 10/20, 30/20) = 0.5
    assert pytest.approx(LeontiefMetric().calculate(user_vec, candidate)) == 0.5


def test_perfect_match():
    """Verify metrics behave correctly when vectors are identical."""
    vec = (33.3, 33.3, 33.4)
    assert L1Metric().calculate(vec, vec) == 0.0
    assert L2Metric().calculate(vec, vec) == 0.0
    assert LeontiefMetric().calculate(vec, vec) == 1.0


def test_leontief_bottleneck_zero():
    """If a candidate gives 0 to a category the user wants, score must be 0."""
    metric = LeontiefMetric()
    user_vec = (10, 40, 50)
    candidate = (0, 50, 50)  # 0/10 = 0.0 ratio
    assert metric.calculate(user_vec, candidate) == 0.0


def test_leontief_with_user_zeros():
    """If user wants 0 in a category, it should not affect the Leontief score."""
    metric = LeontiefMetric()
    user_vec = (50, 0, 50)
    candidate = (25, 50, 25)  # Ratios: 25/50=0.5, (skip), 25/50=0.5 -> min 0.5
    assert metric.calculate(user_vec, candidate) == 0.5

    # Edge case: all funding in one category vs user wants 0 there
    user_vec_2 = (0, 0, 100)
    candidate_2 = (20, 20, 60)  # ratio: 60/100 = 0.6
    assert metric.calculate(user_vec_2, candidate_2) == 0.6


def test_metric_statelessness():
    metric = L1Metric()
    user_vec = (50, 50)
    candidate = (60, 40)

    score1 = metric.calculate(user_vec, candidate)
    score2 = metric.calculate(user_vec, candidate)
    assert score1 == score2 == -20.0
