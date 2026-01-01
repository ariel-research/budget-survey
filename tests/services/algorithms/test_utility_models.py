import numpy as np
import pytest

from application.services.algorithms.utility_models import (
    AntiLeontiefUtilityModel,
    KLUtilityModel,
    L1UtilityModel,
    L2UtilityModel,
    LeontiefUtilityModel,
)


def test_l1_utility_model_calculation():
    utility_model = L1UtilityModel()
    user_vec = (50, 50)
    candidate_a = (60, 40)
    candidate_b = (70, 30)

    # |50-60| + |50-40| = 10 + 10 = 20
    assert utility_model.calculate(user_vec, candidate_a) == -20.0
    # |50-70| + |50-30| = 20 + 20 = 40
    assert utility_model.calculate(user_vec, candidate_b) == -40.0


def test_l2_utility_model_calculation():
    utility_model = L2UtilityModel()
    user_vec = (50, 50)
    # distance = sqrt(10^2 + (-10)^2) = sqrt(200) ≈ 14.142
    candidate_a = (40, 60)
    candidate_b = (50, 50)  # distance 0

    assert pytest.approx(utility_model.calculate(user_vec, candidate_a)) == -np.sqrt(
        200
    )
    assert utility_model.calculate(user_vec, candidate_b) == 0.0

    # Another 3D case: (40, 30, 30) to (50, 25, 25)
    # diff: (10, -5, -5) -> L2: sqrt(100 + 25 + 25) = sqrt(150)
    user_vec_2 = (40, 30, 30)
    candidate_c = (50, 25, 25)
    assert pytest.approx(utility_model.calculate(user_vec_2, candidate_c)) == -np.sqrt(
        150
    )


def test_leontief_utility_model_calculation():
    utility_model = LeontiefUtilityModel()
    user_vec = (10, 90)
    candidate_a = (5, 95)  # Ratios: 5/10=0.5, 95/90=1.05 -> min 0.5
    candidate_b = (2, 98)  # Ratios: 2/10=0.2, 98/90=1.08 -> min 0.2

    assert pytest.approx(utility_model.calculate(user_vec, candidate_a)) == 0.5
    assert pytest.approx(utility_model.calculate(user_vec, candidate_b)) == 0.2


def test_high_dimensional_vectors():
    """Test utility models with 5D vectors summing to 100."""
    user_vec = (20, 20, 20, 20, 20)
    candidate = (25, 15, 20, 10, 30)

    # L1: |5| + |-5| + |0| + |-10| + |10| = 30
    assert L1UtilityModel().calculate(user_vec, candidate) == -30.0

    # L2: sqrt(5^2 + (-5)^2 + 0^2 + (-10)^2 + 10^2) = sqrt(250)
    assert pytest.approx(L2UtilityModel().calculate(user_vec, candidate)) == -np.sqrt(
        250
    )

    # Leontief: min(25/20, 15/20, 20/20, 10/20, 30/20) = 0.5
    assert pytest.approx(LeontiefUtilityModel().calculate(user_vec, candidate)) == 0.5


def test_perfect_match():
    """Verify utility models behave correctly when vectors are identical."""
    vec = (33.3, 33.3, 33.4)
    assert L1UtilityModel().calculate(vec, vec) == 0.0
    assert L2UtilityModel().calculate(vec, vec) == 0.0
    assert LeontiefUtilityModel().calculate(vec, vec) == 1.0


def test_leontief_bottleneck_zero():
    """If a candidate gives 0 to a category the user wants, score must be 0."""
    utility_model = LeontiefUtilityModel()
    user_vec = (10, 40, 50)
    candidate = (0, 50, 50)  # 0/10 = 0.0 ratio
    assert utility_model.calculate(user_vec, candidate) == 0.0


def test_leontief_with_user_zeros():
    """If user wants 0 in a category, it should not affect the Leontief score."""
    utility_model = LeontiefUtilityModel()
    user_vec = (50, 0, 50)
    candidate = (25, 50, 25)  # Ratios: 25/50=0.5, (skip), 25/50=0.5 -> min 0.5
    assert utility_model.calculate(user_vec, candidate) == 0.5

    # Edge case: all funding in one category vs user wants 0 there
    user_vec_2 = (0, 0, 100)
    candidate_2 = (20, 20, 60)  # ratio: 60/100 = 0.6
    assert utility_model.calculate(user_vec_2, candidate_2) == 0.6


def test_utility_model_statelessness():
    utility_model = L1UtilityModel()
    user_vec = (50, 50)
    candidate = (60, 40)

    score1 = utility_model.calculate(user_vec, candidate)
    score2 = utility_model.calculate(user_vec, candidate)
    assert score1 == score2 == -20.0


def test_anti_leontief_utility_model_calculation():
    """
    Test Anti-Leontief Utility Model.
    Formula: U = -max(q_i / p_i) for all i where p_i > 0.
    """
    utility_model = AntiLeontiefUtilityModel()
    user_vec = (10, 90)

    # Case 1: Max ratio is 3.0
    # q/p: 30/10 = 3.0, 70/90 = 0.77...
    # Max is 3.0. Score = -3.0
    candidate_a = (30, 70)
    assert pytest.approx(utility_model.calculate(user_vec, candidate_a)) == -3.0

    # Case 2: Max ratio is determined by the other component
    # q=[5, 95], p=[10, 90]
    # Ratios: 5/10=0.5, 95/90=1.055...
    # Max is 1.055... Score = -1.055...
    candidate_b = (5, 95)
    assert pytest.approx(utility_model.calculate(user_vec, candidate_b)) == -(95 / 90)

    # Case 3: Ignore p_i = 0
    # user=[50, 0, 50]
    # cand=[60, 20, 20]
    # Ratios: 60/50=1.2, 20/0 (skip), 20/50=0.4
    # Max is 1.2. Score = -1.2
    user_vec_zeros = (50, 0, 50)
    candidate_zeros = (60, 20, 20)
    assert (
        pytest.approx(utility_model.calculate(user_vec_zeros, candidate_zeros)) == -1.2
    )


def test_kl_utility_model_calculation():
    """
    Test Kullback-Leibler Utility Model.
    Formula: U = -sum(p_i * ln(p_i / q_i)) after normalization.
    """
    utility_model = KLUtilityModel()

    # Case 1: Standard divergence
    # p=[10, 90] -> normalized [0.1, 0.9]
    # q=[30, 70] -> normalized [0.3, 0.7]
    # KL = 0.1 * ln(0.1/0.3) + 0.9 * ln(0.9/0.7)
    #    = 0.1 * ln(1/3) + 0.9 * ln(9/7)
    #    = 0.1 * (-1.09861) + 0.9 * (0.25131)
    #    = -0.10986 + 0.22618 = 0.11632
    # Score = -0.11632
    user_vec = (10, 90)
    candidate_a = (30, 70)

    p_norm = np.array([0.1, 0.9])
    q_norm = np.array([0.3, 0.7])
    expected_divergence = np.sum(p_norm * np.log(p_norm / q_norm))

    assert (
        pytest.approx(utility_model.calculate(user_vec, candidate_a))
        == -expected_divergence
    )

    # Case 2: q contains 0 (epsilon handling)
    # p=[50, 50]
    # q=[100, 0] -> normalized [1.0, 0.0]
    # KL = 0.5 * ln(0.5/1.0) + 0.5 * ln(0.5 / epsilon)
    user_vec_2 = (50, 50)
    candidate_zero = (100, 0)
    score = utility_model.calculate(user_vec_2, candidate_zero)
    epsilon = 1e-10
    expected_divergence = 0.5 * np.log(0.5) + 0.5 * np.log(0.5 / epsilon)
    assert pytest.approx(score) == -expected_divergence
