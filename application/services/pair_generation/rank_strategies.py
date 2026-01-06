"""
Concrete implementations of ranking-based pair generation strategies.
Defines specific utility model combinations (e.g., L1 vs Leontief) used in surveys.
"""

import logging

from application.services.algorithms.utility_models import (
    AntiLeontiefUtilityModel,
    KLUtilityModel,
    L1UtilityModel,
    L2UtilityModel,
    LeontiefUtilityModel,
)
from application.services.pair_generation.generic_rank_strategy import (
    GenericRankStrategy,
)

logger = logging.getLogger(__name__)


class L1VsLeontiefRankStrategy(GenericRankStrategy):
    """
    Strategy comparing L1 distance (Sum) against Leontief ratio (Ratio).

    """

    def __init__(self, grid_step: int = None):
        """
        Initialize with L1 and Leontief utility models.

        Note: GenericRankStrategy defaults to step=5.
        """
        super().__init__(
            utility_model_a_class=L1UtilityModel,
            utility_model_b_class=LeontiefUtilityModel,
            grid_step=grid_step,
            min_component=10,
        )


class L1VsL2RankStrategy(GenericRankStrategy):
    """
    Strategy comparing L1 distance (Sum) against L2 distance (Root Sum Squared).
    """

    def __init__(self, grid_step: int = None):
        """
        Initialize with L1 and L2 utility models.
        """
        super().__init__(
            utility_model_a_class=L1UtilityModel,
            utility_model_b_class=L2UtilityModel,
            grid_step=grid_step,
            min_component=0,
            normalization_method="ordinal",
        )


class L2VsLeontiefRankStrategy(GenericRankStrategy):
    """
    Strategy comparing L2 distance (Root Sum Squared) against Leontief ratio (Ratio).
    """

    def __init__(self, grid_step: int = None):
        """
        Initialize with L2 and Leontief utility models.
        """
        super().__init__(
            utility_model_a_class=L2UtilityModel,
            utility_model_b_class=LeontiefUtilityModel,
            grid_step=grid_step,
            min_component=10,
        )


class LeontiefVsAntiLeontiefRankStrategy(GenericRankStrategy):
    """
    Strategy comparing Leontief (min ratio) against Anti-Leontief (max ratio aversion).
    """

    def __init__(self, grid_step: int = None):
        super().__init__(
            utility_model_a_class=LeontiefUtilityModel,
            utility_model_b_class=AntiLeontiefUtilityModel,
            grid_step=grid_step,
            min_component=10,
        )


class LeontiefVsKLRankStrategy(GenericRankStrategy):
    """
    Strategy comparing Leontief (min ratio) against Kullback-Leibler (information divergence).
    """

    def __init__(self, grid_step: int = None):
        super().__init__(
            utility_model_a_class=LeontiefUtilityModel,
            utility_model_b_class=KLUtilityModel,
            grid_step=grid_step,
            min_component=10,
        )


class KLVsAntiLeontiefRankStrategy(GenericRankStrategy):
    """
    Strategy comparing Kullback-Leibler (information divergence) against Anti-Leontief (max ratio aversion).
    """

    def __init__(self, grid_step: int = None):
        super().__init__(
            utility_model_a_class=KLUtilityModel,
            utility_model_b_class=AntiLeontiefUtilityModel,
            grid_step=grid_step,
            min_component=10,
        )
