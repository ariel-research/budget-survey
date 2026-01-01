from typing import Tuple

import numpy as np

from application.services.algorithms.utility_model_base import UtilityModel


class L1UtilityModel(UtilityModel):
    """
    Implements L1 (Manhattan) distance as a scoring utility model.

    In the context of budget research, L1 represents the total absolute difference
    between a user's ideal budget and a proposed budget. It measures "total
    disagreement" across all categories.

    Research Context:
        Often used to find "utilitarian" matches where we want to minimize the
        total sum of changes required to reach the ideal.

    Higher Score = Better Match (returns -L1 distance).

    Example:
        User Ideal: [50, 50]
        Candidate A: [60, 40] -> L1 = |50-60| + |50-40| = 20. Score = -20.
        Candidate B: [70, 30] -> L1 = |50-70| + |50-30| = 40. Score = -40.
        A is a better match than B.
    """

    @property
    def name(self) -> str:
        return "l1"

    @property
    def utility_type(self) -> str:
        return "distance"

    def calculate(
        self, user_vec: Tuple[float, ...], candidate_vec: Tuple[float, ...]
    ) -> float:
        user_arr = np.array(user_vec, dtype=float)
        comp_arr = np.array(candidate_vec, dtype=float)
        diff = np.abs(user_arr - comp_arr)
        return -float(np.sum(diff))


class L2UtilityModel(UtilityModel):
    """
    Implements L2 (Euclidean) distance as a scoring utility model.

    L2 represents the "as-the-crow-flies" distance in the budget simplex.
    Unlike L1, L2 penalizes large deviations in a single category more heavily
    than small deviations across many categories (due to squaring).

    Research Context:
        Used when we want to avoid budgets that are "extreme" outliers in any
        specific category relative to the user's preference.

    Higher Score = Better Match (returns -L2 distance).

    Example:
        User Ideal: [50, 50]
        Candidate A: [60, 40] -> L2 = sqrt(10^2 + 10^2) = 14.14. Score = -14.14.
        Candidate B: [50, 50] -> L2 = 0. Score = 0.
    """

    @property
    def name(self) -> str:
        return "l2"

    @property
    def utility_type(self) -> str:
        return "distance"

    def calculate(
        self, user_vec: Tuple[float, ...], candidate_vec: Tuple[float, ...]
    ) -> float:
        user_arr = np.array(user_vec, dtype=float)
        comp_arr = np.array(candidate_vec, dtype=float)
        dist = np.sqrt(np.sum((user_arr - comp_arr) ** 2))
        return -float(dist)


class LeontiefUtilityModel(UtilityModel):
    """
    Implements Leontief ratio as a scoring utility model.

    The Leontief utility model focuses on the "bottleneck" or the category where the
    proposed budget is most deficient relative to the user's ideal. It is
    based on the Leontief utility function: U = min(x_i / a_i).

    Research Context:
        Used to model "Egalitarian" or "Fair" preferences where a budget is
        only as good as its least-satisfied priority. It ensures that the
        user's most critical (but smallest) funding requests are not ignored.

    Higher Score = Better Match (Higher min-ratio).

    Example:
        User Ideal: [10, 90]
        Candidate A: [5, 95]  -> Ratio: [5/10, 95/90] = [0.5, 1.05]. Score = 0.5.
        Candidate B: [2, 98]  -> Ratio: [2/10, 98/90] = [0.2, 1.08]. Score = 0.2.
        Candidate A is much better because it satisfies the 10% priority better.
    """

    @property
    def name(self) -> str:
        return "leontief"

    @property
    def utility_type(self) -> str:
        return "ratio"

    def calculate(
        self, user_vec: Tuple[float, ...], candidate_vec: Tuple[float, ...]
    ) -> float:
        user_arr = np.array(user_vec, dtype=float)
        comp_arr = np.array(candidate_vec, dtype=float)

        # Create mask for non-zero user values to avoid division by zero.
        # This reflects the "skip zeros" rule: if a user didn't fund a category
        # in their ideal, we don't penalize any candidate for its funding level
        # in that category via the ratio utility model.
        non_zero_mask = user_arr > 0

        if not np.any(non_zero_mask):
            # All user values are zero - return 0.0 as the worst possible match score.
            return 0.0

        ratios = comp_arr[non_zero_mask] / user_arr[non_zero_mask]
        return float(np.min(ratios))


class AntiLeontiefUtilityModel(UtilityModel):
    """
    Implements Anti-Leontief ratio as a scoring utility model.

    Logic: Finds the worst *over-funding* ratio.
    Formula: U = -max(q_i / p_i) for all i where p_i > 0.
    Direction: Return negative value (closer to 0 is better).

    Research Context:
        Models "Over-funding aversion". Users dislike when resources are
        "wasted" on categories they care little about, disproportionately
        relative to their preference.
    """

    @property
    def name(self) -> str:
        return "anti_leontief"

    @property
    def utility_type(self) -> str:
        return "ratio"

    def calculate(
        self, user_vec: Tuple[float, ...], candidate_vec: Tuple[float, ...]
    ) -> float:
        user_arr = np.array(user_vec, dtype=float)
        comp_arr = np.array(candidate_vec, dtype=float)

        # Filter p_i > 0 to avoid division by zero
        non_zero_mask = user_arr > 0

        if not np.any(non_zero_mask):
            return 0.0

        ratios = comp_arr[non_zero_mask] / user_arr[non_zero_mask]
        return -float(np.max(ratios))


class KLUtilityModel(UtilityModel):
    """
    Implements Kullback-Leibler (KL) divergence as a scoring utility model.

    Logic: Information divergence.
    Formula: U = -sum(p_i * ln(p_i / q_i)).
    Normalization: Inputs divided by their sum.
    Stability: Use q_i + epsilon in denominator.
    Direction: Return negative value (closer to 0 is better).

    Research Context:
        Models "Information-theoretic asymmetry".
    """

    @property
    def name(self) -> str:
        return "kl"

    @property
    def utility_type(self) -> str:
        return "divergence"

    def calculate(
        self, user_vec: Tuple[float, ...], candidate_vec: Tuple[float, ...]
    ) -> float:
        p = np.array(user_vec, dtype=float)
        q = np.array(candidate_vec, dtype=float)

        # Normalize vectors to ensure they are valid probability distributions
        # Add epsilon to sum to avoid division by zero if a vector is all zeros
        p_sum = np.sum(p)
        q_sum = np.sum(q)

        if p_sum == 0 or q_sum == 0:
            return 0.0  # Should ideally not happen in valid budget vectors

        p_norm = p / p_sum
        q_norm = q / q_sum

        # Stability constant
        epsilon = 1e-10

        # Calculate KL Divergence: sum(p_i * ln(p_i / q_i))
        # Use a mask for p_i > 0 because if p_i is 0, the term is 0 * ln(0) -> 0 (lim x->0 x*ln(x) = 0)
        mask = p_norm > 0

        # Add epsilon to q to avoid division by zero inside log
        # q_norm[mask] could be 0, so we add epsilon.
        # We compute p * ln(p / (q + eps))

        divergence = np.sum(
            p_norm[mask] * np.log(p_norm[mask] / (q_norm[mask] + epsilon))
        )

        return -float(divergence)
